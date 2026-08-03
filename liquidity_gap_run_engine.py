"""
Smart Money Concepts (SMC): Liquidity Gap & Liquidity Run Strategy Engine
========================================================================
Implements the exact 4 liquidity trading strategies:
1. Liquidity Run Entry (BUY): Sweeps Previous Low (Sell-Side Liquidity) + Bullish Reversal.
2. Liquidity Run Entry (SELL): Sweeps Previous High (Buy-Side Liquidity Fakeout) + Bearish Reversal.
3. Liquidity Gap Entry (BUY): Bullish FVG Imbalance created -> Price retraces to fill gap -> BUY.
4. Liquidity Gap Entry (SELL): Bearish FVG Imbalance created -> Price retraces to fill gap -> SELL.
"""

import logging
import pandas as pd
import numpy as np

log = logging.getLogger(__name__)

class LiquidityGapRunEngine:
    def __init__(self, lookback_candles: int = 48):
        self.lookback = lookback_candles

    def analyze(self, df: pd.DataFrame) -> dict | None:
        if df is None or len(df) < 20:
            return None

        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        open_p = df["open"].astype(float)
        volume = df["volume"].astype(float)

        curr_close = float(close.iloc[-1])
        curr_high = float(high.iloc[-1])
        curr_low = float(low.iloc[-1])
        curr_open = float(open_p.iloc[-1])

        prev_close = float(close.iloc[-2])
        prev_high = float(high.iloc[-2])
        prev_low = float(low.iloc[-2])
        prev_open = float(open_p.iloc[-2])

        # Key Highs and Lows of the past range (excluding last 3 candles)
        range_high = float(high.iloc[-self.lookback:-3].max())
        range_low = float(low.iloc[-self.lookback:-3].min())

        # ── 1. LIQUIDITY RUN ENTRY (BUY) — Sweep Previous Low ─────────────────
        # Low spikes below previous key low, but candle closes back ABOVE previous key low
        if (curr_low < range_low or prev_low < range_low) and curr_close > range_low and curr_close > curr_open:
            wick_ratio = (min(curr_open, curr_close) - curr_low) / (curr_high - curr_low + 1e-8)
            if wick_ratio >= 0.25 or curr_close > prev_close:
                sl_price = round(min(curr_low, prev_low), 6)
                return {
                    "signal": "pump",
                    "direction": "BUY",
                    "strategy": "liquidity_run_buy_sweep",
                    "confidence": 0.92,
                    "entry": curr_close,
                    "sl": sl_price,
                    "reason": f"SMC Liquidity Sweep BUY below key low ({range_low:.4f})",
                }

        # ── 2. LIQUIDITY RUN ENTRY (SELL) — Sweep Previous High (Fakeout) ──────
        # High spikes above previous key high, but candle closes back BELOW previous key high
        if (curr_high > range_high or prev_high > range_high) and curr_close < range_high and curr_close < curr_open:
            wick_ratio = (curr_high - max(curr_open, curr_close)) / (curr_high - curr_low + 1e-8)
            if wick_ratio >= 0.25 or curr_close < prev_close:
                sl_price = round(max(curr_high, prev_high), 6)
                return {
                    "signal": "dump",
                    "direction": "SELL",
                    "strategy": "liquidity_run_sell_fakeout",
                    "confidence": 0.92,
                    "entry": curr_close,
                    "sl": sl_price,
                    "reason": f"SMC Liquidity Fakeout SELL above key high ({range_high:.4f})",
                }

        # ── 3. LIQUIDITY GAP ENTRY (BUY) — FVG Fill ────────────────────────────
        # FVG exists where Low of candle i > High of candle i-2
        if len(df) >= 6:
            c3_high = float(high.iloc[-5])
            c1_low = float(low.iloc[-3])
            if c1_low > c3_high:  # Bullish FVG gap exists between c3_high and c1_low
                gap_top = c1_low
                gap_bottom = c3_high
                # Price retraced into the gap and bounced up
                if curr_low <= gap_top and curr_close > gap_bottom and curr_close > curr_open:
                    return {
                        "signal": "pump",
                        "direction": "BUY",
                        "strategy": "liquidity_gap_buy_fvg",
                        "confidence": 0.89,
                        "entry": curr_close,
                        "sl": round(gap_bottom * 0.999, 6),
                        "reason": f"SMC Liquidity Gap Fill BUY ({gap_bottom:.4f}-{gap_top:.4f})",
                    }

        # ── 4. LIQUIDITY GAP ENTRY (SELL) — FVG Fill ───────────────────────────
        # Bearish FVG exists where High of candle i < Low of candle i-2
        if len(df) >= 6:
            c3_low = float(low.iloc[-5])
            c1_high = float(high.iloc[-3])
            if c1_high < c3_low:  # Bearish FVG gap exists between c1_high and c3_low
                gap_top = c3_low
                gap_bottom = c1_high
                # Price retraced up into the gap and printed bearish candle
                if curr_high >= gap_bottom and curr_close < gap_top and curr_close < curr_open:
                    return {
                        "signal": "dump",
                        "direction": "SELL",
                        "strategy": "liquidity_gap_sell_fvg",
                        "confidence": 0.89,
                        "entry": curr_close,
                        "sl": round(gap_top * 1.001, 6),
                        "reason": f"SMC Liquidity Gap Fill SELL ({gap_bottom:.4f}-{gap_top:.4f})",
                    }

        return None
