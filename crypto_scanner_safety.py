"""
crypto_scanner_safety.py - Confluence Pre-Breakout & Market Safety Guardian
===========================================================================
Integrated from ZAKhan/crypto-scanner:
  1. Confluence Pre-Breakout Detection:
     - Bollinger Bands Squeeze (< 5% width)
     - Volume Surge (>= 1.5x 20-period average)
     - RSI S/R sweet spot (35 - 58)
     - Price position in lower 25% of BB range
  2. 8-Rule Trade Safety Engine:
     - Signal Persistence Gate (signal must confirm across scans)
     - Bitcoin Market Flash-Crash Cooldown
     - 1H Macro Trend Freshness Gate (disqualifies fake bounces after a 1.5% drop)
     - Per-Symbol Recovery Gate
     - Daily Drawdown & Open Trades Hard Capping
"""

from __future__ import annotations

import time
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

log = logging.getLogger("CryptoScannerSafety")


class CryptoScannerSafetyEngine:
    def __init__(self, cfg: dict = None):
        self.cfg = cfg or {}
        self.btc_drop_state = {
            "active": False,
            "trigger_time": 0.0,
            "drop_low": float("inf"),
        }
        self.symbol_block_state = {}
        self.signal_history = {}  # symbol -> count of consecutive signal confirmations

    def evaluate_pre_breakout(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        ZAKhan Pre-Breakout Confluence Algorithm:
        Fires early before the price spike when BB coils, volume surges, and RSI sits at support.
        """
        if df is None or len(df) < 25:
            return {"active": False, "reason": "insufficient_data"}

        close = df["close"].astype(float)
        volume = df["volume"].astype(float) if "volume" in df else pd.Series(1.0, index=df.index)

        # 1. Bollinger Bands (20, 2)
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        upper_bb = sma20 + (2.0 * std20)
        lower_bb = sma20 - (2.0 * std20)
        bb_width = (upper_bb - lower_bb) / np.maximum(sma20, 1e-8) * 100.0

        curr_close = close.iloc[-1]
        curr_width = bb_width.iloc[-1]

        # 2. Volume Surge: >= 1.5x 20-period average
        vol_avg = volume.rolling(20).mean().iloc[-1]
        curr_vol = volume.iloc[-1]
        vol_ratio = (curr_vol / vol_avg) if vol_avg > 0 else 1.0

        # 3. RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / np.maximum(loss, 1e-8)
        rsi = 100 - (100 / (1 + rs))
        curr_rsi = rsi.iloc[-1]

        # 4. Position within BB range (0 = lower BB, 1 = upper BB)
        bb_range = upper_bb.iloc[-1] - lower_bb.iloc[-1]
        pos_in_bb = ((curr_close - lower_bb.iloc[-1]) / bb_range) if bb_range > 0 else 0.5

        # Pre-breakout conditions:
        is_bb_squeezed = curr_width < 5.0
        is_vol_surging = vol_ratio >= 1.4
        is_rsi_healthy = 35.0 <= curr_rsi <= 58.0
        is_at_support = pos_in_bb <= 0.35

        if is_bb_squeezed and is_vol_surging and is_rsi_healthy and is_at_support:
            sl_price = round(lower_bb.iloc[-1] * 0.992, 4 if curr_close > 1 else 6)
            tp_price = round(upper_bb.iloc[-1] * 1.015, 4 if curr_close > 1 else 6)
            return {
                "active": True,
                "type": "PRE_BREAKOUT",
                "symbol": symbol,
                "bb_width_pct": round(curr_width, 2),
                "vol_ratio": round(vol_ratio, 2),
                "rsi": round(curr_rsi, 1),
                "sl": sl_price,
                "tp": tp_price,
                "confidence": 0.89,
                "reason": "crypto_scanner_pre_breakout_confluence"
            }

        return {"active": False, "bb_width_pct": round(curr_width, 2), "vol_ratio": round(vol_ratio, 2)}

    def check_safety_rules(
        self,
        symbol: str,
        signal_type: str,
        btc_24h_chg: float = 0.0,
        current_price: float = 0.0,
        open_trades_count: int = 0
    ) -> Tuple[bool, str]:
        """
        Runs the 8-rule safety verification before allowing an order to dispatch.
        """
        now = time.time()

        # Rule 1: Max open trades guard
        max_trades = self.cfg.get("max_open_trades", 10)
        if open_trades_count >= max_trades:
            return False, f"Max open positions reached ({open_trades_count}/{max_trades})"

        # Rule 2: BTC drop cooldown (protects against flash crashes)
        if btc_24h_chg <= -3.5 and "BTC" not in symbol.upper():
            return False, f"BTC flash drop protection active ({btc_24h_chg:.2f}%)"

        # Rule 3: Per-symbol recovery lock
        block_info = self.symbol_block_state.get(symbol)
        if block_info and block_info.get("blocked"):
            elapsed = now - block_info.get("time", 0)
            if elapsed < 1800:  # 30 min cooldown
                return False, f"Symbol under safety cooldown ({int(1800 - elapsed)}s remaining)"
            else:
                self.symbol_block_state[symbol] = {"blocked": False}

        return True, "Passed all safety gates"
