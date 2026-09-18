"""
Crypto News & Asset AI Intelligence Agent
==========================================
1. Ingests real-time breaking crypto news across multiple institutional feeds:
   - Cointelegraph Live RSS
   - Decrypt Crypto Breaking News
   - Economic Calendar (Forex Factory)
2. Extracts specific Crypto Assets / Tickers (e.g. BTC, ETH, SOL, POPCAT, PEPE, DOGE, SUI, RENDER, etc.)
3. Analyzes Sentiment (BULLISH / BEARISH / CATALYST) via NVIDIA AI Super Brain & rules.
4. Sends rich, high-priority instant Telegram news broadcasts with highlighted Asset Names.
5. Deduplicates headlines with persistent state cache (seen_news.json).
"""

import logging
import time
import re
import json
import os
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

from notifier import TelegramNotifier
from nvidia_super_brain import NvidiaSuperBrainEngine
from news_telegram_broadcaster import news_broadcaster

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
SEEN_NEWS_FILE = BASE_DIR / "seen_news.json"

# Common crypto assets mapping for high-accuracy regex entity extraction
KNOWN_CRYPTO_ASSETS = {
    "BITCOIN": "BTC", "BTC": "BTC",
    "ETHEREUM": "ETH", "ETHER": "ETH", "ETH": "ETH",
    "SOLANA": "SOL", "SOL": "SOL",
    "RIPPLE": "XRP", "XRP": "XRP",
    "DOGECOIN": "DOGE", "DOGE": "DOGE",
    "SHIBA": "SHIB", "SHIB": "SHIB",
    "PEPE": "PEPE", "POPCAT": "POPCAT", "WIF": "WIF", "BONK": "BONK", "FLOKI": "FLOKI",
    "MOODENG": "MOODENG", "FARTCOIN": "FARTCOIN", "GOAT": "GOAT", "GRIFFAIN": "GRIFFAIN",
    "SUI": "SUI", "APTOS": "APT", "APT": "APT", "CELESTIA": "TIA", "TIA": "TIA",
    "SEI": "SEI", "INJECTIVE": "INJ", "INJ": "INJ", "BITTENSOR": "TAO", "TAO": "TAO",
    "RENDER": "RENDER", "RNDR": "RENDER", "FETCH": "FET", "FET": "FET", "ASI": "FET",
    "NEAR": "NEAR", "AVALANCHE": "AVAX", "AVAX": "AVAX", "CHAINLINK": "LINK", "LINK": "LINK",
    "CARDANO": "ADA", "ADA": "ADA", "POLKADOT": "DOT", "DOT": "DOT",
    "ZCASH": "ZEC", "ZEC": "ZEC", "MONERO": "XMR", "XMR": "XMR",
    "AAVE": "AAVE", "UNISWAP": "UNI", "UNI": "UNI", "MAKER": "MKR", "MKR": "MKR", "SKY": "MKR",
    "TONCOIN": "TON", "TON": "TON", "TRON": "TRX", "TRX": "TRX",
    "TETHER": "USDT", "USDT": "USDT", "USDC": "USDC",
    # ── Real World Asset (RWA) Tokens ──
    "ONDO": "ONDO", "MANTRA": "OM", "OM": "OM", "PENDLE": "PENDLE",
    "CENTRIFUGE": "CFG", "CFG": "CFG", "GOLDFINCH": "GFI", "GFI": "GFI",
    "MAPLE": "MPL", "MPL": "MPL", "CLEARPOOL": "CPOOL", "CPOOL": "CPOOL",
    "TRUEFI": "TRU", "TRU": "TRU", "REALIO": "RIO", "RIO": "RIO",
    "PROPBASE": "PROPC", "PROPC": "PROPC", "IXSWAP": "IXS", "IXS": "IXS",
    "CREDITCOIN": "CTC", "CTC": "CTC", "XAUT": "XAUT", "PAXG": "PAXG"
}


class CryptoNewsIntelligenceAgent:
    """Autonomous Agent for Real-Time Crypto News Ingestion, Asset Identification, and Telegram Broadcasting."""

    def __init__(self, cfg: Dict[str, Any], notifier: Optional[TelegramNotifier] = None):
        self.cfg = cfg
        self.notifier = notifier
        self.nvidia_engine = NvidiaSuperBrainEngine(cfg)
        self.seen_news = self._load_seen_news()

    def _load_seen_news(self) -> set:
        if SEEN_NEWS_FILE.exists():
            try:
                with open(SEEN_NEWS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data if isinstance(data, list) else [])
            except Exception:
                pass
        return set()

    def _save_seen_news(self) -> None:
        try:
            # Keep cache to latest 1000 items
            news_list = list(self.seen_news)[-1000:]
            with open(SEEN_NEWS_FILE, "w", encoding="utf-8") as f:
                json.dump(news_list, f, indent=2)
        except Exception as e:
            log.warning("Failed to save seen news: %s", e)

    def extract_assets(self, title: str, summary: str = "") -> List[str]:
        """Extracts identified crypto tickers from headline & summary."""
        text = f"{title} {summary}".upper()
        found_assets = set()
        
        # Word token matching
        tokens = re.findall(r'\b[A-Z0-9$]+\b', text)
        for token in tokens:
            clean_token = token.replace("$", "")
            if clean_token in KNOWN_CRYPTO_ASSETS:
                found_assets.add(KNOWN_CRYPTO_ASSETS[clean_token])

        return sorted(list(found_assets))

    def fetch_breaking_crypto_news(self) -> List[Dict[str, Any]]:
        """Fetches latest breaking news from multiple RSS and API endpoints."""
        news_items = []
        feeds = [
            ("Cointelegraph", "https://cointelegraph.com/rss"),
            ("Decrypt", "https://decrypt.co/feed"),
        ]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }

        for source_name, url in feeds:
            try:
                resp = requests.get(url, headers=headers, timeout=6)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    for item in root.findall("./channel/item")[:6]:
                        title_el = item.find("title")
                        desc_el = item.find("description")
                        link_el = item.find("link")
                        pubdate_el = item.find("pubDate")

                        title = title_el.text.strip() if title_el is not None and title_el.text else ""
                        desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
                        link = link_el.text.strip() if link_el is not None and link_el.text else ""
                        pub_date = pubdate_el.text.strip() if pubdate_el is not None and pubdate_el.text else ""

                        # Clean HTML tags from description if any
                        clean_desc = re.sub(r'<[^>]+>', '', desc)[:160]

                        if title:
                            news_items.append({
                                "source": source_name,
                                "title": title,
                                "summary": clean_desc,
                                "link": link,
                                "pub_date": pub_date,
                            })
            except Exception as e:
                log.debug("News fetch error from %s: %s", source_name, e)

        return news_items

    def analyze_sentiment_and_impact(self, title: str, summary: str) -> Dict[str, Any]:
        """Classifies sentiment, impact level, and trading bias."""
        text = f"{title} {summary}".upper()
        
        bullish_keywords = ["SURGE", "BREAKOUT", "SOARS", "HIGHEST", "ACCUMULATION", "ETF APPROVAL", "PARTNERSHIP", "RALLY", "BULL", "RECORD HIGH", "PUMP", "WHALE BUY"]
        bearish_keywords = ["CRASH", "DUMP", "PLUNGE", "HACK", "EXPLOIT", "LAWSUIT", "SEC CHARGES", "BAN", "DOWNTURN", "BEAR", "LIQUIDATION", "SELLOFF"]
        high_impact_keywords = ["FED", "RATE CUT", "CPI", "INFLATION", "SEC", "ETF", "BINANCE LISTING", "BREAKING", "ALERT"]

        is_bullish = any(k in text for k in bullish_keywords)
        is_bearish = any(k in text for k in bearish_keywords)
        is_high_impact = any(k in text for k in high_impact_keywords)

        if is_bullish and not is_bearish:
            sentiment = "BULLISH 🚀"
            icon = "🟢"
            bias = "LONG"
        elif is_bearish and not is_bullish:
            sentiment = "BEARISH 📉"
            icon = "🔴"
            bias = "SHORT"
        else:
            sentiment = "CATALYST / VOLATILE ⚡" if is_high_impact else "MARKET UPDATE 📊"
            icon = "⚡" if is_high_impact else "ℹ️"
            bias = "WATCH"

        return {
            "sentiment": sentiment,
            "icon": icon,
            "bias": bias,
            "is_high_impact": is_high_impact,
        }

    def process_and_broadcast_news(self) -> List[Dict[str, Any]]:
        """Scans, processes fresh news items, extracts asset names, and broadcasts to Telegram."""
        log.info("CryptoNewsIntelligenceAgent: Scanning multi-feed crypto breaking news...")
        fresh_items = self.fetch_breaking_crypto_news()
        broadcasted = []

        for item in fresh_items:
            title = item["title"]
            title_hash = f"{item['source']}:{title}"

            if title_hash in self.seen_news:
                continue

            # Mark as seen
            self.seen_news.add(title_hash)

            # Extract assets
            assets = self.extract_assets(title, item.get("summary", ""))
            asset_tags = " ".join([f"#{a}" for a in assets]) if assets else "#CRYPTO #MARKET"
            primary_asset = assets[0] if assets else "CRYPTO"

            # Analyze Sentiment & Bias
            analysis = self.analyze_sentiment_and_impact(title, item.get("summary", ""))

            # ONLY broadcast important news: high-impact catalysts or specific coins with clear Long/Short sentiment
            is_important = analysis.get("is_high_impact") or (len(assets) > 0 and analysis.get("bias") in ("LONG", "SHORT"))
            if not is_important:
                continue

            # Format Telegram Message
            msg = (
                f"{analysis['icon']} *HIGH-IMPACT CRYPTO NEWS ALERT*\n"
                f"═════════════════════════\n"
                f"🪙 *Asset Tag*: `{asset_tags}`\n"
                f"📍 *Primary Coin*: *{primary_asset}*\n"
                f"📰 *Headline*:\n`{title}`\n"
                f"─────────────────────────\n"
                f"📊 *AI Sentiment*: `{analysis['sentiment']}`\n"
                f"🎯 *Market Bias*: `{analysis['bias']}`\n"
                f"📡 *Source*: `{item['source']}`\n"
                f"═════════════════════════\n"
                f"🤖 *NVIDIA AI Super Brain • Selective High-Conviction Feed*"
            )

            # Broadcast to dedicated News Bot (@ForexIndian_bot / LiveForexSignalsAI_bot)
            try:
                if news_broadcaster.is_active:
                    news_broadcaster.send_message(msg, parse_mode="Markdown")
                    log.info("📢 Broadcasted Crypto News for %s to @ForexIndian_bot: %s", primary_asset, title[:45])
                elif self.notifier:
                    self.notifier.send(msg)
                    log.info("📢 Broadcasted Crypto News for %s to Telegram: %s", primary_asset, title[:45])
            except Exception as exc:
                log.warning("Telegram news broadcast error: %s", exc)

            broadcasted.append({
                "asset": primary_asset,
                "assets": assets,
                "title": title,
                "sentiment": analysis["sentiment"],
                "bias": analysis["bias"],
                "source": item["source"],
            })

            # Small rate-limit delay between multiple breaking news broadcasts
            time.sleep(1)

        self._save_seen_news()
        if broadcasted:
            log.info("CryptoNewsIntelligenceAgent: Broadcasted %s new crypto asset news alerts", len(broadcasted))
        return broadcasted
