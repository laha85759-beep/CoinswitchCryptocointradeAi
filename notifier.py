import logging, requests, time, os, json, hashlib, re
from typing import Dict

log = logging.getLogger(__name__)

_NOTIFIER_DEDUPE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "telegram_sent_log.json")
_NOTIFIER_DEDUPE_TTL_SECONDS = 86400  # 24 Hours TTL to eliminate any duplicate messages  # 15 minutes TTL for deduplicating identical Telegram messages
_NOTIFIER_MAX_ENTRIES = 2000

def _load_sent_log() -> Dict[str, float]:
    try:
        if os.path.exists(_NOTIFIER_DEDUPE_FILE):
            with open(_NOTIFIER_DEDUPE_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            cutoff = time.time() - 86400  # 24 hour retention in file
            return {k: v for k, v in raw.items() if isinstance(v, (int, float)) and v >= cutoff}
    except Exception:
        pass
    return {}

def _save_sent_log(log_data: Dict[str, float]) -> None:
    try:
        if len(log_data) > _NOTIFIER_MAX_ENTRIES:
            kept = dict(sorted(log_data.items(), key=lambda kv: kv[1], reverse=True)[:_NOTIFIER_MAX_ENTRIES])
            log_data = kept
        tmp = _NOTIFIER_DEDUPE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(log_data, f)
        os.replace(tmp, _NOTIFIER_DEDUPE_FILE)
    except Exception:
        pass

class TelegramNotifier:
    _last_emergency_msg = ""
    _last_emergency_time = 0.0

    def __init__(self, token: str = None, chat_id: str = None):
        self.token = (
            token or 
            os.getenv("TELEGRAM_TOKEN") or 
            os.getenv("TELEGRAM_BOT_TOKEN") or 
            os.getenv("NEWS_BOT_TOKEN") or 
            "8710452375:AAG-pqR8amkjx772hAYiLC_0WymUcoruVqE"
        ).strip()
        self.chat_id = (
            chat_id or 
            os.getenv("TELEGRAM_CHAT_ID") or 
            os.getenv("NEWS_CHAT_ID") or 
            os.getenv("NEWS_TELEGRAM_CHAT_ID") or 
            "6207722743"
        ).strip()
        self.enabled = bool(self.token and self.chat_id)

    @staticmethod
    def _content_hash(text: str) -> str:
        normalized = re.sub(r"\s+", " ", text).strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]

    def send(self, msg: str, dedupe: bool = True, ttl_seconds: int = _NOTIFIER_DEDUPE_TTL_SECONDS):
        if not self.enabled or not msg:
            return
        
        # Deduplication check
        if dedupe:
            now = time.time()
            content_key = self._content_hash(msg)
            sent_log = _load_sent_log()
            last_sent = sent_log.get(content_key, 0.0)
            if (now - last_sent) < ttl_seconds:
                log.info("Suppressing duplicate Telegram notification (sent %.1fs ago)", now - last_sent)
                return

        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": msg, "parse_mode": "Markdown"},
                timeout=10,
            )
            if resp.status_code == 200:
                if dedupe:
                    sent_log = _load_sent_log()
                    sent_log[content_key] = time.time()
                    _save_sent_log(sent_log)
            elif resp.status_code == 429:
                log.warning("Telegram rate-limited (HTTP 429): %s", resp.text)
            else:
                log.warning("Telegram error HTTP %s: %s", resp.status_code, resp.text)
        except Exception as e:
            log.warning(f"Telegram error: {e}")

    def send_emergency_alert(self, title: str, details: str):
        """Send an immediate emergency notification to Telegram on any system or trading error."""
        if not self.enabled:
            return
        now = time.time()
        msg_key = f"{title}:{str(details)[:60]}"
        # Deduplicate identical error notifications within 5 minutes to prevent alert flooding
        if msg_key == TelegramNotifier._last_emergency_msg and (now - TelegramNotifier._last_emergency_time) < 300:
            return

        TelegramNotifier._last_emergency_msg = msg_key
        TelegramNotifier._last_emergency_time = now

        formatted = (
            f"🚨 *SYSTEM ALERT • EMERGENCY EXCEPTION*\n"
            f"═════════════════════════\n"
            f"📍 *Component*: `{title}`\n"
            f"⚠️ *Diagnostic Detail*:\n`{str(details)[:300]}`\n"
            f"─────────────────────────\n"
            f"🛡️ *Auto-Recovery*: Active Watchdog maintaining 24/7 daemon loop.\n"
            f"═════════════════════════"
        )
        self.send(formatted, dedupe=False)
