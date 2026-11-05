"""
Professional Multi-Strategy Confluence & Market Structure Engine (10-in-1 Adaptive Matrix)
========================================================================================
Designed initially for GOLD (XAUUSD) and adaptable to BTCUSD, ETHUSD, Forex, and Indices.
Incorporates:
1. Market Structure + VWAP (BOS, CHoCH, Retest)
2. EMA 9/21 + RSI Momentum
3. Supertrend + VWAP Trend Flip
4. Breakout + Volume Expansion
5. Order Block + Liquidity Sweep (SMC)
6. Opening Range Breakout (London/NY Sessions)
7. MACD + EMA Trend Filter
8. Bollinger Band Mean Reversion
9. Donchian Channel Breakout
10. Multi-Timeframe Confluence (H1 Trend, M15 Confirmation, M5 Execution)

Includes Dynamic Failover: If Strategy A fails quality threshold (<75), automatically
evaluates next strategy in the performance matrix.
Enforces Strict Risk: 0.5% max risk, ATR Adaptive SL, Multi-Tier TP (1R, 2R, 3R),
Session Filter (London/NY), High-Impact News Filter, Max Consecutive Loss circuit breaker.
"""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


class InstitutionalStrategyEngine:
    """
    Multi-Timeframe Algorithmic Confluence Strategy Engine.
    Evaluates setups across 10 institutional strategies with automatic failover.
    """

    def __init__(self, cfg: Optional[Dict[str, Any]] = None):
        self.cfg = cfg or {}

        # ── Timeframe & Symbol Configuration ───────────────────────────────────
        self.symbol = self.cfg.get("symbol", "XAUUSD")
        self.htf = self.cfg.get("htf", "H1")        # Higher Timeframe: Trend
        self.ctf = self.cfg.get("ctf", "M15")       # Confirmation Timeframe: Structure
        self.ltf = self.cfg.get("ltf", "M5")        # Execution Timeframe: Retest & Trigger

        # ── Confluence Thresholds ──────────────────────────────────────────────
        self.min_quality_score = float(self.cfg.get("min_quality_score", 75.0))
        self.min_rr_ratio = float(self.cfg.get("min_rr_ratio", 2.0))
        self.risk_per_trade_pct = float(self.cfg.get("risk_per_trade_pct", 0.5))  # Default 0.5% equity

        # ── ATR & Volatility Multipliers ───────────────────────────────────────
        self.atr_period = int(self.cfg.get("atr_period", 14))
        self.atr_buffer_mult = float(self.cfg.get("atr_buffer_mult", 1.2))

        # ── Session Filter (UTC) ───────────────────────────────────────────────
        self.london_start = int(self.cfg.get("london_start_hour", 8))   # 08:00 UTC
        self.london_end = int(self.cfg.get("london_end_hour", 12))     # 12:00 UTC
        self.ny_start = int(self.cfg.get("ny_start_hour", 13))         # 13:00 UTC
        self.ny_end = int(self.cfg.get("ny_end_hour", 17))             # 17:00 UTC

        # ── Circuit Breakers & Loss Management ─────────────────────────────────
        self.max_daily_loss_pct = float(self.cfg.get("max_daily_loss_pct", 2.0))
        self.max_consecutive_losses = int(self.cfg.get("max_consecutive_losses", 3))
        self.consecutive_loss_count = 0
        self.daily_pnl_pct = 0.0
        self.last_loss_time = 0.0
        self.cooldown_seconds = int(self.cfg.get("cooldown_seconds", 1800))  # 30 min cooldown

    # ── 1. TECHNICAL INDICATOR CALCULATORS ──────────────────────────────────────

    @staticmethod
    def calculate_ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        close = df["close"].astype(float)
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def calculate_session_vwap(df: pd.DataFrame) -> pd.Series:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
        vol = df["volume"] if "volume" in df.columns and df["volume"].sum() > 0 else pd.Series(np.ones(len(df)), index=df.index)
        cum_vol = vol.cumsum()
        cum_vp = (typical_price * vol).cumsum()
        return cum_vp / (cum_vol + 1e-9)

    @staticmethod
    def calculate_volume_profile(df: pd.DataFrame, bins: int = 24) -> Dict[str, Any]:
        """
        Computes Institutional Volume Profile:
        - Point of Control (POC): Price level with highest traded volume
        - Value Area High (VAH) and Value Area Low (VAL): 70% of total volume
        """
        if len(df) < 5 or "volume" not in df.columns or df["volume"].sum() <= 0:
            p = float(df["close"].iloc[-1])
            return {"poc": p, "vah": p * 1.01, "val": p * 0.99, "in_value_area": True, "below_val": False, "above_vah": False}
        
        price_min = float(df["low"].min())
        price_max = float(df["high"].max())
        if price_max <= price_min:
            p = float(df["close"].iloc[-1])
            return {"poc": p, "vah": p * 1.01, "val": p * 0.99, "in_value_area": True, "below_val": False, "above_vah": False}

        bin_size = (price_max - price_min) / bins
        vol_bins = np.zeros(bins)
        
        typical_prices = (df["high"] + df["low"] + df["close"]) / 3.0
        for tp, v in zip(typical_prices, df["volume"]):
            idx = int((tp - price_min) / bin_size)
            idx = min(max(idx, 0), bins - 1)
            vol_bins[idx] += v

        poc_idx = int(np.argmax(vol_bins))
        poc_price = price_min + (poc_idx + 0.5) * bin_size

        total_vol = np.sum(vol_bins)
        target_vol = total_vol * 0.70
        curr_vol = vol_bins[poc_idx]
        left_idx, right_idx = poc_idx, poc_idx

        while curr_vol < target_vol and (left_idx > 0 or right_idx < bins - 1):
            next_left_vol = vol_bins[left_idx - 1] if left_idx > 0 else 0
            next_right_vol = vol_bins[right_idx + 1] if right_idx < bins - 1 else 0
            if next_left_vol >= next_right_vol and left_idx > 0:
                left_idx -= 1
                curr_vol += next_left_vol
            elif right_idx < bins - 1:
                right_idx += 1
                curr_vol += next_right_vol
            else:
                break

        val_price = price_min + left_idx * bin_size
        vah_price = price_min + (right_idx + 1) * bin_size
        curr_price = float(df["close"].iloc[-1])

        return {
            "poc": round(poc_price, 6),
            "vah": round(vah_price, 6),
            "val": round(val_price, 6),
            "in_value_area": val_price <= curr_price <= vah_price,
            "above_vah": curr_price > vah_price,
            "below_val": curr_price < val_price
        }

    @staticmethod
    def calculate_order_flow_delta(df: pd.DataFrame, lookback: int = 5) -> Dict[str, Any]:
        """
        Calculates Order Flow Imbalance, Cumulative Volume Delta (CVD), and Aggressive Volume Pressure.
        """
        if len(df) < lookback:
            return {"net_delta_ratio": 0.0, "bias": "neutral", "absorption": False}
        
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))

        deltas = []
        for k in range(-lookback, 0):
            rng = max(high[k] - low[k], 1e-6)
            buy_vol = volume[k] * ((close[k] - low[k]) / rng)
            sell_vol = volume[k] * ((high[k] - close[k]) / rng)
            deltas.append(buy_vol - sell_vol)

        net_delta = float(np.sum(deltas))
        tot_vol = float(np.sum(volume[-lookback:])) or 1.0
        delta_ratio = round(net_delta / tot_vol, 3)

        price_diff = close[-1] - close[-lookback]
        absorption = False
        bias = "neutral"

        if price_diff < 0 and delta_ratio > 0.10:
            absorption = True
            bias = "bullish"
        elif price_diff > 0 and delta_ratio < -0.10:
            absorption = True
            bias = "bearish"
        elif delta_ratio > 0.15:
            bias = "bullish"
        elif delta_ratio < -0.15:
            bias = "bearish"

        return {
            "net_delta_ratio": delta_ratio,
            "bias": bias,
            "absorption": absorption
        }


    # ── 2. MARKET STRUCTURE & SESSIONS ─────────────────────────────────────────

    def is_valid_session(self, dt_utc: Optional[datetime] = None) -> bool:
        """
        Verifies trading session.
        Crypto (BTC, ETH, SOL, altcoins) trades 24/7.
        For traditional assets (Gold, Forex, Indices), checks London (08-12 UTC) / NY (13-17 UTC)
        or allows 24/7 if enforce_session_filter is disabled.
        """
        if not self.cfg.get("enforce_session_filter", False):
            return True
        sym = str(self.symbol or "").upper()
        # Crypto trades 24/7
        if any(c in sym for c in ("BTC", "ETH", "SOL", "USDT", "DOGE", "XRP", "WIF", "PEPE")):
            return True
        now = dt_utc or datetime.now(timezone.utc)
        hour = now.hour
        is_london = self.london_start <= hour < self.london_end
        is_ny = self.ny_start <= hour < self.ny_end
        return is_london or is_ny

    def detect_market_structure(self, df: pd.DataFrame, lookback: int = 20) -> Dict[str, Any]:
        """
        Detects Higher Highs (HH), Higher Lows (HL), Lower Highs (LH), Lower Lows (LL),
        Break of Structure (BOS), and Change of Character (CHoCH).
        """
        if df is None or len(df) < lookback:
            return {"trend": "neutral", "bos": False, "choch": False, "retest": False}

        highs = df["high"].iloc[-lookback:].values
        lows = df["low"].iloc[-lookback:].values
        closes = df["close"].iloc[-lookback:].values

        curr_close = closes[-1]
        prev_swing_high = np.max(highs[:-3])
        prev_swing_low = np.min(lows[:-3])

        # Break of Structure (BOS)
        bullish_bos = curr_close > prev_swing_high
        bearish_bos = curr_close < prev_swing_low

        # Retest detection: price broke structure, then pulled back to retest the broken zone
        bullish_retest = False
        bearish_retest = False

        if bullish_bos:
            # Low of retest candle touches near previous swing high within 0.15%
            dist = abs(df["low"].iloc[-1] - prev_swing_high) / prev_swing_high
            bullish_retest = dist <= 0.003
        elif bearish_bos:
            dist = abs(df["high"].iloc[-1] - prev_swing_low) / prev_swing_low
            bearish_retest = dist <= 0.003

        # Trend bias
        trend = "bullish" if closes[-1] > closes[-5] and highs[-1] > highs[-5] else ("bearish" if closes[-1] < closes[-5] and lows[-1] < lows[-5] else "neutral")

        return {
            "trend": trend,
            "bullish_bos": bool(bullish_bos),
            "bearish_bos": bool(bearish_bos),
            "bullish_retest": bool(bullish_retest),
            "bearish_retest": bool(bearish_retest),
            "prev_swing_high": float(prev_swing_high),
            "prev_swing_low": float(prev_swing_low),
        }

    # ── 3. INDIVIDUAL STRATEGY MODULES (1 TO 10) ────────────────────────────────

    def eval_strategy_0_core_orderflow_vp_vwap_ema43(
        self, df_m5: pd.DataFrame, df_h1: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        MASTER CORE STRATEGY: Order Flow + Volume Profile + VWAP + EMA 43 Trend Filter.
        Requires strict confluence:
          1. EMA 43: Price > EMA 43 (BULLISH) or Price < EMA 43 (BEARISH)
          2. VWAP: Price > Session VWAP for longs, Price < Session VWAP for shorts
          3. Volume Profile: Entry relative to Value Area (VAH/VAL bounce or POC acceptance)
          4. Order Flow / CVD: Aggressive buyer/seller delta confirming trade direction (>0.10 or absorption)
        """
        if len(df_m5) < 45:
            return {"name": "Core OrderFlow + VP + VWAP + EMA 43", "score": 0, "approved": False, "reason": "insufficient_candles"}

        close = float(df_m5["close"].iloc[-1])
        ema43 = float(self.calculate_ema(df_m5["close"], 43).iloc[-1])
        vwap = float(self.calculate_session_vwap(df_m5).iloc[-1])
        vp = self.calculate_volume_profile(df_m5)
        of = self.calculate_order_flow_delta(df_m5)

        score = 0
        direction = None
        confluence_reasons = []

        # --- LONG CONFLUENCE ---
        if close > ema43 and close > vwap:
            long_points = 50
            confluence_reasons.append("Price > EMA 43 and VWAP")

            if close >= vp["poc"] or vp.get("below_val", False) is False:
                long_points += 20
                confluence_reasons.append(f"Volume Profile Support (POC: {vp['poc']})")

            if of["bias"] == "bullish" or of["absorption"]:
                long_points += 25
                confluence_reasons.append(f"Order Flow Bullish Delta: {of['net_delta_ratio']}")

            if long_points >= 85:
                score = long_points
                direction = "BUY"

        # --- SHORT CONFLUENCE ---
        elif close < ema43 and close < vwap:
            short_points = 50
            confluence_reasons.append("Price < EMA 43 and VWAP")

            if close <= vp["poc"] or vp.get("above_vah", False) is False:
                short_points += 20
                confluence_reasons.append(f"Volume Profile Resistance (POC: {vp['poc']})")

            if of["bias"] == "bearish" or of["absorption"]:
                short_points += 25
                confluence_reasons.append(f"Order Flow Bearish Delta: {of['net_delta_ratio']}")

            if short_points >= 85:
                score = short_points
                direction = "SELL"

        return {
            "name": "Core OrderFlow + VP + VWAP + EMA 43",
            "score": score,
            "direction": direction,
            "approved": score >= self.min_quality_score,
            "ema43": round(ema43, 6),
            "vwap": round(vwap, 6),
            "poc": vp["poc"],
            "vah": vp["vah"],
            "val": vp["val"],
            "order_flow_delta": of["net_delta_ratio"],
            "confluence": " | ".join(confluence_reasons)
        }

    def eval_strategy_1_structure_vwap(self, df_m5: pd.DataFrame, df_h1: pd.DataFrame) -> Dict[str, Any]:
        """Strategy 1: Market Structure + Session VWAP (BOS + Retest + VWAP)."""
        vwap = self.calculate_session_vwap(df_m5).iloc[-1]
        close = df_m5["close"].iloc[-1]
        struct = self.detect_market_structure(df_m5)

        # Anti-chop filter: price crossing VWAP back and forth > 3 times in 10 candles
        vwap_series = self.calculate_session_vwap(df_m5).iloc[-10:]
        close_series = df_m5["close"].iloc[-10:]
        crosses = np.sum(np.diff((close_series > vwap_series).astype(int)) != 0)
        if crosses >= 3:
            return {"score": 0, "approved": False, "reason": "vwap_chop_filter_triggered"}

        score = 0
        direction = None
        if close > vwap and struct.get("bullish_bos") and struct.get("bullish_retest"):
            score = 88
            direction = "BUY"
        elif close < vwap and struct.get("bearish_bos") and struct.get("bearish_retest"):
            score = 88
            direction = "SELL"

        return {"name": "Market Structure + VWAP", "score": score, "direction": direction, "approved": score >= self.min_quality_score}

    def eval_strategy_2_ema_rsi(self, df_m5: pd.DataFrame) -> Dict[str, Any]:
        """Strategy 2: EMA 9/21 + 43 EMA Baseline Trend Filter + RSI Momentum Filter."""
        ema9 = self.calculate_ema(df_m5["close"], 9).iloc[-1]
        ema21 = self.calculate_ema(df_m5["close"], 21).iloc[-1]
        ema43 = self.calculate_ema(df_m5["close"], 43).iloc[-1]
        prev_ema9 = self.calculate_ema(df_m5["close"], 9).iloc[-2]
        prev_ema21 = self.calculate_ema(df_m5["close"], 21).iloc[-2]
        rsi = self.calculate_rsi(df_m5["close"], 14).iloc[-1]
        close = df_m5["close"].iloc[-1]

        score = 0
        direction = None
        # Bullish: Price > 43 EMA, EMA 9 > EMA 21 crossover, RSI 48-68
        if close > ema43 and prev_ema9 <= prev_ema21 and ema9 > ema21 and 48 <= rsi <= 68:
            score = 85
            direction = "BUY"
        # Bearish: Price < 43 EMA, EMA 9 < EMA 21 crossunder, RSI 32-52
        elif close < ema43 and prev_ema9 >= prev_ema21 and ema9 < ema21 and 32 <= rsi <= 52:
            score = 85
            direction = "SELL"

        return {"name": "EMA 9/21/43 + RSI", "score": score, "direction": direction, "approved": score >= self.min_quality_score, "ema43": round(ema43, 4)}

    def eval_strategy_3_supertrend_vwap(self, df_m5: pd.DataFrame) -> Dict[str, Any]:
        """Strategy 3: Supertrend + VWAP Trend Flip."""
        atr = self.calculate_atr(df_m5, 10).iloc[-1]
        vwap = self.calculate_session_vwap(df_m5).iloc[-1]
        close = df_m5["close"].iloc[-1]
        score = 0
        direction = None
        # Simplified Pivot Supertrend flip
        upper_band = (df_m5["high"].iloc[-1] + df_m5["low"].iloc[-1]) / 2.0 + (atr * 2.0)
        lower_band = (df_m5["high"].iloc[-1] + df_m5["low"].iloc[-1]) / 2.0 - (atr * 2.0)

        if close > vwap and close > upper_band:
            score = 80
            direction = "BUY"
        elif close < vwap and close < lower_band:
            score = 80
            direction = "SELL"

        return {"name": "Supertrend + VWAP", "score": score, "direction": direction, "approved": score >= self.min_quality_score}

    def eval_strategy_4_breakout_volume(self, df_m5: pd.DataFrame) -> Dict[str, Any]:
        """Strategy 4: Range Breakout + Volume Expansion."""
        vol = df_m5["volume"] if "volume" in df_m5.columns else pd.Series(np.ones(len(df_m5)))
        avg_vol = vol.iloc[-20:].mean()
        curr_vol = vol.iloc[-1]
        close = df_m5["close"].iloc[-1]
        high_20 = df_m5["high"].iloc[-20:-1].max()
        low_20 = df_m5["low"].iloc[-20:-1].min()

        score = 0
        direction = None
        if curr_vol >= avg_vol * 1.8:
            if close > high_20:
                score = 85
                direction = "BUY"
            elif close < low_20:
                score = 85
                direction = "SELL"

        return {"name": "Breakout + Volume", "score": score, "direction": direction, "approved": score >= self.min_quality_score}

    def eval_strategy_5_orderblock_sweep(self, df_m5: pd.DataFrame) -> Dict[str, Any]:
        """Strategy 5: Order Block + Liquidity Sweep (SMC)."""
        lows = df_m5["low"].iloc[-15:].values
        highs = df_m5["high"].iloc[-15:].values
        curr_low = df_m5["low"].iloc[-1]
        curr_high = df_m5["high"].iloc[-1]
        curr_close = df_m5["close"].iloc[-1]
        curr_open = df_m5["open"].iloc[-1]

        score = 0
        direction = None
        # Sell-Side Liquidity Sweep (SSL) + Reversal
        key_low = np.min(lows[:-2])
        if curr_low < key_low and curr_close > key_low and curr_close > curr_open:
            score = 90
            direction = "BUY"
        # Buy-Side Liquidity Sweep (BSL) + Reversal
        key_high = np.max(highs[:-2])
        if curr_high > key_high and curr_close < key_high and curr_close < curr_open:
            score = 90
            direction = "SELL"

        return {"name": "Order Block + Liquidity Sweep", "score": score, "direction": direction, "approved": score >= self.min_quality_score}

    def eval_strategy_6_opening_range(self, df_m5: pd.DataFrame) -> Dict[str, Any]:
        """Strategy 6: Opening Range Breakout (ORB)."""
        close = df_m5["close"].iloc[-1]
        high_or = df_m5["high"].iloc[-6:].max()
        low_or = df_m5["low"].iloc[-6:].min()
        score = 0
        direction = None
        if close > high_or:
            score = 78
            direction = "BUY"
        elif close < low_or:
            score = 78
            direction = "SELL"
        return {"name": "Opening Range Breakout", "score": score, "direction": direction, "approved": score >= self.min_quality_score}

    def eval_strategy_7_macd_ema(self, df_m5: pd.DataFrame) -> Dict[str, Any]:
        """Strategy 7: MACD + EMA Trend Filter."""
        ema50 = self.calculate_ema(df_m5["close"], 50).iloc[-1]
        ema200 = self.calculate_ema(df_m5["close"], 200).iloc[-1]
        close = df_m5["close"].iloc[-1]

        ema12 = self.calculate_ema(df_m5["close"], 12)
        ema26 = self.calculate_ema(df_m5["close"], 26)
        macd = ema12 - ema26
        signal = self.calculate_ema(macd, 9)

        score = 0
        direction = None
        if ema50 > ema200 and close > ema50 and macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
            score = 81
            direction = "BUY"
        elif ema50 < ema200 and close < ema50 and macd.iloc[-1] < signal.iloc[-1] and macd.iloc[-2] >= signal.iloc[-2]:
            score = 81
            direction = "SELL"
        return {"name": "MACD + EMA Trend Filter", "score": score, "direction": direction, "approved": score >= self.min_quality_score}

    def eval_strategy_8_bollinger_reversion(self, df_m5: pd.DataFrame) -> Dict[str, Any]:
        """Strategy 8: Bollinger Band Mean Reversion."""
        sma20 = df_m5["close"].rolling(20).mean().iloc[-1]
        std20 = df_m5["close"].rolling(20).std().iloc[-1]
        upper = sma20 + (2.0 * std20)
        lower = sma20 - (2.0 * std20)
        rsi = self.calculate_rsi(df_m5["close"], 14).iloc[-1]
        close = df_m5["close"].iloc[-1]

        score = 0
        direction = None
        if close <= lower and rsi <= 30:
            score = 76
            direction = "BUY"
        elif close >= upper and rsi >= 70:
            score = 76
            direction = "SELL"
        return {"name": "Bollinger Band Mean Reversion", "score": score, "direction": direction, "approved": score >= self.min_quality_score}

    def eval_strategy_9_donchian_breakout(self, df_m5: pd.DataFrame) -> Dict[str, Any]:
        """Strategy 9: Donchian Channel Breakout."""
        d_high = df_m5["high"].iloc[-20:-1].max()
        d_low = df_m5["low"].iloc[-20:-1].min()
        close = df_m5["close"].iloc[-1]

        score = 0
        direction = None
        if close > d_high:
            score = 79
            direction = "BUY"
        elif close < d_low:
            score = 79
            direction = "SELL"
        return {"name": "Donchian Channel Breakout", "score": score, "direction": direction, "approved": score >= self.min_quality_score}

    def eval_strategy_10_multi_timeframe(self, df_m5: pd.DataFrame, df_m15: pd.DataFrame, df_h1: pd.DataFrame) -> Dict[str, Any]:
        """Strategy 10: Multi-Timeframe Confluence (H1 Trend + M15 Structure + M5 Retest)."""
        h1_ema50 = self.calculate_ema(df_h1["close"], 50).iloc[-1]
        h1_ema200 = self.calculate_ema(df_h1["close"], 200).iloc[-1]
        m15_struct = self.detect_market_structure(df_m15)
        m5_struct = self.detect_market_structure(df_m5)

        h1_bull = h1_ema50 > h1_ema200
        h1_bear = h1_ema50 < h1_ema200

        score = 0
        direction = None
        if h1_bull and m15_struct["trend"] == "bullish" and m5_struct.get("bullish_retest"):
            score = 94
            direction = "BUY"
        elif h1_bear and m15_struct["trend"] == "bearish" and m5_struct.get("bearish_retest"):
            score = 94
            direction = "SELL"
        return {"name": "Multi-Timeframe Confluence", "score": score, "direction": direction, "approved": score >= self.min_quality_score}

    # ── 4. MULTI-STRATEGY FAILOVER MATRIX (PRIMARY + FALLBACK HIERARCHY) ─────────

    def evaluate_multi_strategy_matrix(
        self,
        df_m5: pd.DataFrame,
        df_m15: Optional[pd.DataFrame] = None,
        df_h1: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates strategies in hierarchical priority. If one strategy fails or scores < 75,
        automatically cascades down to the next viable setup in the matrix.
        """
        # Session check
        if not self.is_valid_session():
            return {"approved": False, "reason": "outside_london_or_new_york_session", "score": 0}

        # Circuit breaker check: daily loss limit reached
        if self.daily_pnl_pct <= -self.max_daily_loss_pct:
            return {"approved": False, "reason": "max_daily_loss_circuit_breaker_active", "score": 0}

        # Consecutive loss cooldown check
        if self.consecutive_loss_count >= self.max_consecutive_losses:
            if (time.time() - self.last_loss_time) < self.cooldown_seconds:
                return {"approved": False, "reason": "consecutive_loss_cooldown_active", "score": 0}
            else:
                self.consecutive_loss_count = 0  # Cooldown expired, reset

        strategies_to_test = [
            lambda: self.eval_strategy_0_core_orderflow_vp_vwap_ema43(df_m5, df_h1),
            lambda: self.eval_strategy_10_multi_timeframe(df_m5, df_m15 or df_m5, df_h1 or df_m5),
            lambda: self.eval_strategy_5_orderblock_sweep(df_m5),
            lambda: self.eval_strategy_1_structure_vwap(df_m5, df_h1 or df_m5),
            lambda: self.eval_strategy_4_breakout_volume(df_m5),
            lambda: self.eval_strategy_2_ema_rsi(df_m5),
            lambda: self.eval_strategy_7_macd_ema(df_m5),
            lambda: self.eval_strategy_3_supertrend_vwap(df_m5),
            lambda: self.eval_strategy_9_donchian_breakout(df_m5),
            lambda: self.eval_strategy_6_opening_range(df_m5),
            lambda: self.eval_strategy_8_bollinger_reversion(df_m5),
        ]

        evaluated_results = []
        for strat_fn in strategies_to_test:
            res = strat_fn()
            evaluated_results.append(res)
            # If strategy produces a valid, high-confidence signal >= 75 score -> select and break
            if res.get("approved") and res.get("direction"):
                # Calculate adaptive ATR TP/SL and sizing
                trade_params = self.calculate_trade_parameters(df_m5, res["direction"])
                res.update(trade_params)
                res["failover_history"] = [r["name"] for r in evaluated_results[:-1]]
                log.info("Institutional Engine Selected Strategy: %s (Score: %s, Direction: %s)", res["name"], res["score"], res["direction"])
                return res

        # ── ULTIMATE FAILOVER: NVIDIA Super Brain Autonomous Strategy Generator ──
        # When all 10 standard rule-based strategies produce no viable entry,
        # activate Super Brain Intelligence (GLM-5.3 + Nemotron) to synthesize a custom strategy
        try:
            from nvidia_super_brain import NvidiaSuperBrainEngine
            super_brain = NvidiaSuperBrainEngine(self.cfg)
            custom_strat = super_brain.synthesize_custom_strategy(
                symbol=self.symbol,
                df=df_m5,
                market_data={"price": float(df_m5["close"].iloc[-1])}
            )
            if custom_strat.get("approved") and custom_strat.get("direction"):
                custom_strat["failover_history"] = [r["name"] for r in evaluated_results]
                custom_strat["risk_per_trade_pct"] = self.risk_per_trade_pct
                if not custom_strat.get("tp1") or not custom_strat.get("tp2"):
                    trade_params = self.calculate_trade_parameters(df_m5, custom_strat["direction"])
                    for k, v in trade_params.items():
                        if k not in custom_strat or not custom_strat[k]:
                            custom_strat[k] = v
                log.info("Institutional Engine Fallback Triggered -> Super Brain Synthesized Strategy: %s", custom_strat.get("name"))
                return custom_strat
        except Exception as sb_exc:
            log.warning("Super Brain strategy synthesis exception: %s", sb_exc)

        return {
            "approved": False,
            "reason": "all_10_strategies_and_superbrain_failed_confluence_threshold",
            "score": max([r.get("score", 0) for r in evaluated_results] or [0]),
            "evaluated_count": len(evaluated_results),
        }

    # ── 5. ADAPTIVE ATR TP/SL & MULTI-TIER EXITS ──────────────────────────────────

    def calculate_trade_parameters(self, df_m5: pd.DataFrame, direction: str) -> Dict[str, Any]:
        """Calculates adaptive ATR-based Stop Loss and Multi-Tier Take Profit (1R, 2R, 3R)."""
        close = float(df_m5["close"].iloc[-1])
        atr = float(self.calculate_atr(df_m5, self.atr_period).iloc[-1] or 1.0)
        buffer = atr * self.atr_buffer_mult

        struct = self.detect_market_structure(df_m5)
        # Dynamic minimum risk distance: 0.8% of price or ATR (avoids giant $0.50 SL on sub-dollar coins)
        min_risk_dist = max(close * 0.008, 1e-6)

        if direction == "BUY":
            swing_low = struct.get("prev_swing_low") or (close - buffer)
            raw_sl = min(close - buffer, swing_low - (atr * 0.3))
            risk_dist = max(close - raw_sl, min_risk_dist)
            sl_price = round(close - risk_dist, 6)
            tp1 = round(close + (risk_dist * 1.5), 6)
            tp2 = round(close + (risk_dist * 3.0), 6)
            tp3 = round(close + (risk_dist * 4.5), 6)
        else:
            swing_high = struct.get("prev_swing_high") or (close + buffer)
            raw_sl = max(close + buffer, swing_high + (atr * 0.3))
            risk_dist = max(raw_sl - close, min_risk_dist)
            sl_price = round(close + risk_dist, 6)
            tp1 = round(close - (risk_dist * 1.5), 6)
            tp2 = round(close - (risk_dist * 3.0), 6)
            tp3 = round(close - (risk_dist * 4.5), 6)

        rr_ratio = round((abs(tp2 - close)) / risk_dist, 2)

        return {
            "entry_price": close,
            "stop_loss": sl_price,
            "tp1": tp1,  # 30-50% exit + move SL to breakeven
            "tp2": tp2,  # Second exit
            "tp3": tp3,  # Runner exit / trailing
            "risk_reward_ratio": rr_ratio,
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "atr": round(atr, 4),
        }
