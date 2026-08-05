"""
Kronos AI Foundation Model Trading Agent
=========================================
Uses Tsinghua / NeoQuasar Kronos Financial K-Line Transformer Foundation Model
to perform zero-shot autoregressive price & volatility forecasting on 5m candles.
"""

import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure Kronos package directory is in sys.path
KRONOS_DIR = Path(__file__).parent / "Kronos"
if str(KRONOS_DIR) not in sys.path:
    sys.path.insert(0, str(KRONOS_DIR))

log = logging.getLogger(__name__)


class KronosAIAgent:
    """
    Kronos AI Agent: Leverages pre-trained Kronos K-line Transformer foundation model
    to forecast 5m candle price trajectory over the next 12 candles (60 minutes).
    """

    def __init__(self, cfg, model_name: str = "NeoQuasar/Kronos-small"):
        self.cfg = cfg
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.predictor = None
        self._initialized = False

    def _lazy_init(self):
        """Lazy load Kronos model weights from HuggingFace Hub on first prediction."""
        if self._initialized:
            return True
        try:
            from model import Kronos, KronosTokenizer, KronosPredictor

            log.info("KronosAIAgent: Loading Kronos Foundation Model weights (%s)...", self.model_name)
            self.tokenizer = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
            self.model = Kronos.from_pretrained(self.model_name)
            self.predictor = KronosPredictor(self.model, self.tokenizer, max_context=512)
            self._initialized = True
            log.info("KronosAIAgent: Model successfully loaded into memory ✅")
            return True
        except Exception as exc:
            log.warning("KronosAIAgent: Model initialization notice (%s). Using algorithmic fallback.", exc)
            return False

    def predict_trajectory(self, symbol: str, ohlcv_candles: list[dict], pred_len: int = 12) -> dict:
        """
        Forecast price return over next `pred_len` 5m candles (default 12 candles = 60 mins).
        Returns dict with predicted return %, direction, and confidence.
        """
        if not ohlcv_candles or len(ohlcv_candles) < 20:
            return {"forecast_pct": 0.0, "direction": "neutral", "confidence_boost": 0.0, "status": "insufficient_data"}

        try:
            df = pd.DataFrame(ohlcv_candles)
            col_map = {"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume", "vol": "volume"}
            df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

            for c in ["open", "high", "low", "close", "volume"]:
                if c not in df.columns:
                    df[c] = df["close"] if "close" in df.columns else 0.0
                df[c] = df[c].astype(float)

            if "timestamps" not in df.columns and "t" in df.columns:
                df["timestamps"] = pd.to_datetime(df["t"], unit="ms")
            elif "timestamps" not in df.columns:
                df["timestamps"] = pd.date_range(end=pd.Timestamp.now(), periods=len(df), freq="5min")

            df_context = df.tail(400).reset_index(drop=True)
            last_close = float(df_context["close"].iloc[-1])

            if self._lazy_init() and self.predictor is not None:
                x_df = df_context[["open", "high", "low", "close", "volume"]]
                x_ts = df_context["timestamps"]
                y_ts = pd.date_range(start=x_ts.iloc[-1] + pd.Timedelta(minutes=5), periods=pred_len, freq="5min")

                pred_df = self.predictor.predict(
                    df=x_df,
                    x_timestamp=x_ts,
                    y_timestamp=y_ts,
                    pred_len=pred_len,
                    T=0.8,
                    top_p=0.9,
                    sample_count=1,
                    verbose=False,
                )

                predicted_close = float(pred_df["close"].iloc[-1])
                forecast_pct = ((predicted_close - last_close) / last_close) * 100.0
            else:
                closes = df_context["close"].values
                slope = np.polyfit(np.arange(len(closes[-12:])), closes[-12:], 1)[0]
                forecast_pct = (slope * pred_len / last_close) * 100.0

            direction = "bullish" if forecast_pct > 0.3 else ("bearish" if forecast_pct < -0.3 else "neutral")
            confidence_boost = min(0.20, max(-0.20, forecast_pct / 10.0))

            return {
                "symbol": symbol,
                "last_price": last_close,
                "forecast_pct": round(forecast_pct, 2),
                "direction": direction,
                "confidence_boost": round(confidence_boost, 3),
                "status": "success",
            }
        except Exception as exc:
            log.warning("Kronos prediction error for %s: %s", symbol, exc)
            return {"symbol": symbol, "forecast_pct": 0.0, "direction": "neutral", "confidence_boost": 0.0, "status": "error"}

    def enhance_signals(self, signals: list[dict], market_data_map: dict) -> list[dict]:
        """
        Enhance signal confidence scores using Kronos Transformer price predictions.
        """
        enhanced = []
        for sig in signals:
            symbol = sig["symbol"]
            cand_data = market_data_map.get(symbol, {}).get("candles", [])
            pred = self.predict_trajectory(symbol, cand_data, pred_len=12)

            original_conf = sig["confidence"]
            boost = pred.get("confidence_boost", 0.0)

            if sig["signal"] == "pump" and pred["direction"] == "bullish":
                new_conf = min(0.98, original_conf + abs(boost))
                sig["kronos_verdict"] = f"CONFIRMED_BULLISH (+{pred['forecast_pct']}%)"
            elif sig["signal"] == "dump" and pred["direction"] == "bearish":
                new_conf = min(0.98, original_conf + abs(boost))
                sig["kronos_verdict"] = f"CONFIRMED_BEARISH ({pred['forecast_pct']}%)"
            elif (sig["signal"] == "pump" and pred["direction"] == "bearish") or (sig["signal"] == "dump" and pred["direction"] == "bullish"):
                new_conf = max(0.20, original_conf - abs(boost) * 1.5)
                sig["kronos_verdict"] = f"REJECTED_CONTRADICTION ({pred['forecast_pct']}%)"
            else:
                new_conf = original_conf
                sig["kronos_verdict"] = f"NEUTRAL ({pred['forecast_pct']}%)"

            sig["confidence"] = round(new_conf, 3)
            sig["kronos_forecast_pct"] = pred["forecast_pct"]
            enhanced.append(sig)

        return enhanced
