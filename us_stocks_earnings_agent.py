"""
US Stocks Earnings Trading AI Agent
===================================
DISABLED: This agent has been disabled because it was executing blind phantom
trades every 15-minute cycle with no actual earnings date checking, no
deduplication, and fabricated market data that bypassed risk management.

To re-enable, integrate a real earnings calendar API (e.g., Alpha Vantage)
and add proper deduplication by (stock, earnings_date).
"""

import logging

log = logging.getLogger(__name__)


class USStocksEarningsAgent:
    """DISABLED: Previously fired blind trades every cycle with phantom data."""

    def __init__(self, cfg, cs_client=None, delta_client=None, notifier=None, audit=None):
        self.cfg = cfg
        log.info("USStocksEarningsAgent: DISABLED — no real earnings calendar integrated")

    def fetch_monthly_earnings_calendar(self) -> list[dict]:
        return []

    def process_and_execute_earnings_trades(self, custom_event_payload=None) -> list[dict]:
        log.info("USStocksEarningsAgent: Skipped — agent disabled (no real earnings data source)")
        return []
