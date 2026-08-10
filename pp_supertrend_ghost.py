"""
PP SuperTrend + Reversal Zone Finder [Ghost Protocol] V3 + FRVP Strategy Engine
=================================================================================
Ported from PineScript v5:
1. Pivot Point SuperTrend (© LonesomeTheBlue):
   - Pivot Period = 2, ATR Factor = 3.0, ATR Period = 10
   - Center Line = Weighted average of Pivot High / Pivot Low
   - Upper Band = Center - (Factor * ATR)
   - Lower Band = Center + (Factor * ATR)
   - SuperTrend Trailing Stop & Direction (Trend == 1 for Bullish, -1 for Bearish)
   - Buy Signal: Trend flips from -1 to 1
   - Sell Signal: Trend flips from 1 to -1

2. Reversal Zone Finder [Ghost Protocol] V3:
   - Swing Lookback = 20
   - Session / Anchor VWAP + 2.5 StdDev Bands
   - 9 EMA Trend Filter
   - Bullish Zone: Low < Swing Low AND Close > Swing Low AND Close < VWAP
   - Bearish Zone: High > Swing High AND Close < Swing High AND Close > VWAP
"""

import numpy as np
import pandas as pd
import logging

log = logging.getLogger(__name__)

class PPSuperTrendGhostEngine:
    def __init__(self, prd: int = 2, factor: float = 3.0, pd_atr: int = 10, lookback: int = 20, vwap_len: int = 50):
        self.prd = prd
        self.factor = factor
        self.pd_atr = pd_atr
        self.lookback = lookback
        self.vwap_len = vwap_len

    def analyze(self, df: pd.DataFrame) -> dict:
        if df is None or len(df) < (self.lookback * 2 + 10):
            return {
                "signal": "normal",
                "confidence": 0.0,
                "trend": "neutral",
                "pp_supertrend_sl": 0.0,
                "ghost_bull_zone": False,
                "ghost_bear_zone": False,
                "reason": "insufficient_candles",
            }

        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['volume'].values
        n = len(close)

        # 1. Calculate ATR (10-period)
        tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
        tr = np.insert(tr, 0, high[0] - low[0])
        atr = pd.Series(tr).ewm(span=self.pd_atr, adjust=False).mean().values

        # 2. Pivot High/Low (prd=2)
        ph = np.full(n, np.nan)
        pl = np.full(n, np.nan)
        for i in range(self.prd, n - self.prd):
            if high[i] == np.max(high[i - self.prd : i + self.prd + 1]):
                ph[i] = high[i]
            if low[i] == np.min(low[i - self.prd : i + self.prd + 1]):
                pl[i] = low[i]

        # 3. Center line calculation using pivot points
        center = np.full(n, np.nan)
        curr_center = np.nan
        for i in range(n):
            lastpp = ph[i] if not np.isnan(ph[i]) else (pl[i] if not np.isnan(pl[i]) else np.nan)
            if not np.isnan(lastpp):
                if np.isnan(curr_center):
                    curr_center = lastpp
                else:
                    curr_center = (curr_center * 2.0 + lastpp) / 3.0
            center[i] = curr_center

        if np.isnan(center[0]):
            first_valid = np.where(~np.isnan(center))[0]
            if len(first_valid) > 0:
                center[:first_valid[0]] = center[first_valid[0]]
            else:
                center[:] = (high + low) / 2.0

        # 4. Upper / Lower bands
        up_band = center - (self.factor * atr)
        dn_band = center + (self.factor * atr)

        # 5. Trend & Trailing Stop calculation
        t_up = np.zeros(n)
        t_dn = np.zeros(n)
        trend = np.ones(n, dtype=int)
        trailing_sl = np.zeros(n)

        for i in range(1, n):
            if close[i - 1] > t_up[i - 1]:
                t_up[i] = max(up_band[i], t_up[i - 1])
            else:
                t_up[i] = up_band[i]

            if close[i - 1] < t_dn[i - 1]:
                t_dn[i] = min(dn_band[i], t_dn[i - 1])
            else:
                t_dn[i] = dn_band[i]

            if close[i] > t_dn[i - 1]:
                trend[i] = 1
            elif close[i] < t_up[i - 1]:
                trend[i] = -1
            else:
                trend[i] = trend[i - 1]

            trailing_sl[i] = t_up[i] if trend[i] == 1 else t_dn[i]

        pp_buy = (trend[-1] == 1) and (trend[-2] == -1)
        pp_sell = (trend[-1] == -1) and (trend[-2] == 1)
        pp_trend = trend[-1]

        # 6. Ghost Protocol Reversal Zone Finder
        swing_highs = [high[i] for i in range(self.lookback, n - self.lookback) if high[i] == np.max(high[i - self.lookback : i + self.lookback + 1])]
        swing_lows = [low[i] for i in range(self.lookback, n - self.lookback) if low[i] == np.min(low[i - self.lookback : i + self.lookback + 1])]

        active_highest = swing_highs[-1] if swing_highs else np.max(high[-self.lookback:])
        active_lowest = swing_lows[-1] if swing_lows else np.min(low[-self.lookback:])

        tp = (high + low + close) / 3.0
        cum_vol = np.cumsum(volume)
        vwap = np.cumsum(tp * volume) / np.where(cum_vol == 0, 1, cum_vol)
        ema9 = pd.Series(close).ewm(span=9, adjust=False).mean().values

        ghost_bull_zone = (low[-1] < active_lowest) and (close[-1] > active_lowest) and (close[-1] < vwap[-1])
        ghost_bear_zone = (high[-1] > active_highest) and (close[-1] < active_highest) and (close[-1] > vwap[-1])

        # 7. Combined Signal Scoring
        signal_type = "normal"
        confidence = 0.50
        reasons = []

        if pp_buy or (trend[-1] == 1 and ghost_bull_zone):
            signal_type = "pump"
            reasons.append("pp_supertrend_buy_signal" if pp_buy else "ghost_protocol_bullish_reversal_zone")
            confidence = 0.96 if (pp_buy and ghost_bull_zone) else (0.90 if pp_buy else 0.85)
            if close[-1] > ema9[-1]:
                confidence += 0.03
        elif pp_sell or (trend[-1] == -1 and ghost_bear_zone):
            signal_type = "dump"
            reasons.append("pp_supertrend_sell_signal" if pp_sell else "ghost_protocol_bearish_reversal_zone")
            confidence = 0.96 if (pp_sell and ghost_bear_zone) else (0.90 if pp_sell else 0.85)
            if close[-1] < ema9[-1]:
                confidence += 0.03
        elif trend[-1] == 1 and close[-1] > ema9[-1]:
            signal_type = "pump"
            reasons.append("pp_supertrend_bullish_trend_continuation")
            confidence = 0.72
        elif trend[-1] == -1 and close[-1] < ema9[-1]:
            signal_type = "dump"
            reasons.append("pp_supertrend_bearish_trend_continuation")
            confidence = 0.72

        return {
            "signal": signal_type,
            "confidence": round(min(0.95, confidence), 3),
            "trend": "bullish" if pp_trend == 1 else "bearish",
            "pp_supertrend_sl": round(trailing_sl[-1], 6),
            "ghost_bull_zone": bool(ghost_bull_zone),
            "ghost_bear_zone": bool(ghost_bear_zone),
            "reason": " + ".join(reasons) if reasons else "pp_supertrend_neutral",
        }
