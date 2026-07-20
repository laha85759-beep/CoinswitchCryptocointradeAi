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
#  Consolidation + Breakout Engine
# ═══════════════════════════════════════════════════════════════════════════════

class ConsolidationBreakoutEngine:
    """
    Detects coins consolidating for 1-2 days and fires on breakout / trendline breakout.

    Consolidation = narrow price range + Bollinger squeeze (low BB width percentile).
    Breakout      = price closes above range high with volume confirmation.
    Trendline     = price breaks above a descending trendline drawn from swing lows.
    """

    def __init__(self, cfg: dict):
        self.lookback         = cfg.get("consolidation_lookback_hours", 48)
        self.range_max_pct    = cfg.get("consolidation_range_max_pct", 4.0)
        self.bb_squeeze_pct   = cfg.get("bb_squeeze_percentile", 20)
        self.breakout_vol_mul = cfg.get("breakout_volume_multiplier", 1.8)
        self.trendline_on     = cfg.get("trendline_breakout_enabled", True)

    # ── public ────────────────────────────────────────────────────────────────
    def detect(self, df_1h: pd.DataFrame, df_5m: pd.DataFrame | None = None) -> dict | None:
        if df_1h is None or len(df_1h) < 24:
            return None
        if not self._is_consolidating(df_1h):
            return None
        return self._check_breakout(df_1h, df_5m)

    # ── consolidation check ───────────────────────────────────────────────────
    def _is_consolidating(self, df: pd.DataFrame) -> bool:
        lookback = min(self.lookback, len(df))
        recent   = df.tail(lookback)

        high_range = float(recent.high.max())
        low_range  = float(recent.low.min())
        range_pct  = (high_range - low_range) / low_range * 100
        if range_pct > self.range_max_pct:
            return False

        if len(df) >= 50:
            _, _, _, bw = bollinger(df.close, 20, 2.0)
            bw_clean = bw.dropna()
            if len(bw_clean) >= 20:
                current_bw = float(bw_clean.iloc[-1])
                bw_pctl    = float((bw_clean <= current_bw).sum() / len(bw_clean) * 100)
                if bw_pctl > self.bb_squeeze_pct:
                    return False
        return True

    # ── breakout detection ────────────────────────────────────────────────────
    def _check_breakout(self, df_1h: pd.DataFrame, df_5m: pd.DataFrame | None = None) -> dict | None:
        lookback   = min(self.lookback, len(df_1h))
        recent     = df_1h.tail(lookback)
        high_range = float(recent.high.max())
        low_range  = float(recent.low.min())

        df = df_5m if df_5m is not None and len(df_5m) > 10 else df_1h
        cur  = float(df.close.iloc[-1])
        prev = float(df.close.iloc[-2]) if len(df) > 1 else cur

        # ── price breakout above range ────────────────────────────────────────
        if cur > high_range and prev <= high_range:
            avg_vol     = float(df_1h.volume.tail(lookback).mean())
            current_vol = float(df_1h.volume.iloc[-1])
            vol_mult    = current_vol / avg_vol if avg_vol > 0 else 0

            if vol_mult >= self.breakout_vol_mul:
                r = float(rsi(df.close).iloc[-1]) if len(df) >= 14 else 50.0
                if 40 < r < 75:
                    return {
                        "type":                "consolidation_breakout",
                        "direction":           "BUY",
                        "entry_price":         cur,
                        "consolidation_high":  high_range,
                        "consolidation_low":   low_range,
                        "range_pct":           round((high_range - low_range) / low_range * 100, 2),
                        "volume_multiplier":   round(vol_mult, 2),
                        "rsi":                 round(r, 1),
                        "strength":            min(100, int(vol_mult * 25 + (75 - r) * 0.5)),
                    }

        # ── trendline breakout ────────────────────────────────────────────────
        if self.trendline_on and len(df_1h) >= 24:
            tl = self._check_trendline_break(df_1h)
            if tl:
                return tl
        return None

    # ── trendline detection (swing-low linear regression) ─────────────────────
    def _check_trendline_break(self, df: pd.DataFrame) -> dict | None:
        swing_lows = []
        for i in range(2, len(df) - 2):
            lo = float(df.low.iloc[i])
            if lo <= float(df.low.iloc[i - 1]) and lo <= float(df.low.iloc[i + 1]):
                swing_lows.append((i, lo))
        if len(swing_lows) < 3:
            return None

        x = np.array([s[0] for s in swing_lows[-3:]], dtype=float)
        y = np.array([s[1] for s in swing_lows[-3:]], dtype=float)
        slope, intercept = np.polyfit(x, y, 1)

        idx  = float(len(df) - 1)
        tl   = slope * idx + intercept
        cur  = float(df.close.iloc[-1])
        prev = float(df.close.iloc[-2]) if len(df) > 1 else cur

        if cur > tl and prev <= tl:
            avg_vol     = float(df.volume.tail(24).mean())
            current_vol = float(df.volume.iloc[-1])
            vol_mult    = current_vol / avg_vol if avg_vol > 0 else 0
            if vol_mult >= self.breakout_vol_mul * 0.7:
                r = float(rsi(df.close).iloc[-1]) if len(df) >= 14 else 50.0
                return {
                    "type":              "trendline_breakout",
                    "direction":         "BUY",
                    "entry_price":       cur,
                    "trendline_value":   round(tl, 8),
                    "trendline_slope":   round(slope, 8),
                    "volume_multiplier": round(vol_mult, 2),
                    "rsi":               round(r, 1),
                    "strength":          min(100, int(vol_mult * 20 + (75 - r) * 0.5)),
                }
        return None


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
        quote = self.cfg["quote_currency"]
        min_vol = self.cfg.get("min_volume_usdt", 50_000)

        # Try c2c2 first (has candle data), fallback to c2c1
        for exchange in ("c2c2", "c2c1"):
            tickers = self.client.get_all_tickers(exchange)
            log.info("Scanner: got %s tickers from %s", len(tickers), exchange)
            if not tickers:
                continue

            pairs = []
            for sym, data in tickers.items():
                raw_quote = data.get("quoteVolume")
                vol = float(raw_quote) if raw_quote else 0.0
                if vol <= 0:
                    base_vol = float(data.get("baseVolume", 0) or 0)
                    last_price = float(data.get("lastPrice", 0) or 0)
                    vol = base_vol * last_price

                if sym.endswith(f"/{quote}") and vol >= min_vol and sym not in self.cfg["blacklist"]:
                    pairs.append((sym, vol))

            if pairs:
                pairs.sort(key=lambda x: x[1], reverse=True)
                result = [p[0] for p in pairs[: self.cfg["top_n_by_volume"]]]
                log.info("Scanner: found %s %s pairs with vol >= %s", len(result), exchange, min_vol)
                return result
            else:
                sample = list(tickers.items())[:5]
                log.warning(
                    "Scanner: 0 %s pairs matched (quote=%s min_vol=%s). Sample: %s",
                    exchange, quote, min_vol,
                    [(s, {k: v for k, v in d.items() if k in ("lastPrice", "baseVolume", "quoteVolume")}) for s, d in sample],
                )

        log.error("Scanner: no symbols found on ANY exchange")
        return []

    def _ohlcv(self, symbol: str) -> pd.DataFrame | None:
        try:
            interval = self._parse_timeframe(self.cfg["timeframe"])
            # c2c2 has candle data; fallback to c2c1
            for ex in ("c2c2", "c2c1"):
                candles = self.client.get_ohlcv(symbol, interval, self.cfg["candle_limit"], exchange=ex)
                if candles and len(candles) >= 50:
                    df = pd.DataFrame(candles)
                    df["open"] = df["o"].astype(float)
                    df["high"] = df["h"].astype(float)
                    df["low"]  = df["l"].astype(float)
                    df["close"] = df["c"].astype(float)
                    df["volume"] = df["volume"].astype(float)
                    return df
            log.debug("OHLCV: insufficient candles for %s on c2c2/c2c1", symbol)
            return None
        except Exception as e:
            log.debug(f"OHLCV error {symbol}: {e}")
            return None

    def _ohlcv_1h(self, symbol: str, limit: int = 48) -> pd.DataFrame | None:
        try:
            for ex in ("c2c2", "c2c1"):
                candles = self.client.get_ohlcv(symbol, 60, limit, exchange=ex)
                if candles and len(candles) >= 24:
                    df = pd.DataFrame(candles)
                    df["open"]   = df["o"].astype(float)
                    df["high"]   = df["h"].astype(float)
                    df["low"]    = df["l"].astype(float)
                    df["close"]  = df["c"].astype(float)
                    df["volume"] = df["volume"].astype(float)
                    return df
            return None
        except Exception as e:
            log.debug(f"1h OHLCV error {symbol}: {e}")
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
