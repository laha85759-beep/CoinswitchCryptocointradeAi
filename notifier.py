import logging, requests, time

log = logging.getLogger(__name__)

class TelegramNotifier:
    _last_emergency_msg = ""
    _last_emergency_time = 0.0

    def __init__(self, token: str, chat_id: str):
        self.token   = token
        self.chat_id = chat_id
        self.enabled = bool(token and chat_id)

    def send(self, msg: str):
        if not self.enabled:
            return
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": msg, "parse_mode": "Markdown"},
                timeout=10,
            ).raise_for_status()
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
        self.send(formatted)
