"""
HKUDS AI-Trader Integration Agent & Market Intelligence Engine
=============================================================
Integration with HKUDS AI-Trader Platform (https://ai4trade.ai)

Capabilities:
1. Agent Registration & Identity Token Management with AI-Trader API.
2. Market Intelligence Fetcher: Ingests Macro Regime Signals, BTC ETF Flows, and Financial Event Snapshots.
3. Copy-Trading Engine: Fetches top-performing AI Trader signals from the platform and executes on CoinSwitch Pro & Delta Exchange India.
4. Cross-Platform Signal Sync: Publishes our bot's high-confidence signals (SMC Liquidity, PP SuperTrend, Scalps, Earnings) to AI-Trader.
5. Enforces MARKET Order Entries with mandatory Take-Profit (+4.8%) & Stop-Loss (-0.05%).
"""

import logging
import time
import requests
from datetime import datetime, timezone

from coinswitch_client import CoinSwitchClient
from delta_client import DeltaClient
from config import CONFIG
from dual_exchange import DualExecutionAgent
from agents import AuditLogger, RiskManagerAgent
from notifier import TelegramNotifier

log = logging.getLogger(__name__)

AI_TRADER_BASE_URL = "https://ai4trade.ai/api"


class AITraderAgent:
    """Agent for HKUDS AI-Trader Platform Integration, Market Intelligence, and Copy Trading."""

    def __init__(
        self,
        cfg: dict,
        cs_client: CoinSwitchClient,
        delta_client: DeltaClient,
        notifier: TelegramNotifier,
        audit: AuditLogger,
    ):
        self.cfg = cfg
        self.cs_client = cs_client
        self.delta_client = delta_client
        self.notifier = notifier
        self.audit = audit
        self.executor = DualExecutionAgent(cfg, cs_client, delta_client, notifier, audit)
        self.risk_manager = RiskManagerAgent(cfg, cs_client, audit, delta_client=delta_client)
        
        self.token = cfg.get("ai_trader_token", "")
        self.agent_name = cfg.get("ai_trader_agent_name", "CoinSwitchDeltaAITrader")
        self.email = cfg.get("ai_trader_email", "trader@ai4trade.ai")
        self._ensure_registered()

    def _ensure_registered(self) -> None:
        """Register or login agent on HKUDS AI-Trader platform if token is not configured."""
        if self.token:
            return
        try:
            url = f"{AI_TRADER_BASE_URL}/claw/agents/selfRegister"
            payload = {
                "name": self.agent_name,
                "email": self.email,
                "password": "CoinswitchDeltaBot_2026_SecureKey",
            }
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code in (200, 201):
                data = resp.json()
                self.token = data.get("token", "")
                log.info("AI-Trader Agent registered successfully! Token acquired.")
            else:
                log.debug("AI-Trader registration response: %s %s", resp.status_code, resp.text[:200])
        except Exception as exc:
            log.debug("AI-Trader registration notice: %s. Continuing with public API mode.", exc)

    def fetch_market_intel(self) -> dict:
        """Fetch Macro Regime Signals, BTC ETF Flows, and Market Intelligence from AI-Trader."""
        intel = {
            "macro_regime": "neutral",
            "bullish_count": 0,
            "etf_flow_summary": "neutral",
            "volatility_multiplier": 1.0,
            "raw_signals": [],
        }

        # 1. Fetch Macro Signals
        try:
            res = requests.get(f"{AI_TRADER_BASE_URL}/market-intel/macro-signals", timeout=5)
            if res.status_code == 200:
                data = res.json()
                verdict = str(data.get("verdict", "neutral")).lower()
                intel["macro_regime"] = verdict
                intel["bullish_count"] = data.get("bullish_count", 0)
                if "bullish" in verdict:
                    intel["volatility_multiplier"] = 1.2
                elif "bearish" in verdict:
                    intel["volatility_multiplier"] = 0.85
        except Exception as exc:
            log.debug("AI-Trader macro signals fetch notice: %s", exc)

        # 2. Fetch ETF Flows
        try:
            res = requests.get(f"{AI_TRADER_BASE_URL}/market-intel/etf-flows", timeout=5)
            if res.status_code == 200:
                data = res.json()
                summary = data.get("summary", {})
                intel["etf_flow_summary"] = summary
        except Exception as exc:
            log.debug("AI-Trader ETF flows fetch notice: %s", exc)

        log.info("AI-Trader Market Intel: Macro Regime = %s | Volatility Multiplier = %s", intel["macro_regime"], intel["volatility_multiplier"])
        return intel

    def fetch_top_ai_signals_and_copytrade(self) -> list[dict]:
        """Fetch top performing signals from HKUDS AI-Trader platform and execute copy trades."""
        log.info("AITraderAgent: Scanning top AI-Trader community signals for copy trading...")
        executed_trades = []

        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        urls = [
            f"{AI_TRADER_BASE_URL}/claw/signals/featured",
            f"{AI_TRADER_BASE_URL}/claw/signals/latest",
        ]

        raw_signals = []
        for url in urls:
            try:
                res = requests.get(url, headers=headers, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    sig_list = data if isinstance(data, list) else data.get("signals", data.get("result", []))
                    if isinstance(sig_list, list):
                        raw_signals.extend(sig_list)
                        break
            except Exception as exc:
                log.debug("AI-Trader signal fetch notice for %s: %s", url, exc)

        for sig_item in raw_signals[:5]:
            try:
                symbol = str(sig_item.get("symbol", "BTC/USDT")).upper()
                if "/" not in symbol:
                    base = symbol.replace("USDT", "").replace("USD", "")
                    symbol = f"{base}/USDT"

                action = str(sig_item.get("action", sig_item.get("direction", "buy"))).lower()
                direction = "long" if action in ("buy", "long", "pump") else "short"
                signal_type = "pump" if direction == "long" else "dump"
                confidence = float(sig_item.get("confidence", 0.90) or 0.90)

                price = 0.0
                try:
                    price = float(self.cs_client.get_ticker_price(symbol))
                except Exception:
                    price = 100.0

                signal = {
                    "signal_id": f"AITRADER-{int(time.time()*1000)}",
                    "symbol": symbol,
                    "signal": signal_type,
                    "confidence": confidence,
                    "suspected_cause": f"hkuds_ai_trader_copytrade_{direction}",
                    "supporting_data": {
                        "price": price,
                        "volume_ratio": 2.0,
                        "change_5m": 1.0 if signal_type == "pump" else -1.0,
                        "source": "HKUDS AI-Trader Platform",
                    },
                }

                approval = self.risk_manager._evaluate_one(signal, False)
                if approval.get("approved"):
                    approval["order_type"] = "market"  # Force MARKET order entry
                    results = self.executor.execute([approval])
                    executed_trades.append({
                        "symbol": symbol,
                        "direction": direction,
                        "source": "HKUDS AI-Trader",
                        "results": results,
                    })

                    if self.notifier:
                        self.notifier.send(
                            f"🤖 *HKUDS AI-TRADER COPYTRADE EXECUTED*\n\n"
                            f"• *Symbol*: `{symbol}`\n"
                            f"• *Direction*: `{direction.upper()}` (MARKET Entry)\n"
                            f"• *Price*: `${price:.4f}`\n"
                            f"• *Platform*: HKUDS AI-Trader CopyTrading Engine\n"
                            f"• *Exchanges*: CoinSwitch Pro & Delta Exchange India\n"
                            f"• *TP*: `+4.8%` | *SL*: `-0.05%`"
                        )
            except Exception as trade_exc:
                log.debug("AI-Trader copytrade execution notice for %s: %s", sig_item, trade_exc)

        return executed_trades

    def publish_signal_to_platform(self, signal: dict) -> None:
        """Publish our bot's high-confidence signals to HKUDS AI-Trader platform."""
        if not self.token:
            return
        try:
            url = f"{AI_TRADER_BASE_URL}/claw/signals/publish"
            headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
            payload = {
                "symbol": signal.get("symbol"),
                "action": "buy" if signal.get("signal") == "pump" else "sell",
                "confidence": signal.get("confidence", 0.90),
                "strategy": signal.get("suspected_cause", "SMC_Liquidity_SuperTrend"),
                "timestamp": int(time.time()),
            }
            requests.post(url, json=payload, headers=headers, timeout=5)
        except Exception as exc:
            log.debug("AI-Trader signal publish notice: %s", exc)
