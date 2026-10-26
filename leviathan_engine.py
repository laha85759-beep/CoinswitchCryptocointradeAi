"""
leviathan_engine.py - Leviathan Trend-Filtered Price Action & Break of Structure (BOS) Engine
=============================================================================================
Extracted & integrated from santiquiroz/leviathan for live execution across:
  - CoinSwitch Pro (Spot)
  - Delta Exchange India (Crypto F&O & Futures)
  - MyFundedPerpetuals ($2,500 Prop Firm)
  - MetaTrader 5 (CK Capital $10K Instant Funding)

Strategy Formula (3-Pillar Confluence):
  1. Triple EMA Trend Filter:
     - Long: EMA(9) > EMA(21) and Close > EMA(200)
     - Short: EMA(9) < EMA(21) and Close < EMA(200)
  2. Break of Structure (BOS):
     - Long: Close breaks highest high of last 20 bars
     - Short: Close breaks lowest low of last 20 bars
  3. Price Action Candle Trigger:
     - Bullish / Bearish Engulfing OR Pinbar with customizable wick-to-body ratio (default 2.0x)
  4. Precise Stop Loss (SL) & Take Profit (TP):
     - SL: 1.5x ATR below swing structure
     - TP: 1:2.0 Risk-to-Reward ratio (or configurable TP %)
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

log = logging.getLogger("LeviathanEngine")


def calc_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def is_bullish_engulfing(df: pd.DataFrame) -> pd.Series:
    prev_open = df["open"].shift(1)
    prev_close = df["close"].shift(1)
    curr_open = df["open"]
    curr_close = df["close"]

    prev_bearish = prev_close < prev_open
    curr_bullish = curr_close > curr_open
    engulfs = (curr_open <= prev_close) & (curr_close >= prev_open)
    return prev_bearish & curr_bullish & engulfs


def is_bearish_engulfing(df: pd.DataFrame) -> pd.Series:
    prev_open = df["open"].shift(1)
    prev_close = df["close"].shift(1)
    curr_open = df["open"]
    curr_close = df["close"]

    prev_bullish = prev_close > prev_open
    curr_bearish = curr_close < curr_open
    engulfs = (curr_open >= prev_close) & (curr_close <= prev_open)
    return prev_bullish & curr_bearish & engulfs


def is_bullish_pinbar(df: pd.DataFrame, wick_ratio: float = 2.0) -> pd.Series:
    open_p = df["open"]
    close_p = df["close"]
    high_p = df["high"]
    low_p = df["low"]

    body = (close_p - open_p).abs()
    lower_wick = np.minimum(open_p, close_p) - low_p
    upper_wick = high_p - np.maximum(open_p, close_p)

    valid_pin = (lower_wick >= wick_ratio * np.maximum(body, 1e-8)) & (lower_wick > upper_wick * 1.5)
    return valid_pin


def is_bearish_pinbar(df: pd.DataFrame, wick_ratio: float = 2.0) -> pd.Series:
    open_p = df["open"]
    close_p = df["close"]
    high_p = df["high"]
    low_p = df["low"]

    body = (close_p - open_p).abs()
    upper_wick = high_p - np.maximum(open_p, close_p)
    lower_wick = np.minimum(open_p, close_p) - low_p

    valid_pin = (upper_wick >= wick_ratio * np.maximum(body, 1e-8)) & (upper_wick > lower_wick * 1.5)
    return valid_pin


class LeviathanStrategyEngine:
    def __init__(
        self,
        ema_fast: int = 9,
        ema_slow: int = 21,
        ema_trend: int = 200,
        structure_lookback: int = 20,
        atr_period: int = 14,
        atr_multiplier: float = 1.5,
        risk_reward_ratio: float = 2.0,
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.ema_trend = ema_trend
        self.structure_lookback = structure_lookback
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.risk_reward_ratio = risk_reward_ratio

    def evaluate(self, df: pd.DataFrame, symbol: str = "ASSET") -> Dict[str, Any]:
        """
        Evaluates OHLCV DataFrame for Leviathan 3-pillar setup.
        Returns setup dictionary with action, entry, exact sl, and exact tp.
        """
        if df is None or len(df) < self.structure_lookback + 5:
            return {"active": False, "reason": "insufficient_candles"}

        df = df.copy()
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)

        ema9 = calc_ema(df["close"], self.ema_fast)
        ema21 = calc_ema(df["close"], self.ema_slow)
        effective_trend_period = self.ema_trend if len(df) >= self.ema_trend else max(30, len(df) - 2)
        ema200 = calc_ema(df["close"], effective_trend_period)
        atr_series = calc_atr(df, self.atr_period)

        # Structure Breakouts: Highest high / lowest low of preceding 20 bars (excluding current)
        rolling_high = df["high"].shift(1).rolling(window=self.structure_lookback).max()
        rolling_low = df["low"].shift(1).rolling(window=self.structure_lookback).min()

        last_idx = df.index[-1]
        curr_close = df["close"].iloc[-1]
        curr_atr = atr_series.iloc[-1] or (curr_close * 0.015)

        # 1. Trend Filter
        is_bull_trend = (ema9.iloc[-1] > ema21.iloc[-1]) and (curr_close > ema200.iloc[-1])
        is_bear_trend = (ema9.iloc[-1] < ema21.iloc[-1]) and (curr_close < ema200.iloc[-1])

        # 2. Break of Structure (BOS)
        bos_long = curr_close > rolling_high.iloc[-1]
        bos_short = curr_close < rolling_low.iloc[-1]

        # 3. Candle Trigger
        bull_engulf = is_bullish_engulfing(df).iloc[-1]
        bear_engulf = is_bearish_engulfing(df).iloc[-1]
        bull_pin = is_bullish_pinbar(df).iloc[-1]
        bear_pin = is_bearish_pinbar(df).iloc[-1]

        bull_trigger = bull_engulf or bull_pin
        bear_trigger = bear_engulf or bear_pin

        # Check Confluence
        if is_bull_trend and bos_long and bull_trigger:
            pattern = "engulfing" if bull_engulf else "pinbar"
            swing_sl = rolling_low.iloc[-1]
            sl_price = round(min(swing_sl, curr_close - (self.atr_multiplier * curr_atr)), 4 if curr_close > 1 else 6)
            risk = max(curr_close - sl_price, curr_close * 0.008)
            tp_price = round(curr_close + (risk * self.risk_reward_ratio), 4 if curr_close > 1 else 6)

            return {
                "active": True,
                "symbol": symbol,
                "action": "BUY",
                "direction": "long",
                "confidence": 0.92,
                "pattern": pattern,
                "entry_price": curr_close,
                "sl": sl_price,
                "tp": tp_price,
                "rr_ratio": self.risk_reward_ratio,
                "reason": f"leviathan_bos_long_{pattern}_ema_confluence",
            }

        elif is_bear_trend and bos_short and bear_trigger:
            pattern = "engulfing" if bear_engulf else "pinbar"
            swing_sh = rolling_high.iloc[-1]
            sl_price = round(max(swing_sh, curr_close + (self.atr_multiplier * curr_atr)), 4 if curr_close > 1 else 6)
            risk = max(sl_price - curr_close, curr_close * 0.008)
            tp_price = round(curr_close - (risk * self.risk_reward_ratio), 4 if curr_close > 1 else 6)

            return {
                "active": True,
                "symbol": symbol,
                "action": "SELL",
                "direction": "short",
                "confidence": 0.92,
                "pattern": pattern,
                "entry_price": curr_close,
                "sl": sl_price,
                "tp": tp_price,
                "rr_ratio": self.risk_reward_ratio,
                "reason": f"leviathan_bos_short_{pattern}_ema_confluence",
            }

        return {"active": False, "reason": "no_confluence", "trend": "bullish" if is_bull_trend else ("bearish" if is_bear_trend else "neutral")}
