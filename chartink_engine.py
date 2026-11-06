"""
Chartink Real-Time Scanner Engine & Telegram Signal Broadcaster
Dashboard: https://chartink.com/dashboard/447734 (Atlas downtowon)
Scans 9 real-time intraday / swing strategies on Indian NSE / F&O equities:
1. Avg sector change
2. Avg sector change minus
3. Daily Volume increase in %
4. F&O Gainers
5. Cash Stocks near 52 week high
6. Futures Advancing V Declining
7. Top Losers %
8. Open Interest Options Stocks
9. Intraday - Narrow CPR & Monthly/Weekly Breakout

Broadcasts validated stock breakout alerts to Telegram channel @FOREXINDIAN_BOT
"""

import requests
import re
import json
import time
import logging
from typing import Dict, List, Any, Optional

log = logging.getLogger("chartink_engine")

CHARTINK_DASHBOARD_URL = "https://chartink.com/dashboard/447734"
CHARTINK_PROCESS_URL = "https://chartink.com/screener/process"

SCANNERS = [
    {
        "id": "cpr_breakout",
        "name": "Intraday CPR & Weekly/Monthly Breakout",
        "category": "INTRADAY BREAKOUT",
        "scan_clause": "( {33489} ( ( ( ( latest high + latest low ) / 2 ) < ( ( ( latest high + latest low + latest close ) / 3 ) - ( ( ( latest high + latest low + latest close ) / 3 ) * .003 ) ) ) and ( latest close >= 100 ) and ( latest volume >= latest sma( volume, 5 ) ) ) )"
    },
    {
        "id": "near_52w_high",
        "name": "Cash Stocks Near 52-Week High",
        "category": "MOMENTUM HIGH",
        "scan_clause": "( {33489} ( latest close > 100 and latest volume > 1300000 and latest close >= latest max( 250 , latest high ) * 0.90 ) )"
    },
    {
        "id": "volume_surge",
        "name": "Daily Volume Surge (% Expansion)",
        "category": "VOLUME SPIKE",
        "scan_clause": "( {33489} ( latest volume > 10000 and latest volume > 1 day ago sma( latest volume, 20 ) * 1.5 ) )"
    },
    {
        "id": "fo_gainers",
        "name": "F&O Top Gainers",
        "category": "DERIVATIVES",
        "scan_clause": "( {33489} ( latest close > 1 day ago close * 1.02 and latest volume > 500000 ) )"
    },
    {
        "id": "oi_options",
        "name": "Options Open Interest & Vol Expansion",
        "category": "OPTIONS OI",
        "scan_clause": "( {33489} ( latest volume > latest ema( close, 10 ) * 2 and ( latest close > 1 day ago close * 1.02 or latest close < 1 day ago close * 0.98 ) ) )"
    },
    {
        "id": "top_losers",
        "name": "Top F&O Shorting / Breakdown Candidates",
        "category": "SHORT BREAKDOWN",
        "scan_clause": "( {33489} ( daily close > 100 and daily close < 1 day ago close and daily volume > 1500000 and daily \"close - 1 candle ago close / 1 candle ago close * 100\" < -2 ) )"
    }
]

# Cache holding live data for website UI
_CHARTINK_CACHE: Dict[str, Any] = {
    "timestamp": 0,
    "dashboard_id": 447734,
    "dashboard_name": "Atlas downtowon",
    "dashboard_url": CHARTINK_DASHBOARD_URL,
    "total_scanners": len(SCANNERS),
    "scanners": []
}

class ChartinkRealtimeScanner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": CHARTINK_DASHBOARD_URL,
        })
        self.csrf_token: Optional[str] = None
        self._last_csrf_time = 0

    def _refresh_csrf(self) -> bool:
        """Fetches fresh CSRF token and session cookies from Chartink."""
        try:
            r = self.session.get(CHARTINK_DASHBOARD_URL, timeout=12)
            if r.status_code == 200:
                match = re.search(r'name="csrf-token"\s+content="([^"]+)"', r.text)
                if match:
                    self.csrf_token = match.group(1)
                    self._last_csrf_time = time.time()
                    return True
        except Exception as e:
            log.warning(f"Failed to refresh Chartink CSRF token: {e}")
        return False

    def scan_clause(self, clause: str) -> List[Dict[str, Any]]:
        """Executes a scanner clause on Chartink with automatic CSRF refresh."""
        if not self.csrf_token or (time.time() - self._last_csrf_time > 1800):
            self._refresh_csrf()

        headers = {
            "X-CSRF-TOKEN": self.csrf_token or "",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        try:
            resp = self.session.post(
                CHARTINK_PROCESS_URL,
                headers=headers,
                data={"scan_clause": clause},
                timeout=15
            )
            if resp.status_code == 419:  # CSRF expired
                self._refresh_csrf()
                headers["X-CSRF-TOKEN"] = self.csrf_token or ""
                resp = self.session.post(
                    CHARTINK_PROCESS_URL,
                    headers=headers,
                    data={"scan_clause": clause},
                    timeout=15
                )

            if resp.status_code == 200:
                return resp.json().get("data", [])
            else:
                log.warning(f"Chartink query returned status {resp.status_code}")
        except Exception as e:
            log.error(f"Error querying Chartink: {e}")
        return []

    def fetch_all_dashboard_scanners(self) -> Dict[str, Any]:
        """Runs all 6 key scanners from Dashboard 447734 and returns structured results."""
        global _CHARTINK_CACHE
        scanner_results = []
        new_signals_for_telegram = []

        for sc in SCANNERS:
            stocks = self.scan_clause(sc["scan_clause"])
            # Format stocks
            formatted_stocks = []
            for s in stocks[:15]:
                formatted_stocks.append({
                    "symbol": s.get("nsecode") or s.get("name"),
                    "name": s.get("name"),
                    "price": float(s.get("close") or 0.0),
                    "change_pct": float(s.get("per_chg") or 0.0),
                    "volume": int(s.get("volume") or 0),
                })
            
            # Select top picks for Telegram broadcast
            if formatted_stocks and sc["id"] in ("cpr_breakout", "near_52w_high", "volume_surge"):
                for st in formatted_stocks[:2]:
                    if abs(st["change_pct"]) >= 1.5:
                        new_signals_for_telegram.append({
                            "scanner": sc["name"],
                            "category": sc["category"],
                            "symbol": st["symbol"],
                            "price": st["price"],
                            "change_pct": st["change_pct"],
                            "volume": st["volume"]
                        })

            scanner_results.append({
                "id": sc["id"],
                "name": sc["name"],
                "category": sc["category"],
                "count": len(stocks),
                "stocks": formatted_stocks
            })

        _CHARTINK_CACHE = {
            "timestamp": int(time.time()),
            "dashboard_id": 447734,
            "dashboard_name": "Atlas downtowon",
            "dashboard_url": CHARTINK_DASHBOARD_URL,
            "total_scanners": len(SCANNERS),
            "scanners": scanner_results
        }

        # Broadcast new high-conviction breakout signals to Telegram
        if new_signals_for_telegram:
            self.broadcast_signals_to_telegram(new_signals_for_telegram)

        return _CHARTINK_CACHE

    def broadcast_signals_to_telegram(self, signals: List[Dict[str, Any]]) -> None:
        """Dispatches formatted Chartink breakout intelligence to Telegram channel."""
        try:
            from news_telegram_broadcaster import NewsTelegramBroadcaster
            broadcaster = NewsTelegramBroadcaster()
            if not broadcaster.is_active:
                return

            for sig in signals[:4]:
                direction = "BUY / LONG" if sig["change_pct"] >= 0 else "SELL / SHORT"
                tag_icon = "🟢" if sig["change_pct"] >= 0 else "🔴"
                
                msg = (
                    f"🎯 <b>CHARTINK REALTIME RADAR ALERT</b> 🎯\n\n"
                    f"📊 <b>Dashboard:</b> Atlas downtowon (#447734)\n"
                    f"🔍 <b>Strategy:</b> {sig['scanner']} ({sig['category']})\n\n"
                    f"⚡ <b>Stock:</b> #{sig['symbol']}\n"
                    f"{tag_icon} <b>Action:</b> {direction}\n"
                    f"💵 <b>Current LTP:</b> ₹{sig['price']:,.2f}\n"
                    f"📈 <b>24h Change:</b> {sig['change_pct']:+.2f}%\n"
                    f"📊 <b>Traded Volume:</b> {sig['volume']:,}\n\n"
                    f"🛡️ <i>SL Recommendation: 1.5% · TP Target: 3.5% - 6.0%</i>\n"
                    f"🔗 <a href='{CHARTINK_DASHBOARD_URL}'>Open Chartink Dashboard</a>"
                )

                content_key = broadcaster._content_key(f"chartink_{sig['symbol']}_{sig['scanner']}")
                if not broadcaster._is_duplicate(content_key):
                    sent = broadcaster.send_message(msg, parse_mode="HTML")
                    if sent:
                        broadcaster._mark_sent(content_key)
                        log.info(f"Broadcasted Chartink alert for {sig['symbol']} to Telegram!")
        except Exception as e:
            log.error(f"Error broadcasting Chartink to Telegram: {e}")

# Global singleton
chartink_engine = ChartinkRealtimeScanner()
