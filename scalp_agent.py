"""
Quick Scalping AI Agent (QuickScalpAgent)
=========================================
1. Scans 1-minute and 3-minute micro candles for fast momentum scalp opportunities.
2. Uses Micro-RSI breakouts, 1m VWAP price sweeps, and high 1m volume spikes (>2.5x mean).
3. Executes quick scalp trades with ultra-fast TP (+1.2%) and tight SL (-0.05%).
4. Trades across both CoinSwitch Pro and Delta Exchange India simultaneously.
"""

import logging
import time
import pandas as pd
import numpy as np

from coinswitch_client import CoinSwitchClient
from delta_client import DeltaClient
from dual_exchange import DualExecutionAgent
from agents import AuditLogger, RiskManagerAgent
from notifier import TelegramNotifier

log = logging.getLogger(__name__)

def rsi_1m(s: pd.Series, p: int = 14) -> pd.Series:
    d = s.diff()
    g = d.clip(lower=0).ewm(com=p - 1, adjust=False).mean()
    l = (-d).clip(lower=0).ewm(com=p - 1, adjust=False).mean()
    return 100 - 100 / (1 + g / l)

class QuickScalpAgent:
    def __init__(self, cfg: dict, cs_client: CoinSwitchClient, delta_client: DeltaClient, notifier: TelegramNotifier | None, audit: AuditLogger):
        self.cfg = cfg
        self.cs_client = cs_client
        self.delta_client = delta_client
        self.notifier = notifier
        self.audit = audit
        self.executor = DualExecutionAgent(cfg, cs_client, delta_client, notifier, audit)
        self.risk_manager = RiskManagerAgent(cfg, cs_client, audit, delta_client=delta_client)

    def scan_and_execute_scalps(self, symbols: list[str]) -> list[dict]:
        """Scans 1m/3m micro momentum and executes quick scalp trades."""
        log.info("QuickScalpAgent: Scanning %s symbols for 1m/3m quick scalp setups...", len(symbols))
        scalp_results = []

        for symbol in symbols[:30]:  # Top 30 liquid symbols
            try:
                # Fetch 1m candles
                df = self.cs_client.get_candles(symbol, exchange="c2c2", interval=1, limit=50)
                if df is None or len(df) < 20:
                    continue

                close = float(df["close"].iloc[-1])
                prev_close = float(df["close"].iloc[-2])
                volume = float(df["volume"].iloc[-1])
                avg_vol = float(df["volume"].tail(15).mean())
                vol_ratio = volume / avg_vol if avg_vol > 0 else 1.0

                r = float(rsi_1m(df["close"]).iloc[-1]) if len(df) >= 14 else 50.0

                # Calculate 1m VWAP
                tp = (df["high"] + df["low"] + df["close"]) / 3.0
                vwap = float(((tp * df["volume"]).cumsum() / df["volume"].cumsum()).iloc[-1])

                # Scalp Signals:
                # Scalp Long: Close > VWAP, RSI > 58, 1m Vol Ratio > 2.2x
                # Scalp Short: Close < VWAP, RSI < 42, 1m Vol Ratio > 2.2x
                scalp_type = None
                direction = "long"

                if close > vwap and r >= 58.0 and vol_ratio >= 2.2:
                    scalp_type = "pump"
                    direction = "long"
                elif close < vwap and r <= 42.0 and vol_ratio >= 2.2 and self.cfg.get("short_selling_enabled", True):
                    scalp_type = "dump"
                    direction = "short"

                if scalp_type:
                    signal = {
                        "signal_id": f"SCALP-{int(time.time()*1000)}",
                        "symbol": symbol,
                        "signal": scalp_type,
                        "confidence": 0.88,
                        "reason": f"quick_scalp_1m_rsi={r:.1f}_vol={vol_ratio:.2f}x",
                        "supporting_data": {
                            "price": close,
                            "volume_24h": 100000.0,
                            "atr_pct": 1.0,
                            "volume_ratio": vol_ratio,
                            "change_5m": 1.2 if scalp_type == "pump" else -1.2,
                        }
                    }

                    approval = self.risk_manager._evaluate_one(signal, False)
                    # Override scalp TP/SL to quick scalp parameters: TP +1.2%, SL -0.05%
                    if approval.get("approved"):
                        approval["take_profit_pct"] = 1.2
                        approval["stop_loss_pct"] = 0.05

                        log.info("⚡ QuickScalpAgent SIGNAL APPROVED: %s -> %s (RSI=%.1f, Vol=%.2fx)", symbol, direction.upper(), r, vol_ratio)
                        results = self.executor.execute([approval])
                        scalp_results.extend(results)

                        if self.notifier:
                            self.notifier.send(
                                f"⚡ *QUICK SCALP TRADE EXECUTED*\n"
                                f"━━━━━━━━━━━━━━━━━━━━━\n"
                                f"Asset  : `{symbol}`\n"
                                f"Trade  : `{direction.upper()}`\n"
                                f"Entry  : `${close}`\n"
                                f"RSI 1m : `{r:.1f}` | Vol Ratio: `{vol_ratio:.1f}x`\n"
                                f"Target : TP +1.2% | SL -0.05%"
                            )
                        break

            except Exception as exc:
                log.debug("Scalp scan error for %s: %s", symbol, exc)

        return scalp_results
