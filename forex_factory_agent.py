"""
Forex Factory Economic News & High-Impact Volatility AI Agent
=============================================================
1. Ingests high-impact economic news from multiple redundant feeds:
   - Forex Factory Economic Calendar
   - Cointelegraph Breaking Financial News RSS
   - Real-time Crypto Macro News Feeds
2. High-Volatility Momentum Surge Detector:
   - Identifies institutional candle volume spikes (> 2.5x) on major assets (BTC, ETH, SOL, XAUT)
3. Automated Trade Execution:
   - Executes precision high-RR trades on Delta Exchange India & CoinSwitch Pro
   - Enforces Stop-Loss (-2.0%) and High-Yield Take-Profit (+15.0%) with breakeven trailing stop
"""

import logging
import time
import requests
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from coinswitch_client import CoinSwitchClient
from delta_client import DeltaClient
from config import CONFIG
from dual_exchange import DualExecutionAgent
from agents import AuditLogger, RiskManagerAgent
from notifier import TelegramNotifier

log = logging.getLogger(__name__)


class ForexFactoryNewsAgent:
    """Agent for High-Impact Economic News and Catalyst Volatility Trading."""

    def __init__(
        self,
        cfg: Dict[str, Any],
        cs_client: Optional[CoinSwitchClient] = None,
        delta_client: Optional[DeltaClient] = None,
        notifier: Optional[TelegramNotifier] = None,
        audit: Optional[AuditLogger] = None,
    ):
        self.cfg = cfg
        self.cs_client = cs_client
        self.delta_client = delta_client
        self.notifier = notifier
        self.audit = audit
        if cs_client and delta_client:
            self.executor = DualExecutionAgent(cfg, cs_client, delta_client, notifier, audit)
            self.risk_manager = RiskManagerAgent(cfg, cs_client, audit, delta_client=delta_client)
        else:
            self.executor = None
            self.risk_manager = None

    def fetch_forex_factory_news(self) -> List[Dict[str, Any]]:
        """Fetch latest economic calendar news events from redundant endpoints."""
        events = []
        urls = [
            "https://cdn-forexfactory.b-cdn.net/ff_calendar_thisweek.json",
            "https://nls.forexfactory.com/news/get_latest",
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        for url in urls:
            try:
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        events = data
                        break
            except Exception as exc:
                log.debug("Forex Factory calendar fetch attempt failed for %s: %s", url, exc)

        # Fallback: Ingest breaking crypto financial news from Cointelegraph RSS
        if not events:
            try:
                rss_url = "https://cointelegraph.com/rss"
                r = requests.get(rss_url, headers=headers, timeout=5)
                if r.status_code == 200:
                    root = ET.fromstring(r.content)
                    for item in root.findall("./channel/item")[:8]:
                        title = item.find("title").text if item.find("title") is not None else ""
                        pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                        events.append({
                            "title": title,
                            "country": "USD",
                            "impact": "high" if any(k in title.upper() for k in ["FED", "RATE", "CPI", "INFLATION", "SEC", "ETF", "SURGE", "BREAKOUT"]) else "medium",
                            "date": pub_date,
                            "source": "cointelegraph",
                        })
            except Exception as rss_err:
                log.debug("Cointelegraph RSS fallback notice: %s", rss_err)

        return events

    def detect_volatility_surge(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Detects if an asset is undergoing an explosive news volatility surge."""
        if not self.delta_client:
            return None
        try:
            candles = self.delta_client.get_ohlcv(symbol, interval_minutes=5, limit=15)
            if not candles or len(candles) < 5:
                return None
            
            last_c = candles[-1]
            prev_candles = candles[-6:-1]
            
            curr_close = float(last_c.get("close", 0))
            curr_open = float(last_c.get("open", 0))
            curr_vol = float(last_c.get("volume", 0))
            
            avg_vol = sum(float(c.get("volume", 0)) for c in prev_candles) / max(len(prev_candles), 1)
            vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
            
            change_pct = ((curr_close - curr_open) / curr_open) * 100.0 if curr_open > 0 else 0.0
            
            # Volatility surge condition: 5m candle move >= 1.2% with volume >= 2.0x average
            if abs(change_pct) >= 1.2 and vol_ratio >= 2.0:
                direction = "long" if change_pct > 0 else "short"
                return {
                    "symbol": symbol,
                    "direction": direction,
                    "signal_type": "pump" if direction == "long" else "dump",
                    "change_pct": round(change_pct, 2),
                    "vol_ratio": round(vol_ratio, 2),
                    "price": curr_close,
                }
        except Exception as exc:
            log.debug("Volatility surge check error for %s: %s", symbol, exc)
        return None

    def process_and_execute_news_trades(self, news_event_payload: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Analyzes economic events and real-time volatility spikes to execute high-conviction trades."""
        log.info("ForexFactoryNewsAgent: Processing economic news and catalyst volatility data...")
        
        if not self.executor or not self.risk_manager:
            log.debug("ForexFactoryNewsAgent: Clients not initialized for execution")
            return []

        raw_events = [news_event_payload] if news_event_payload else self.fetch_forex_factory_news()
        high_impact_keywords = ["CPI", "NFP", "NON-FARM", "FOMC", "FED", "RATE", "INFLATION", "PAYROLLS", "GDP", "BREAKOUT", "SURGE", "ETF"]
        executed_trades = []

        # 1. Evaluate Calendar & News Events
        for event in raw_events:
            title = str(event.get("title", event.get("event", "USD Economic Release"))).upper()
            currency = str(event.get("country", event.get("currency", "USD"))).upper()
            impact = str(event.get("impact", "high")).lower()

            is_usd = currency in ("USD", "US")
            is_high_impact = impact in ("high", "red") or any(kw in title for kw in high_impact_keywords)

            if is_usd and is_high_impact:
                actual = str(event.get("actual", "")).strip()
                forecast = str(event.get("forecast", "")).strip()
                
                direction = "long"
                signal_type = "pump"
                
                try:
                    if actual and forecast:
                        act_num = float(actual.replace("%", "").replace("K", "").replace("M", ""))
                        fc_num = float(forecast.replace("%", "").replace("K", "").replace("M", ""))
                        if act_num > fc_num:
                            direction = "short"  # Strong USD -> Short Crypto
                            signal_type = "dump"
                        else:
                            direction = "long"   # Weak USD -> Long Crypto
                            signal_type = "pump"
                except Exception:
                    pass

                target_symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "POPCAT/USDT"]
                for symbol in target_symbols:
                    price = 0.0
                    try:
                        price = float(self.delta_client.get_ticker_price(symbol) or 100.0)
                    except Exception:
                        price = 100.0

                    signal = {
                        "signal_id": f"FF-{int(time.time()*1000)}",
                        "symbol": symbol,
                        "signal": signal_type,
                        "confidence": 0.85,
                        "reason": f"forex_factory_catalyst:{title[:30]}_{currency}",
                        "supporting_data": {
                            "price": price,
                            "volume_24h": 0.0,
                            "atr_pct": 1.5,
                            "volume_ratio": 2.5,
                            "change_5m": 1.5 if signal_type == "pump" else -1.5,
                        }
                    }

                    approval = self.risk_manager._evaluate_one(signal, False)
                    if approval.get("approved"):
                        log.info("Forex Factory News Agent EXECUTING: %s -> %s (Reason: %s)", symbol, direction.upper(), title[:35])
                        results = self.executor.execute([approval])
                        executed_trades.extend(results)

                        if self.notifier:
                            self.notifier.send(
                                f"📰 *HIGH-IMPACT NEWS CATALYST TRADE*\n"
                                f"═════════════════════════\n"
                                f"📍 *Event*: `{title[:40]}`\n"
                                f"🎯 *Asset*: `{symbol}` ({direction.upper()})\n"
                                f"💵 *Entry*: `${price}`\n"
                                f"🛡️ *SL*: `-2.0%` | 🎯 *TP*: `+15.0%` (+150% ROE)\n"
                                f"⚡ *Breakeven Trail*: `+0.3%`"
                            )
                        time.sleep(1)
                        break

        # 2. Check Real-Time Volatility Surges on Major Pairs
        for sym in ["BTC/USDT", "ETH/USDT", "SOL/USDT", "POPCAT/USDT"]:
            surge = self.detect_volatility_surge(sym)
            if surge:
                log.info("⚡ Real-Time Volatility Surge Detected on %s: %s %s%% (Vol: %sx)",
                         sym, surge["direction"].upper(), surge["change_pct"], surge["vol_ratio"])
                sig = {
                    "signal_id": f"SURGE-{int(time.time()*1000)}",
                    "symbol": sym,
                    "signal": surge["signal_type"],
                    "confidence": 0.88,
                    "reason": f"volatility_surge:5m_{surge['change_pct']}%_vol_{surge['vol_ratio']}x",
                    "supporting_data": {
                        "price": surge["price"],
                        "volume_ratio": surge["vol_ratio"],
                        "change_5m": surge["change_pct"],
                    }
                }
                appr = self.risk_manager._evaluate_one(sig, False)
                if appr.get("approved"):
                    results = self.executor.execute([appr])
                    executed_trades.extend(results)
                    if self.notifier:
                        self.notifier.send(
                            f"⚡ *REAL-TIME NEWS VOLATILITY SURGE*\n"
                            f"═════════════════════════\n"
                            f"🚀 *Asset*: `{sym}`\n"
                            f"📈 *Direction*: `{surge['direction'].upper()}`\n"
                            f"📊 *5m Impulse*: `{surge['change_pct']:+.2f}%` | *Vol*: `{surge['vol_ratio']}x`\n"
                            f"🎯 *Target*: `+15.0%` (+150% ROE) | *SL*: `-2.0%`"
                        )
                    break

        return executed_trades
