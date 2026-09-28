"""
AI Article Generation Engine — TheSmartMag Growth Content Studio
================================================================
Generates audience-targeted financial articles per topic, attaches the right
affiliate partner CTA per audience segment, and feeds the public Newsstand.

- Uses the 1min.AI API (already integrated in this repo) when available.
- Falls back to a deterministic, high-quality quant-template writer offline.
- Every article carries affiliate targeting metadata so the funnel
  (view -> read -> CTA click -> conversion) is fully trackable.

Topics & audiences:
  crypto     -> retail crypto traders           -> CoinSwitch Pro / Delta India
  india      -> Indian F&O / equity traders     -> Delta India / Indian brokers
  forex      -> forex & macro traders           -> Prop firms (FTM / Atlas)
  prop       -> funded-challenge aspirants      -> Prop firm partners
  markets    -> general market audience         -> Pro subscription upsell
"""
import os
import re
import json
import time
import uuid
import logging
import threading
from typing import Dict, Any, List, Optional

log = logging.getLogger(__name__)

# ── Topic definitions: target audience + funnel-matched affiliate CTA ─────────
TOPICS: Dict[str, Dict[str, Any]] = {
    "crypto": {
        "label": "Crypto & Digital Assets",
        "audience": "retail crypto traders and DeFi investors",
        "partners": [
            {"code": "coinswitch_pro", "name": "CoinSwitch Pro", "url": "https://coinswitch.co/pro/signup?code=PmstphH", "cta": "Open a CoinSwitch Pro account & claim your signup bonus"},
            {"code": "delta_india", "name": "Delta Exchange India", "url": "https://www.delta.exchange/?code=YXQSZA", "cta": "Trade crypto futures on Delta India — 10% off fees"},
        ],
    },
    "india": {
        "label": "Indian Equities & F&O",
        "audience": "NSE/BSE intraday and options traders",
        "partners": [
            {"code": "delta_india", "name": "Delta Exchange India", "url": "https://www.delta.exchange/?code=YXQSZA", "cta": "Trade index options on Delta India — 10% off"},
            {"code": "coinswitch_pro", "name": "CoinSwitch Pro", "url": "https://coinswitch.co/pro/signup?code=PmstphH", "cta": "Start spot investing on CoinSwitch Pro"},
        ],
    },
    "forex": {
        "label": "Forex & Macro",
        "audience": "forex swing traders and macro watchers",
        "partners": [
            {"code": "ftm_prop", "name": "Funded Trader Markets", "url": "https://fundedtradermarkets.com/ref/arnab", "cta": "Get a funded forex account up to $100k (promo: arnab)"},
            {"code": "atlas_funded", "name": "Atlas Funded", "url": "https://affiliates.atlasfunded.com/Tracking/click/?affid=12275&campaign=11320&product_id=1&t_type=Register&t_lang=EN", "cta": "Pass your prop challenge with Atlas — 20% off"},
        ],
    },
    "prop": {
        "label": "Prop Firms & Funded Challenges",
        "audience": "funded-challenge aspirants and scalpers",
        "partners": [
            {"code": "atlas_funded", "name": "Atlas Funded", "url": "https://affiliates.atlasfunded.com/Tracking/click/?affid=12275&campaign=11320&product_id=1&t_type=Register&t_lang=EN", "cta": "Start your Atlas Funded evaluation — 20% off"},
            {"code": "aquafunded", "name": "AquaFunded", "url": "https://www.aquafunded.com/?afmc=6e9", "cta": "Claim AquaFunded 90% payout challenge (promo: 6e9)"},
        ],
    },
    "markets": {
        "label": "Global Markets",
        "audience": "serious retail traders upgrading their toolkit",
        "partners": [
            {"code": "tsm_pro_plan", "name": "TheSmartMag Pro", "url": "https://trade.thesmartmag.com/#trades", "cta": "Unlock real-time AI signals with TheSmartMag Pro ($49/mo)"},
        ],
    },
}

# Rotating article angles so consecutive generations differ
ANGLES = [
    ("breakdown", "What {subject} really means for {audience}"),
    ("playbook", "The {period} playbook: trading {subject} step by step"),
    ("risk", "Risk-first guide: surviving {subject} without blowing your account"),
    ("flows", "Smart money flows behind {subject} — what the tape shows"),
    ("beginner", "{subject} explained simply for {audience}"),
]

SUBJECTS = {
    "crypto": ["the Bitcoin halving cycle", "altcoin rotation", "crypto funding rates", "exchange outflows", "spot ETF flows"],
    "india": ["Nifty expiry-day gamma", "Bank Nifty PCR shifts", "FII/DII flows", "India VIX spikes", "options chain max pain"],
    "forex": ["Fed vs RBI policy divergence", "Dollar index breakouts", "gold's macro bid", "carry trade unwinds", "CPI surprises"],
    "prop": ["passing funded evaluations", "prop firm drawdown rules", "consistent payout strategies", "scaling plans", "news-trading restrictions"],
    "markets": ["the AI trade", "rate-cut cycles", "multi-asset momentum", "liquidity-driven rallies", "volatility regime shifts"],
}


class ArticleStudio:
    """Generates and caches audience-targeted articles with affiliate CTAs."""

    def __init__(self):
        self.lock = threading.Lock()
        self._ai_client = None

    # ── 1min.AI integration (graceful fallback) ─────────────────────────────
    def _get_ai_client(self):
        if self._ai_client is not None:
            return self._ai_client
        try:
            from onemin_ai_client import OneMinAIClient
            self._ai_client = OneMinAIClient()
        except Exception:
            self._ai_client = False
        return self._ai_client

    def _ai_generate(self, prompt: str) -> Optional[str]:
        client = self._get_ai_client()
        if not client:
            return None
        try:
            res = client.analyze_sentiment(prompt)
            # 1min.AI chat completions shape (OpenAI-compatible) or plain text
            if isinstance(res, dict):
                choices = res.get("choices") or []
                if choices and isinstance(choices[0], dict):
                    msg = choices[0].get("message") or {}
                    text = msg.get("content") or choices[0].get("text")
                    if text and len(text) > 200:
                        return text.strip()
                if res.get("response") and len(res["response"]) > 200:
                    return res["response"].strip()
        except Exception as exc:
            log.debug("1min.AI article generation skipped: %s", exc)
        return None

    # ── Deterministic template writer (always available, decent quality) ────
    def _template_generate(self, topic: str, angle: str, subject: str, market_note: str) -> Dict[str, Any]:
        cfg = TOPICS[topic]
        audience = cfg["audience"]
        title_map = {
            "breakdown": f"What {subject} really means for {audience.title()}",
            "playbook": f"The {time.strftime('%B %Y')} playbook: trading {subject} step by step",
            "risk": f"Risk-first guide: surviving {subject} without blowing your account",
            "flows": f"Smart money flows behind {subject} — what the tape shows",
            "beginner": f"{subject.title()}, explained simply for {audience}",
        }
        title = title_map.get(angle, f"Market brief: {subject}")

        body = [
            f"**Why this matters now**\n{market_note}",
            f"\n**The setup**\n{subject.title()} is currently the single biggest driver on the desks of professional traders. "
            f"For {audience}, the opportunity is not predicting every tick — it is positioning with asymmetric risk: "
            f"defined stop-losses, minimum 1:3 reward-to-risk, and letting the algorithm do the monitoring 24/7.",
            f"\n**How institutions read it**\nOrder-flow desks watch liquidity pools and fair-value gaps around {subject}. "
            f"When retail sentiment crowds one side, the tape usually shows accumulation on the other. "
            f"The SmartMag Neural Core scores these imbalances in real time across crypto, index and FX markets.",
            f"\n**The 3-step execution framework**\n"
            f"1. Let the AI consensus engine (>= 85% model agreement) flag the setup — never chase without confluence.\n"
            f"2. Size at 0.25%–0.5% equity risk per trade; the Capital Survival protocol halts the day at −1.5%.\n"
            f"3. Trail the break-even lock at +0.3% and let winners run toward the +6% to +15% target ladder.",
            f"\n**Common mistakes to avoid**\nAveraging into losers, trading every catalyst, and ignoring session timing. "
            f"{audience} who survive year one are almost always the ones who automated discipline before scaling size.",
        ]
        takeaways = [
            f"{subject.title()} is the current institutional focus — trade with confluence, not emotion.",
            "Risk a maximum of 0.5% per trade with a minimum 1:3 reward-to-risk ratio.",
            "Automate stop management — manual trailing is where most retail accounts bleed.",
        ]

        return {
            "title": title,
            "summary": f"A practical, risk-first briefing on {subject} for {audience} — with an executable 3-step framework.",
            "body": "\n".join(body),
            "takeaways": takeaways,
        }

    # ── Public API ───────────────────────────────────────────────────────────
    def generate_article(self, topic: str = "markets", use_ai: bool = True) -> Dict[str, Any]:
        topic = topic if topic in TOPICS else "markets"
        cfg = TOPICS[topic]
        angle_key, angle_tpl = ANGLES[int(time.time() // 3600) % len(ANGLES)]
        subject = SUBJECTS[topic][int(time.time() // 1800) % len(SUBJECTS[topic])]

        # Fresh market context line (best-effort; template fallback keeps it generic)
        market_note = self._market_note(topic)

        article = None
        used_ai = False
        if use_ai:
            prompt = (
                f"You are a senior financial markets editor at TheSmartMag. Write a concise, engaging article "
                f"(350-500 words, markdown, with a 3-bullet takeaway list at the end) about: {subject}. "
                f"Angle: {angle_tpl.format(subject=subject, audience=cfg['audience'], period=time.strftime('%B %Y'))}. "
                f"Context: {market_note}. Target audience: {cfg['audience']}. "
                f"Rules: no financial advice guarantees, mention risk management, be specific and practical."
            )
            ai_text = self._ai_generate(prompt)
            if ai_text:
                article = self._parse_ai_text(ai_text, subject, cfg["audience"])
                used_ai = True

        if not article:
            article = self._template_generate(topic, angle_key, subject, market_note)

        # Attach audience-matched affiliate CTA (rotate per hour for A/B)
        partners = cfg["partners"]
        partner = partners[int(time.time() // 3600) % len(partners)]

        return {
            "id": f"gen_{topic}_{uuid.uuid4().hex[:8]}",
            "topic": topic,
            "topic_label": cfg["label"],
            "title": article["title"],
            "summary": article["summary"],
            "body": article["body"],
            "takeaways": article["takeaways"],
            "sentiment": self._guess_sentiment(article["title"] + article["summary"]),
            "reading_minutes": max(1.0, round(len(article["body"].split()) / 220.0, 1)),
            "affiliate_partner": partner["code"],
            "affiliate_url": partner["url"],
            "cta_text": partner["cta"],
            "source_refs": ["TheSmartMag Quant Desk", "ForexFactory Calendar", "Live RSS wires"],
            "model": "1min.ai" if used_ai else "template-quant",
            "published_at": int(time.time()),
        }

    def _market_note(self, topic: str) -> str:
        try:
            from news_agent_core import news_core
            summary = news_core.get_market_sentiment_summary()
            with news_core.lock:
                news = list(news_core.cached_news)
            label = summary.get("label", "NEUTRAL")
            top = news[0].get("title", "markets consolidating ahead of macro catalysts") if news else "markets consolidating ahead of macro catalysts"
            return f"Live desk read: overall sentiment is {label} ({summary.get('bull_pct', 50)}% bullish). Top wire: “{top}”."
        except Exception:
            return "Markets are rotating as macro catalysts approach; risk appetite remains selective."

    @staticmethod
    def _parse_ai_text(text: str, subject: str, audience: str) -> Optional[Dict[str, Any]]:
        try:
            takeaways: List[str] = []
            body = text
            # Extract bullet takeaways if present
            m = re.search(r"(?:takeaways?|key points?)[:\s]*\n((?:[-*•].+\n?)+)", text, re.IGNORECASE)
            if m:
                takeaways = [re.sub(r"^[-*•]\s*", "", ln).strip() for ln in m.group(1).strip().splitlines() if ln.strip()]
                body = text[: m.start()].strip()
            title = ""
            tm = re.search(r"^#\s*(.+)$", body, re.MULTILINE)
            if tm:
                title = tm.group(1).strip()
                body = body.replace(tm.group(0), "").strip()
            if not title:
                first_line = body.splitlines()[0] if body else ""
                title = re.sub(r"[*_#]", "", first_line).strip()[:120] or f"Market brief: {subject}"
            return {
                "title": title,
                "summary": re.sub(r"[*_#]", "", body.split("\n\n")[0])[:260],
                "body": body,
                "takeaways": takeaways[:4] or [
                    f"{subject.title()} is the key catalyst to watch this week.",
                    "Keep per-trade risk at 0.25%–0.5% with minimum 1:3 R:R.",
                    "Automate trailing stops — discipline scales, emotion doesn't.",
                ],
            }
        except Exception:
            return None

    @staticmethod
    def _guess_sentiment(text: str) -> str:
        t = text.lower()
        bull = any(w in t for w in ("bull", "rally", "surge", "breakout", "surviving", "playbook", "win"))
        bear = any(w in t for w in ("crash", "dump", "risk", "blow", "warning", "fear", "drop"))
        if bull and not bear:
            return "BULLISH"
        if bear and not bull:
            return "BEARISH"
        return "NEUTRAL"


# Singleton used by API routes
article_studio = ArticleStudio()
