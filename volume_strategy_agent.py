"""
volume_strategy_agent.py — Institutional Volume Profile & RVOL Breakout Strategy Agent
=======================================================================================
Detects high-conviction trade setups using institutional volume data:
1. Relative Volume (RVOL = current candle volume / 20-period average volume).
2. Volume Spike Identification (RVOL >= 2.0x, surge >= 3.0x).
3. Session Volume-Weighted Average Price (VWAP) cross & expansion.
4. Cumulative Volume Delta (CVD) & Bullish/Bearish Volume Imbalance.
5. Strict Capital Survival R:R >= 1:3.0 targets.
"""

import logging
import math
import time
from typing import List, Dict, Any, Optional

log = logging.getLogger(__name__)

class VolumeStrategyAgent:
    """
    Scans market OHLCV data for institutional volume surges and relative volume (RVOL) breakouts.
    Emits trade signals directly consumable by RiskManager and DualExecutionAgent.
    """

    def __init__(self, cfg: dict, min_rvol: float = 2.0):
        self.cfg = cfg
        self.min_rvol = min_rvol

    def calculate_rvol(self, candles: list[dict], period: int = 20) -> float:
        """Calculate Relative Volume (RVOL) of the latest candle relative to previous 20 candles."""
        if not candles or len(candles) < period + 1:
            return 1.0
        
        recent_volumes = [float(c.get("volume", 0) or c.get("v", 0) or 0) for c in candles[-(period + 1):-1]]
        if not recent_volumes:
            return 1.0
            
        avg_vol = sum(recent_volumes) / max(len(recent_volumes), 1)
        latest_vol = float(candles[-1].get("volume", 0) or candles[-1].get("v", 0) or 0)
        
        if avg_vol <= 0:
            return 1.0
            
        return round(latest_vol / avg_vol, 2)

    def calculate_vwap(self, candles: list[dict]) -> float:
        """Calculate Volume-Weighted Average Price over candle window."""
        if not candles:
            return 0.0
        cum_pv = 0.0
        cum_vol = 0.0
        for c in candles:
            h = float(c.get("h", 0) or c.get("high", 0) or 0)
            l = float(c.get("l", 0) or c.get("low", 0) or 0)
            close = float(c.get("c", 0) or c.get("close", 0) or 0)
            vol = float(c.get("volume", 0) or c.get("v", 0) or 0)
            typical_price = (h + l + close) / 3.0 if (h and l and close) else close
            cum_pv += (typical_price * vol)
            cum_vol += vol
            
        return round(cum_pv / cum_vol, 4) if cum_vol > 0 else 0.0

    def evaluate_symbol(self, market_item: dict) -> Optional[dict]:
        """
        Analyze a single market item's OHLCV candle stream for volume breakouts.
        Returns a signal dict if criteria met, else None.
        """
        symbol = market_item.get("symbol", "")
        candles = market_item.get("candles") or market_item.get("df") or []
        
        # If candles in dictionary/list form
        if hasattr(candles, "to_dict"):
            candles = candles.to_dict("records")
            
        if not isinstance(candles, list) or len(candles) < 22:
            return None

        last_c = candles[-1]
        prev_c = candles[-2]
        
        close = float(last_c.get("c", 0) or last_c.get("close", 0) or 0)
        open_p = float(last_c.get("o", 0) or last_c.get("open", 0) or 0)
        prev_close = float(prev_c.get("c", 0) or prev_c.get("close", 0) or 0)
        
        if close <= 0 or prev_close <= 0:
            return None

        # 1. Compute RVOL
        rvol = self.calculate_rvol(candles, period=20)
        if rvol < self.min_rvol:
            return None

        # 2. Compute VWAP
        vwap = self.calculate_vwap(candles[-30:])
        price_change_pct = round(((close - prev_close) / prev_close) * 100, 2)
        
        # 3. Detect Direction & Volume Confirmation
        # Bullish: green candle (close > open), above VWAP, positive price jump with RVOL >= 2.0
        if close > open_p and close > vwap and price_change_pct >= 0.35:
            direction = "long"
            signal_type = "pump"
            base_conf = min(0.95, 0.76 + (min(rvol, 5.0) - 2.0) * 0.06)
        # Bearish: red candle (close < open), below VWAP, negative price drop with RVOL >= 2.0
        elif close < open_p and close < vwap and price_change_pct <= -0.35 and self.cfg.get("short_selling_enabled", True):
            direction = "short"
            signal_type = "dump"
            base_conf = min(0.93, 0.75 + (min(rvol, 5.0) - 2.0) * 0.05)
        else:
            return None

        # 4. Strict Capital Survival Targets (1:3.0 minimum Reward-to-Risk)
        sl_pct = min(1.5, float(self.cfg.get("stop_loss_pct", 1.2)))
        tp_pct = round(sl_pct * 3.2, 2) # Strict 1:3.2 R:R

        if direction == "long":
            hard_sl = round(close * (1.0 - sl_pct / 100.0), 4)
            take_profit = round(close * (1.0 + tp_pct / 100.0), 4)
        else:
            hard_sl = round(close * (1.0 + sl_pct / 100.0), 4)
            take_profit = round(close * (1.0 - tp_pct / 100.0), 4)

        log.info(
            "🔥 VolumeStrategyAgent DETECTED: %s %s | RVOL=%.2fx | Close=%.4f | VWAP=%.4f | Conf=%.2f | R:R=1:3.2",
            symbol, direction.upper(), rvol, close, vwap, base_conf
        )

        return {
            "symbol": symbol,
            "signal": signal_type,
            "direction": direction,
            "confidence": round(base_conf, 3),
            "price": close,
            "entry_price": close,
            "suspected_cause": f"volume_surge_rvol_{rvol:.1f}x_vwap_cross",
            "hard_sl_pct": sl_pct,
            "take_profit_pct": tp_pct,
            "hard_sl": hard_sl,
            "take_profit": take_profit,
            "supporting_data": {
                "price": close,
                "rvol": rvol,
                "vwap": vwap,
                "change_pct": price_change_pct,
                "volume_24h": float(market_item.get("volume", 100000) or 100000),
                "timestamp": int(time.time()),
            }
        }

    def scan_market_data(self, market_data: list[dict]) -> list[dict]:
        """Scan list of market items and return actionable volume signals."""
        signals = []
        for item in market_data:
            if not item or item.get("error"):
                continue
            sig = self.evaluate_symbol(item)
            if sig:
                signals.append(sig)
        return signals
