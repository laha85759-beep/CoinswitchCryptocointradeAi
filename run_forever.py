"""Run the bot continuously with automatic restart and notifications.

Usage: python run_forever.py
"""
import logging
import time
import traceback

from config import CONFIG
import main

from notifier import TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def _notify(text: str) -> None:
    try:
        notifier = TelegramNotifier(CONFIG.get("telegram_token", ""), CONFIG.get("telegram_chat_id", ""))
        if notifier:
            notifier.send(text)
    except Exception:
        log.exception("Failed to send notification")


def main_loop() -> None:
    import os
    poll = int(CONFIG.get("poll_interval_sec", 900) or 900)
    flag_path = os.path.join(os.path.dirname(__file__), "trigger_cycle.flag")
    
    while True:
        # Clear flag file if it exists at start of execution
        if os.path.exists(flag_path):
            try:
                os.remove(flag_path)
            except Exception:
                pass
                
        try:
            log.info("Starting bot cycle")
            main.run()
            log.info("Cycle finished; entering sleep pool of %s seconds", poll)
        except Exception as exc:
            tb = traceback.format_exc()
            log.error("Bot cycle CRASH: %s", exc)
            log.error(tb)
            _notify(f"🚨 Bot cycle crashed: {str(exc)}\nSee logs for details.")
            
        # Sleep in 1-second chunks and monitor trigger flag file
        end_sleep = time.time() + poll
        try:
            while time.time() < end_sleep:
                if os.path.exists(flag_path):
                    log.info("Manual trigger flag detected! Breaking sleep loop.")
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            log.info("run_forever interrupted by KeyboardInterrupt")
            break


if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        log.info("Exiting run_forever")