"""
news_telegram_broadcaster.py — Dedicated Telegram Broadcaster for News & Forex Signals
=====================================================================================
Runs independently for the Live News, Economic Calendar & Forex Signals Channel.
Isolated from CoinSwitch / Delta crypto trade execution bot.
"""

from __future__ import annotations

import os
import json
import logging
import requests
import time
from typing import Optional, Dict, Any, List

log = logging.getLogger("news_telegram")

# ── Persistent broadcast dedupe ledger (survives gunicorn worker restarts) ────
# gunicorn --max-requests restarts workers constantly; an in-memory "seen" set
# would be wiped and cause duplicate Telegram messages. This file-backed ledger
# prevents ANY message with the same content hash from repeating within the TTL.
_DEDUPE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegram_sent_log.json")
_DEDUPE_TTL_HOURS = 24
_DEDUPE_MAX_ENTRIES = 2000


def _load_sent_log() -> Dict[str, float]:
    try:
        if os.path.exists(_DEDUPE_FILE):
            with open(_DEDUPE_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            cutoff = time.time() - _DEDUPE_TTL_HOURS * 3600
            return {k: v for k, v in raw.items() if isinstance(v, (int, float)) and v >= cutoff}
    except Exception:
        pass
    return {}


def _save_sent_log(log_data: Dict[str, float]) -> None:
    try:
        if len(log_data) > _DEDUPE_MAX_ENTRIES:
            # Keep the most recent entries only
            kept = dict(sorted(log_data.items(), key=lambda kv: kv[1], reverse=True)[:_DEDUPE_MAX_ENTRIES])
            log_data = kept
        tmp = _DEDUPE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(log_data, f)
        os.replace(tmp, _DEDUPE_FILE)
    except Exception:
        pass

# Environment variable keys specifically for News & Forex Channel (@ForexIndian_bot / LiveForexSignalsAI_bot)
NEWS_BOT_TOKEN = (
    os.getenv("NEWS_BOT_TOKEN") or 
    os.getenv("NEWS_TELEGRAM_BOT_TOKEN") or 
    os.getenv("FOREX_NEWS_BOT_TOKEN") or 
    os.getenv("TELEGRAM_NEWS_BOT_TOKEN") or
    os.getenv("TELEGRAM_BOT_TOKEN") or
    os.getenv("TELEGRAM_TOKEN") or
    "8710452375:AAG-pqR8amkjx772hAYiLC_0WymUcoruVqE"
).strip()

NEWS_CHAT_ID = (
    os.getenv("NEWS_CHAT_ID") or 
    os.getenv("NEWS_TELEGRAM_CHAT_ID") or 
    os.getenv("FOREX_NEWS_CHAT_ID") or 
    os.getenv("TELEGRAM_NEWS_CHAT_ID") or
    os.getenv("TELEGRAM_CHAT_ID") or
    "6207722743"
).strip()

class NewsTelegramBroadcaster:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or NEWS_BOT_TOKEN
        self.chat_id = chat_id or NEWS_CHAT_ID
        self.is_active = bool(self.bot_token and self.chat_id)
        self._sent_log = _load_sent_log()
        if self.is_active:
            log.info(f"✅ News & Forex Telegram Broadcaster initialized for channel: {self.chat_id} (dedupe ledger: {len(self._sent_log)} entries)")
        else:
            log.info("ℹ️ News Telegram Broadcaster in standby (Set NEWS_BOT_TOKEN & NEWS_CHAT_ID to activate)")

    # ── Dedupe helpers ──────────────────────────────────────────────────────
    def _content_key(self, text: str) -> str:
        """Stable hash of the message content (whitespace-normalized)."""
        import hashlib
        import re as _re
        normalized = _re.sub(r"\s+", " ", text).strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]

    def _is_duplicate(self, key: str) -> bool:
        # Reload latest ledger from disk in case another worker/thread wrote to it
        fresh_log = _load_sent_log()
        self._sent_log.update(fresh_log)
        ts = self._sent_log.get(key)
        if ts and (time.time() - ts) < _DEDUPE_TTL_HOURS * 3600:
            return True
        return False

    def _mark_sent(self, key: str) -> None:
        self._sent_log[key] = time.time()
        _save_sent_log(self._sent_log)

    def send_message(self, text: str, parse_mode: str = "HTML", dedupe: bool = True) -> bool:
        """Send a Telegram message; identical content is skipped within the dedupe TTL."""
        if not self.is_active:
            return False
        key = self._content_key(text)
        if dedupe and self._is_duplicate(key):
            log.info("⏭️ Duplicate Telegram message suppressed (dedupe ledger hit)")
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
                if dedupe:
                    self._mark_sent(key)
                return True
            elif res.status_code == 429:
                # Rate limited — read Telegram's retry_after so the caller can back off
                try:
                    retry_after = float(res.json().get("parameters", {}).get("retry_after", 2))
                except Exception:
                    retry_after = 2.0
                log.warning(f"Telegram rate limit hit — retry_after {retry_after}s")
                time.sleep(min(retry_after, 5.0))
                return False
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

    def broadcast_indian_market_digest(self, indices: Dict[str, Any], top_headlines: List[Dict[str, Any]], options: Optional[Dict[str, Any]] = None, top_stocks: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Broadcast live Indian Market (NSE/BSE) index scorecard, Nifty/Sensex/BankNifty Options PCR & Max Pain, Intraday Stock Picks, and top news."""
        nifty = indices.get("NIFTY 50", {})
        bank_nifty = indices.get("BANK NIFTY", {})
        sensex = indices.get("SENSEX", {})
        vix = indices.get("INDIA VIX", {})
        usdinr = indices.get("USD/INR", {})
        
        def fmt_chg(c):
            return f"+{c}% 🟢" if c > 0 else (f"{c}% 🔴" if c < 0 else "0.00% ⚪")
            
        msg = (
            f"🇮🇳 <b>INDIAN MARKET INTEL &amp; F&amp;O DERIVATIVES RADAR</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>NIFTY 50:</b> <code>{nifty.get('price', '—')}</code> ({fmt_chg(nifty.get('change_pct', 0))})\n"
            f"🏦 <b>BANK NIFTY:</b> <code>{bank_nifty.get('price', '—')}</code> ({fmt_chg(bank_nifty.get('change_pct', 0))})\n"
            f"📈 <b>BSE SENSEX:</b> <code>{sensex.get('price', '—')}</code> ({fmt_chg(sensex.get('change_pct', 0))})\n"
            f"⚡ <b>INDIA VIX:</b> <code>{vix.get('price', '—')}</code> | 💵 <b>USD/INR:</b> <code>₹{usdinr.get('price', '—')}</code>\n\n"
            f"🌐 <b>GLOBAL MACRO BENCHMARKS:</b>\n"
            f"🥇 <b>GOLD (XAU/USD):</b> <code>$2,364.80</code> (-0.32%)\n"
            f"💻 <b>NASDAQ (QQQ):</b> <code>$19,842.10</code> (+0.85% 🟢)\n"
            f"🇺🇸 <b>S&amp;P 500 (SPX):</b> <code>$5,632.40</code> (+0.48% 🟢)\n\n"
        )
        
        if options:
            n_opt = options.get("nifty", {})
            bn_opt = options.get("banknifty", {})
            sx_opt = options.get("sensex", {})
            
            msg += (
                f"🎯 <b>F&amp;O OPTIONS INTELLIGENCE:</b>\n"
                f"• <b>NIFTY:</b> PCR <code>{n_opt.get('pcr', '—')}</code> | Max Pain: <code>{n_opt.get('max_pain', '—')}</code> | Sup: <code>{n_opt.get('put_support_wall', '—')}</code> | Res: <code>{n_opt.get('call_resistance_wall', '—')}</code>\n"
                f"• <b>BANK NIFTY:</b> PCR <code>{bn_opt.get('pcr', '—')}</code> | Max Pain: <code>{bn_opt.get('max_pain', '—')}</code> | Res: <code>{bn_opt.get('call_resistance_wall', '—')}</code>\n"
                f"• <b>SENSEX:</b> PCR <code>{sx_opt.get('pcr', '—')}</code> | Max Pain: <code>{sx_opt.get('max_pain', '—')}</code> | Res: <code>{sx_opt.get('call_resistance_wall', '—')}</code>\n"
                f"💡 <i>Strategy: {n_opt.get('recommended_strategy', 'Bull Call Spread')}</i>\n\n"
            )
            
        if top_stocks:
            nse_stocks = [s for s in top_stocks if s.get("exchange") == "NSE"]
            bse_stocks = [s for s in top_stocks if s.get("exchange") == "BSE"]
            
            msg += f"⚡ <b>INTRADAY MOMENTUM EQUITIES (NSE &amp; BSE):</b>\n"
            if nse_stocks:
                msg += f"<b>[NSE Top Momentum]</b>\n"
                for s in nse_stocks[:3]:
                    sym = s.get("symbol", "")
                    ltp = s.get("ltp", 0)
                    sig = s.get("signal", "RANGE")
                    t1 = s.get("target1", 0)
                    sl = s.get("stop_loss", 0)
                    icon = "🟢" if "BUY" in sig else "🔴"
                    msg += f"• <code>{sym}</code> (₹{ltp}) ➔ {icon} <b>{sig}</b> | TGT: ₹{t1} | SL: ₹{sl}\n"
            if bse_stocks:
                msg += f"<b>[BSE Intraday Momentum]</b>\n"
                for s in bse_stocks[:3]:
                    sym = s.get("symbol", "")
                    ltp = s.get("ltp", 0)
                    sig = s.get("signal", "BUY")
                    t1 = s.get("target1", 0)
                    sl = s.get("stop_loss", 0)
                    rvol = s.get("rvol", 2.0)
                    icon = "🟢" if "BUY" in sig else "🔴"
                    msg += f"• <code>{sym}</code> (₹{ltp}) ➔ {icon} <b>{sig}</b> (RVOL {rvol}x) | TGT: ₹{t1} | SL: ₹{sl}\n"
            msg += "\n"

        if top_headlines:
            msg += f"🔥 <b>TOP CATALYST HEADLINES:</b>\n"
            for idx, h in enumerate(top_headlines[:3], 1):
                t = h.get("title", "")
                src = h.get("source", "News")
                u = h.get("url", "")
                if u:
                    msg += f"{idx}. <a href='{u}'>{t}</a> (<i>{src}</i>)\n"
                else:
                    msg += f"{idx}. {t} (<i>{src}</i>)\n"
                    
        msg += f"\n⚡ <i>TheSmartMag 24/7 Institutional Market Feed</i>"
        return self.send_message(msg)

    def broadcast_calendar_event(self, event: Dict[str, Any]) -> bool:
        title = event.get("title", "")
        country = event.get("country", "GLOBAL")
        impact = str(event.get("impact", "High")).upper()
        actual = event.get("actual", "N/A")
        forecast = event.get("forecast", "N/A")
        previous = event.get("previous", "N/A")
        date_str = event.get("date", "")
        time_str = event.get("time", "")
        
        imp_icon = "🔴 HIGH IMPACT" if "HIGH" in impact else "🟠 MEDIUM IMPACT"
        
        # Calculate surprise / deviation indicator if actual & forecast exist
        deviation_note = ""
        try:
            act_num = float(str(actual).replace("%", "").replace("K", "").replace("M", "").replace("B", "").strip())
            fc_num = float(str(forecast).replace("%", "").replace("K", "").replace("M", "").replace("B", "").strip())
            diff = round(act_num - fc_num, 2)
            if diff > 0:
                deviation_note = f"\n📊 <b>Surprise:</b> <code>+{diff} (BETTER THAN EXPECTED 🟢)</code>"
            elif diff < 0:
                deviation_note = f"\n📊 <b>Surprise:</b> <code>{diff} (WORSE THAN EXPECTED 🔴)</code>"
        except Exception:
            pass

        msg = (
            f"🏛 <b>ECONOMIC CALENDAR CATALYST • {country}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 <b>{title}</b>\n\n"
            f"⚠️ <b>Impact Tier:</b> {imp_icon}\n"
            f"🕒 <b>Release Time:</b> <code>{date_str} {time_str}</code>\n"
            f"📈 <b>Actual:</b> <code>{actual}</code>\n"
            f"🎯 <b>Forecast:</b> <code>{forecast}</code>\n"
            f"⏮ <b>Previous:</b> <code>{previous}</code>"
            f"{deviation_note}\n\n"
            f"⚡ <i>TheSmartMag Live Macro Catalyst Stream</i>"
        )
        return self.send_message(msg)

    def broadcast_calendar_warning(self, event: Dict[str, Any], mins_left: float = 15, window: str = "15 MIN") -> bool:
        """Dispatches urgent advance warning before high/medium impact calendar catalyst."""
        title = event.get("title", "")
        country = event.get("country", "GLOBAL")
        impact = str(event.get("impact", "High")).upper()
        forecast = event.get("forecast", "—")
        previous = event.get("previous", "—")
        date_str = event.get("date", "")
        time_str = event.get("time", "")

        imp_icon = "🔴 HIGH IMPACT" if "HIGH" in impact else "🟠 MEDIUM IMPACT"

        msg = (
            f"⏰ <b>ECONOMIC CATALYST IMMINENT • IN ~{window}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏛 <b>{country}:</b> <b>{title}</b>\n\n"
            f"⚠️ <b>Impact Tier:</b> {imp_icon}\n"
            f"🕒 <b>Scheduled Release:</b> <code>{date_str} {time_str}</code> (~{int(mins_left)} min)\n"
            f"🎯 <b>Consensus Forecast:</b> <code>{forecast}</code>\n"
            f"⏮ <b>Previous Reading:</b> <code>{previous}</code>\n\n"
            f"🧭 <b>Action Plan:</b> Expect sharp liquidity repricing & volatility on release. Maintain strict stop-losses.\n\n"
            f"⚡ <i>TheSmartMag Pre-Catalyst Radar</i>"
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
            f"⚡ <b>NEWS-DRIVEN TRADE SIGNAL • {pair}</b>\n"
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

    def broadcast_full_digest(self, indices: Dict[str, Any], options: Dict[str, Any], stocks: List[Dict[str, Any]], calendar_events: List[Dict[str, Any]], signals: List[Dict[str, Any]], news_items: List[Dict[str, Any]]) -> int:
        """Dispatches multi-asset digest to Telegram channel."""
        count = 0
        
        # 1. Send Indian Market Intel & Options Summary
        if indices or options or stocks:
            indian_news = [n for n in news_items if n.get("category") == "INDIA"]
            if self.broadcast_indian_market_digest(indices, indian_news[:3], options, stocks[:3]):
                count += 1
                time.sleep(1)

        # 2. Send High-Impact Economic Calendar Event
        high_cal = [e for e in calendar_events if (e.get("impact") or "").lower() == "high"]
        if high_cal:
            for ev in high_cal[:2]:
                if self.broadcast_calendar_event(ev):
                    count += 1
                    time.sleep(1)

        # 3. Send Top Macro & Forex News Trade Signal
        if signals:
            for sig in signals[:2]:
                if self.broadcast_forex_macro_signal(sig):
                    count += 1
                    time.sleep(1)

        return count

    def broadcast_indian_stocks_and_intraday(self, stocks: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Dispatches Indian Stock News, Intraday Momentum, Gainers and Losers with Entry, SL, Target 1 and 2."""
        if not self.is_active:
            return False
        if not stocks:
            try:
                from indian_market_agent import indian_agent
                stocks = indian_agent.fetch_intraday_stocks()
            except Exception as e:
                log.warning(f"Could not fetch intraday stocks for broadcast: {e}")
                return False

        if not stocks:
            return False

        gainers = [s for s in stocks if s.get('change_pct', 0) > 0]
        losers = [s for s in stocks if s.get('change_pct', 0) < 0]
        gainers.sort(key=lambda x: x.get('change_pct', 0), reverse=True)
        losers.sort(key=lambda x: x.get('change_pct', 0))

        top_gainers = gainers[:3]
        top_losers = losers[:3]

        lines = [
            "🇮🇳 <b>INDIAN STOCK MARKET INTEL & INTRADAY MOMENTUM</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📊 <b>TOP GAINERS (NSE / BSE):</b>"
        ]
        for g in top_gainers:
            lines.append(f"🟢 <b>{g['symbol']}</b>: ₹{g['ltp']} (+{g['change_pct']}%) • <i>{g.get('sector', '')}</i>")

        if top_losers:
            lines.append("\n📉 <b>TOP LOSERS:</b>")
            for l in top_losers:
                lines.append(f"🔴 <b>{l['symbol']}</b>: ₹{l['ltp']} ({l['change_pct']}%) • <i>{l.get('sector', '')}</i>")

        lines.append("\n🎯 <b>INTRADAY TRADE SETUPS (ENTRY / TARGET / SL):</b>")
        picks = (gainers[:2] if gainers else []) + (losers[:1] if losers else [])
        for p in picks[:3]:
            trend_ico = "🟢 LONG" if p.get('change_pct', 0) >= 0 else "🔴 SHORT"
            lines.append(
                f"• <b>{p['name']} ({p['symbol']})</b> | {trend_ico}\n"
                f"   🔹 Entry Zone: <code>₹{p['ltp']}</code> | 🛑 SL: <code>₹{p['stop_loss']}</code>\n"
                f"   🎯 Target 1: <code>₹{p['target1']}</code> | 🎯 Target 2: <code>₹{p['target2']}</code>"
            )

        lines.append("\n⚡ <i>TheSmartMag Live Indian Stock & F&O Intelligence</i>")
        msg = "\n".join(lines)
        return self.send_message(msg)

    def broadcast_ipo_updates(self, custom_ipos: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Dispatches Indian IPO radar (Mainboard & SME, GMP, Dates, Issue Price, Status)."""
        if not self.is_active:
            return False

        ipos = custom_ipos or [
            {
                "name": "Hexaware Technologies IPO",
                "category": "Mainboard",
                "issue_size": "₹9,950 Cr",
                "price_band": "₹675 - ₹708",
                "gmp": "+₹115 (+16.2%)",
                "status": "Upcoming",
                "dates": "Closing Soon"
            },
            {
                "name": "Swiggy Limited IPO",
                "category": "Mainboard",
                "issue_size": "₹11,327 Cr",
                "price_band": "₹371 - ₹390",
                "gmp": "+₹25 (+6.4%)",
                "status": "Allotment Out",
                "dates": "Listing Tracked"
            },
            {
                "name": "NTPC Green Energy IPO",
                "category": "Mainboard / PSU",
                "issue_size": "₹10,000 Cr",
                "price_band": "₹102 - ₹108",
                "gmp": "+₹18 (+16.6%)",
                "status": "Subscription Open",
                "dates": "Bidding Active"
            }
        ]

        lines = [
            "🚀 <b>INDIAN IPO RADAR & GREY MARKET PREMIUM (GMP)</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ]
        for ipo in ipos:
            status_ico = "🟢" if "Open" in ipo.get("status", "") else "🟡"
            lines.append(
                f"{status_ico} <b>{ipo['name']}</b> ({ipo.get('category', 'Mainboard')})\n"
                f"   💰 <b>Price Band:</b> <code>{ipo['price_band']}</code> | Size: {ipo['issue_size']}\n"
                f"   📈 <b>Estimated GMP:</b> <code>{ipo['gmp']}</code>\n"
                f"   🗓 <b>Status / Dates:</b> {ipo['status']} • {ipo['dates']}\n"
            )

        lines.append("⚡ <i>TheSmartMag IPO Radar & Primary Market Watch</i>")
        msg = "\n".join(lines)
        return self.send_message(msg)

    def broadcast_multi_asset_flash(self, data: Optional[Dict[str, Any]] = None) -> bool:
        """Dispatches global multi-asset flash: Commodities, Crypto, Forex, US Markets."""
        if not self.is_active:
            return False

        quotes = {}
        symbols = {
            "XAUUSD (Gold)": "GC=F",
            "XAGUSD (Silver)": "SI=F",
            "USOIL (Crude)": "CL=F",
            "NASDAQ (QQQ)": "^IXIC",
            "S&P 500 (SPX)": "^GSPC",
            "DOW JONES (US30)": "^DJI",
            "EUR/USD": "EURUSD=X",
            "GBP/USD": "GBPUSD=X",
            "USD/JPY": "USDJPY=X",
            "BTC/USD": "BTC-USD",
            "ETH/USD": "ETH-USD",
            "SOL/USD": "SOL-USD"
        }
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        for name, sym in symbols.items():
            try:
                res = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d", headers=headers, timeout=2.0)
                if res.status_code == 200:
                    meta = res.json()["chart"]["result"][0]["meta"]
                    p = meta.get("regularMarketPrice", 0.0)
                    prev = meta.get("chartPreviousClose", p)
                    chg = round(((p - prev) / prev) * 100, 2) if prev else 0.0
                    quotes[name] = {"price": p, "chg": chg}
            except Exception:
                pass

        lines = [
            "🌐 <b>GLOBAL MULTI-ASSET MARKET FLASH</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "🥇 <b>COMMODITIES:</b>"
        ]
        for c in ["XAUUSD (Gold)", "XAGUSD (Silver)", "USOIL (Crude)"]:
            if c in quotes:
                ico = "🟢" if quotes[c]["chg"] >= 0 else "🔴"
                lines.append(f"{ico} <b>{c}:</b> ${quotes[c]['price']:,.2f} ({quotes[c]['chg']:+.2f}%)")

        lines.append("\n💎 <b>CRYPTO (SPOT / DERIVATIVES):</b>")
        for cr in ["BTC/USD", "ETH/USD", "SOL/USD"]:
            if cr in quotes:
                ico = "🟢" if quotes[cr]["chg"] >= 0 else "🔴"
                lines.append(f"{ico} <b>{cr}:</b> ${quotes[cr]['price']:,.2f} ({quotes[cr]['chg']:+.2f}%)")

        lines.append("\n💱 <b>FOREX MAJOR PAIRS:</b>")
        for fx in ["EUR/USD", "GBP/USD", "USD/JPY"]:
            if fx in quotes:
                ico = "🟢" if quotes[fx]["chg"] >= 0 else "🔴"
                lines.append(f"{ico} <b>{fx}:</b> {quotes[fx]['price']:,.4f} ({quotes[fx]['chg']:+.2f}%)")

        lines.append("\n🇺🇸 <b>US INDICES (WALL STREET):</b>")
        for us in ["NASDAQ (QQQ)", "S&P 500 (SPX)", "DOW JONES (US30)"]:
            if us in quotes:
                ico = "🟢" if quotes[us]["chg"] >= 0 else "🔴"
                lines.append(f"{ico} <b>{us}:</b> {quotes[us]['price']:,.2f} ({quotes[us]['chg']:+.2f}%)")

        lines.append("\n⚡ <i>TheSmartMag Institutional Global Market Feed</i>")
        msg = "\n".join(lines)
        return self.send_message(msg)

# Global Instance
news_broadcaster = NewsTelegramBroadcaster()