"""
news_telegram_broadcaster.py — Dedicated Telegram Broadcaster for News & Forex Signals
=====================================================================================
Runs independently for the Live News, Economic Calendar & Forex Signals Channel.
Isolated from CoinSwitch / Delta crypto trade execution bot.
"""

import os
import logging
import requests
import time
from typing import Optional, Dict, Any

log = logging.getLogger("news_telegram")

# Environment variable keys specifically for News & Forex Channel
NEWS_BOT_TOKEN = (
    os.getenv("NEWS_BOT_TOKEN") or 
    os.getenv("NEWS_TELEGRAM_BOT_TOKEN") or 
    os.getenv("FOREX_NEWS_BOT_TOKEN") or 
    ""
).strip()

NEWS_CHAT_ID = (
    os.getenv("NEWS_CHAT_ID") or 
    os.getenv("NEWS_TELEGRAM_CHAT_ID") or 
    os.getenv("FOREX_NEWS_CHAT_ID") or 
    ""
).strip()

class NewsTelegramBroadcaster:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or NEWS_BOT_TOKEN
        self.chat_id = chat_id or NEWS_CHAT_ID
        self.is_active = bool(self.bot_token and self.chat_id)
        if self.is_active:
            log.info(f"✅ News & Forex Telegram Broadcaster initialized for channel: {self.chat_id}")
        else:
            log.info("ℹ️ News Telegram Broadcaster in standby (Set NEWS_BOT_TOKEN & NEWS_CHAT_ID to activate)")

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        if not self.is_active:
            return False
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": False
            }
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                log.info("📢 News Telegram message dispatched successfully")
                return True
            else:
                log.warning(f"Telegram News API response {res.status_code}: {res.text}")
                return False
        except Exception as e:
            log.error(f"Failed to send Telegram news message: {e}")
            return False

    def broadcast_breaking_news(self, article: Dict[str, Any], ai_insight: Optional[str] = None) -> bool:
        title = article.get("title", "").strip()
        source = article.get("source") or article.get("source_name") or "Market Wire"
        link = article.get("url") or article.get("link") or ""
        sentiment = article.get("sentiment", "NEUTRAL").upper()
        category = article.get("category", "MARKET").upper()
        
        sent_icon = "🟢 BULLISH" if "BULL" in sentiment else ("🔴 BEARISH" if "BEAR" in sentiment else "⚪ NEUTRAL")
        cat_badge = "🇮🇳 INDIAN EQUITIES & REGULATORY" if category == "INDIA" else f"🌐 {category}"
        
        msg = (
            f"📰 <b>BREAKING NEWS ALERT • {source}</b>\n"
            f"🏷 <i>{cat_badge}</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>{title}</b>\n\n"
            f"📊 <b>Sentiment:</b> {sent_icon}\n"
        )
        if ai_insight:
            msg += f"🧠 <b>AI Catalyst Insight:</b> <i>{ai_insight}</i>\n"
        if link:
            msg += f"\n🔗 <a href='{link}'>Read Full Article</a>\n"
            
        msg += f"\n⚡ <i>TheSmartMag 24/7 Intelligence Wire</i>"
        return self.send_message(msg)

    def broadcast_indian_market_digest(self, indices: Dict[str, Any], top_headlines: List[Dict[str, Any]]) -> bool:
        """Broadcast live Indian Market (NSE/BSE) index scorecard and top market stories."""
        nifty = indices.get("NIFTY 50", {})
        bank_nifty = indices.get("BANK NIFTY", {})
        sensex = indices.get("SENSEX", {})
        usdinr = indices.get("USD/INR", {})
        
        def fmt_chg(c):
            return f"+{c}% 🟢" if c > 0 else (f"{c}% 🔴" if c < 0 else "0.00% ⚪")
            
        msg = (
            f"🇮🇳 <b>INDIAN MARKET INTEL • NSE / BSE LIVE RADAR</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>NIFTY 50:</b> <code>{nifty.get('price', '—')}</code> ({fmt_chg(nifty.get('change_pct', 0))})\n"
            f"🏦 <b>BANK NIFTY:</b> <code>{bank_nifty.get('price', '—')}</code> ({fmt_chg(bank_nifty.get('change_pct', 0))})\n"
            f"📈 <b>SENSEX:</b> <code>{sensex.get('price', '—')}</code> ({fmt_chg(sensex.get('change_pct', 0))})\n"
            f"💵 <b>USD / INR:</b> <code>₹{usdinr.get('price', '—')}</code> ({fmt_chg(usdinr.get('change_pct', 0))})\n\n"
            f"🔥 <b>TOP INDIAN CATALYST HEADLINES:</b>\n"
        )
        
        for idx, h in enumerate(top_headlines[:4], 1):
            t = h.get("title", "")
            src = h.get("source", "News")
            u = h.get("url", "")
            if u:
                msg += f"{idx}. <a href='{u}'>{t}</a> (<i>{src}</i>)\n"
            else:
                msg += f"{idx}. {t} (<i>{src}</i>)\n"
                
        msg += f"\n⚡ <i>TheSmartMag Dedicated Indian & Global Intel Feed</i>"
        return self.send_message(msg)

    def broadcast_calendar_event(self, event: Dict[str, Any]) -> bool:
        title = event.get("title", "")
        country = event.get("country", "GLOBAL")
        impact = event.get("impact", "High").upper()
        actual = event.get("actual", "N/A")
        forecast = event.get("forecast", "N/A")
        previous = event.get("previous", "N/A")
        
        imp_icon = "🔴 HIGH IMPACT" if "HIGH" in impact else "🟠 MEDIUM IMPACT"
        
        msg = (
            f"🏛 <b>ECONOMIC CALENDAR RELEASE • {country}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>{title}</b>\n\n"
            f"⚠️ <b>Impact:</b> {imp_icon}\n"
            f"📈 <b>Actual:</b> <code>{actual}</code>\n"
            f"🎯 <b>Forecast:</b> <code>{forecast}</code>\n"
            f"⏮ <b>Previous:</b> <code>{previous}</code>\n\n"
            f"⚡ <i>TheSmartMag Live Macro Catalyst Stream</i>"
        )
        return self.send_message(msg)

    def broadcast_forex_macro_signal(self, signal: Dict[str, Any]) -> bool:
        pair = signal.get("symbol", "EUR/USD")
        direction = signal.get("direction", "BUY").upper()
        entry = signal.get("entry", "0.0")
        tp1 = signal.get("tp1", "0.0")
        tp2 = signal.get("tp2", "0.0")
        sl = signal.get("sl", "0.0")
        reason = signal.get("reason", "Institutional Order Flow & Macro Catalyst")
        levels = signal.get("levels", {})
        
        dir_icon = "🟢 BUY / LONG" if direction == "BUY" else "🔴 SELL / SHORT"
        
        msg = (
            f"⚡ <b>LIVE FOREX & MACRO SIGNAL</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Asset:</b> <code>{pair}</code>\n"
            f"🎯 <b>Direction:</b> {dir_icon}\n\n"
            f"🔹 <b>Entry Zone:</b> <code>{entry}</code>\n"
            f"🎯 <b>Target 1:</b> <code>{tp1}</code>\n"
            f"🎯 <b>Target 2:</b> <code>{tp2}</code>\n"
            f"🛑 <b>Stop Loss:</b> <code>{sl}</code>\n\n"
            f"🧠 <b>Catalyst & Technicals:</b>\n<i>{reason}</i>\n"
        )
        
        if levels.get("beginner"):
            msg += f"\n🔰 <b>Beginner Guide:</b> {levels['beginner']}\n"
        if levels.get("experienced"):
            msg += f"🏛 <b>Institutional Edge:</b> {levels['experienced']}\n"
            
        msg += f"\n⚡ <i>TheSmartMag Dedicated Forex & Macro Channel</i>"
        return self.send_message(msg)

# Global Instance
news_broadcaster = NewsTelegramBroadcaster()