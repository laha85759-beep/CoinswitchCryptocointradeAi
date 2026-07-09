"""
Market Scanner + AI Signal Engine  (CoinSwitch edition)
═══════════════════════════════════════════════════════
Scores each coin 0–100 for pump / dump probability using
6 weighted technical signals on 5-minute candles.
"""

import logging
import numpy as np
import pandas as pd

from coinswitch_client import CoinSwitchClient

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  Indicators
# ═══════════════════════════════════════════════════════════════════════════════

def ema(s: pd.Series, p: int) -> pd.Series:
    return s.ewm(span=p, adjust=False).mean()

def rsi(s: pd.Series, p: int = 14) -> pd.Series:
    d = s.diff()
    g = d.clip(lower=0).ewm(com=p - 1, adjust=False).mean()
    l = (-d).clip(lower=0).ewm(com=p - 1, adjust=False).mean()
    return 100 - 100 / (1 + g / l)

def vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df.high + df.low + df.close) / 3
    return (tp * df.volume).cumsum() / df.volume.cumsum()

def bollinger(s: pd.Series, p: int = 20, k: float = 2.0):
    mid  = s.rolling(p).mean()
    std  = s.rolling(p).std()
    bw   = (2 * k * std) / mid
    return mid + k * std, mid, mid - k * std, bw


# ═══════════════════════════════════════════════════════════════════════════════
#  Signal Engine
# ═══════════════════════════════════════════════════════════════════════════════

class SignalEngine:
    def __init__(self, weights: dict):
        self.w = weights

    def score(self, df: pd.DataFrame) -> dict:
        pump, dump = {}, {}

        # 1 ── EMA 9/21 cross ────────────────────────────────────────────────
        e9, e21 = ema(df.close, 9), ema(df.close, 21)
        if   e9.iloc[-1] > e21.iloc[-1] and e9.iloc[-2] <= e21.iloc[-2]:
            pump["ema_cross"], dump["ema_cross"] = 100, 0
        elif e9.iloc[-1] < e21.iloc[-1] and e9.iloc[-2] >= e21.iloc[-2]:
            pump["ema_cross"], dump["ema_cross"] = 0, 100
        elif e9.iloc[-1] > e21.iloc[-1]:
            pump["ema_cross"], dump["ema_cross"] = 60, 40
        else:
            pump["ema_cross"], dump["ema_cross"] = 40, 60

        # 2 ── RSI ────────────────────────────────────────────────────────────
        r = rsi(df.close).iloc[-1]
        if   r < 30:  pump["rsi"], dump["rsi"] = 90, 10
        elif r < 45:  pump["rsi"], dump["rsi"] = 68, 32
        elif r > 70:  pump["rsi"], dump["rsi"] = 10, 90
        elif r > 55:  pump["rsi"], dump["rsi"] = 32, 68
        else:         pump["rsi"], dump["rsi"] = 50, 50

        # 3 ── VWAP ───────────────────────────────────────────────────────────
        vw   = vwap(df).iloc[-1]
        diff = (df.close.iloc[-1] - vw) / vw * 100
        if   diff > 0.5:  pump["vwap"], dump["vwap"] = 70, 30
        elif diff < -0.5: pump["vwap"], dump["vwap"] = 30, 70
        else:             pump["vwap"], dump["vwap"] = 50, 50

        # 4 ── Volume spike ───────────────────────────────────────────────────
        avg_vol  = df.volume.rolling(20).mean().iloc[-1]
        vol_r    = df.volume.iloc[-1] / avg_vol if avg_vol else 1
        chg      = (df.close.iloc[-1] - df.close.iloc[-2]) / df.close.iloc[-2] * 100
        if vol_r > 2.5:
            pump["volume_spike"], dump["volume_spike"] = (95, 5) if chg > 0 else (5, 95)
        elif vol_r > 1.5:
            pump["volume_spike"], dump["volume_spike"] = (70, 30) if chg > 0 else (30, 70)
        else:
            pump["volume_spike"], dump["volume_spike"] = 50, 50

        # 5 ── Momentum (5-candle ROC) ────────────────────────────────────────
        roc = (df.close.iloc[-1] - df.close.iloc[-6]) / df.close.iloc[-6] * 100
        if   roc > 1.5:  pump["momentum"], dump["momentum"] = 80, 20
        elif roc > 0.5:  pump["momentum"], dump["momentum"] = 65, 35
        elif roc < -1.5: pump["momentum"], dump["momentum"] = 20, 80
        elif roc < -0.5: pump["momentum"], dump["momentum"] = 35, 65
        else:            pump["momentum"], dump["momentum"] = 50, 50

        # 6 ── Bollinger squeeze + position ───────────────────────────────────
        upper, mid_b, lower, bw = bollinger(df.close)
        squeeze    = bw.iloc[-5:].mean() <= bw.rolling(50).min().iloc[-1] * 1.2
        above_mid  = df.close.iloc[-1] > mid_b.iloc[-1]
        near_upper = df.close.iloc[-1] > upper.iloc[-1] * 0.995
        near_lower = df.close.iloc[-1] < lower.iloc[-1] * 1.005

        if squeeze and above_mid:
            pump["bb_squeeze"], dump["bb_squeeze"] = 80, 20
        elif squeeze and not above_mid:
            pump["bb_squeeze"], dump["bb_squeeze"] = 20, 80
        elif near_upper:
            pump["bb_squeeze"], dump["bb_squeeze"] = 25, 75
        elif near_lower:
            pump["bb_squeeze"], dump["bb_squeeze"] = 75, 25
        else:
            pump["bb_squeeze"], dump["bb_squeeze"] = 50, 50

        # ── Weighted composite ────────────────────────────────────────────────
        w = self.w
        tw = sum(w.values())
        ps = sum(pump.get(k, 50) * v for k, v in w.items()) / tw
        ds = sum(dump.get(k, 50) * v for k, v in w.items()) / tw

        return {
            "pump_score": round(ps, 1),
            "dump_score": round(ds, 1),
            "rsi":        round(r,  1),
            "vol_ratio":  round(vol_r, 2),
            "roc5":       round(roc, 2),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Market Scanner
# ═══════════════════════════════════════════════════════════════════════════════

class MarketScanner:
    def __init__(self, config: dict, client: CoinSwitchClient):
        self.cfg    = config
        self.client = client
        self.engine = SignalEngine(config["weights"])

    @staticmethod
    def _parse_timeframe(tf: str) -> int:
        m = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}
        return m.get(tf, 5)

    def _top_symbols(self) -> list[str]:
        tickers = self.client.get_all_tickers_multi()

        pairs = []
        for sym, data in tickers.items():
            raw_vol = data.get("quoteVolume", 0)
            vol = float(raw_vol) if raw_vol else 0.0
            if (
                sym.endswith(f"/{self.cfg['quote_currency']}")
                and vol >= self.cfg["min_volume_usdt"]
                and sym not in self.cfg["blacklist"]
            ):
                pairs.append((sym, vol))

        pairs.sort(key=lambda x: x[1], reverse=True)
        return [p[0] for p in pairs[: self.cfg["top_n_by_volume"]]]

    def _ohlcv(self, symbol: str) -> pd.DataFrame | None:
        try:
            interval = self._parse_timeframe(self.cfg["timeframe"])
            candles = self.client.get_ohlcv(symbol, interval, self.cfg["candle_limit"])
            if not candles or len(candles) < 50:
                return None
            df = pd.DataFrame(candles)
            df["open"] = df["o"].astype(float)
            df["high"] = df["h"].astype(float)
            df["low"]  = df["l"].astype(float)
            df["close"] = df["c"].astype(float)
            df["volume"] = df["volume"].astype(float)
            return df
        except Exception as e:
            log.debug(f"OHLCV error {symbol}: {e}")
            return None

    def scan(self) -> tuple[list[dict], list[dict]]:
        symbols = self._top_symbols()
        log.info(f"  Scanning {len(symbols)} symbols on CoinSwitch…")

        pumps, dumps = [], []

        for sym in symbols:
            df = self._ohlcv(sym)
            if df is None:
                continue

            res   = self.engine.score(df)
            price = df.close.iloc[-1]

            if res["pump_score"] >= self.cfg["pump_score_min"]:
                pumps.append({**res, "symbol": sym, "direction": "BUY",  "price": price})

            if res["dump_score"] >= self.cfg["dump_score_min"]:
                dumps.append({**res, "symbol": sym, "direction": "SELL", "price": price})

        n = self.cfg["max_signals"]
        pumps.sort(key=lambda x: x["pump_score"], reverse=True)
        dumps.sort(key=lambda x: x["dump_score"], reverse=True)
        return pumps[:n], dumps[:n]
