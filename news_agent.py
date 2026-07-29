"""
Forex Calendar Economic News Fetcher
====================================
Fetches high-impact economic events (US CPI, NFP, FOMC, Rate Decisions)
from ForexFactory / Economic Calendar APIs. Provides sentiment and volatility
impact factors to the bot's signal and risk engine.
"""

import logging
import requests
from datetime import datetime, timezone

log = logging.getLogger(__name__)

HIGH_IMPACT_EVENTS = {
    "cpi": "US Inflation Rate (CPI)",
    "nfp": "Non-Farm Payrolls (NFP)",
    "fomc": "FOMC Interest Rate Decision",
    "gdp": "Gross Domestic Product (GDP)",
    "ppi": "Producer Price Index (PPI)",
    "unemployment": "Unemployment Rate",
    "powell": "Fed Chair Speech",
}


class ForexCalendarAgent:
    """Fetches economic calendar events and scores market sentiment / volatility impact."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self._cached_events = []
        self._last_fetch = 0.0

    def fetch_economic_calendar(self) -> list[dict]:
        """Fetch high-impact Forex economic events for the current day/week."""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get("https://raw.githubusercontent.com/rreichel3/US-Economic-Events/main/events.json", headers=headers, timeout=5)
            if resp.status_code == 200:
                events = resp.json()
                high_impact = []
                today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

                for item in events:
                    impact = str(item.get("impact", "")).lower()
                    title = str(item.get("title", "")).lower()
                    date = str(item.get("date", ""))

                    # Filter for High Impact USD/Macro events
                    if impact in ("high", "red") or any(k in title for k in HIGH_IMPACT_EVENTS.keys()):
                        high_impact.append({
                            "title": item.get("title"),
                            "country": item.get("country", "USD"),
                            "date": date,
                            "impact": "HIGH",
                            "forecast": item.get("forecast", ""),
                            "previous": item.get("previous", ""),
                        })

                self._cached_events = high_impact
                log.info("Forex Calendar: fetched %s high-impact events", len(high_impact))
                return high_impact
        except Exception as exc:
            log.warning("Forex Calendar fetch notice: %s. Using default macro volatility engine.", exc)
            return []

    def evaluate_news_impact(self) -> dict:
        """
        Evaluates current macro news volatility factor.
        Returns:
            volatility_multiplier: 1.0 (normal) to 1.25 (high-volatility news event)
            news_bias: 'neutral', 'high_volatility'
        """
        events = self.fetch_economic_calendar()
        if not events:
            return {"volatility_multiplier": 1.0, "news_bias": "neutral", "active_events": []}

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_events = [e for e in events if now_str in e.get("date", "")]

        if today_events:
            log.info("Forex Calendar: %s High-Impact Macro Economic events active today!", len(today_events))
            return {
                "volatility_multiplier": 1.25,  # Expect higher volatility expansion
                "news_bias": "high_volatility",
                "active_events": [e["title"] for e in today_events]
            }

        return {"volatility_multiplier": 1.0, "news_bias": "neutral", "active_events": []}
