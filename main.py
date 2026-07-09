"""
AI Crypto Auto-Trader — CoinSwitch Pro
Entry point called by GitHub Actions every 15 minutes.

Each cycle:
  1. Monitor existing open trades (check SL hit / TP filled)
  2. Scan market for new pump signals
  3. Execute new BUY trades if found
"""

import logging
import os
import sys
from datetime import datetime, timezone

from coinswitch_client import CoinSwitchClient
from scanner import MarketScanner
from trader import TradeExecutor
from notifier import TelegramNotifier
from config import CONFIG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", mode="a", encoding="utf-8"),
    ],
)
logging.getLogger().handlers[0].stream.reconfigure(encoding="utf-8", errors="replace")
log = logging.getLogger(__name__)
MONDAY_NOTICE_FILE = "last_monday_notice.txt"


def _send_monday_resumption_notice(notifier: TelegramNotifier) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    if os.path.exists(MONDAY_NOTICE_FILE):
        with open(MONDAY_NOTICE_FILE, encoding="utf-8") as handle:
            last_date = handle.read().strip()
    else:
        last_date = ""

    if last_date != today:
        notifier.send(
            "📅 *WEEKEND RESUMPTION*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🔄 Markets are open again and the bot is back online."
        )
        with open(MONDAY_NOTICE_FILE, "w", encoding="utf-8") as handle:
            handle.write(today)


def run():
    log.info("=" * 60)
    log.info(f"🤖 CoinSwitch AI Bot — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    log.info("=" * 60)

    if not CONFIG["api_key"] or not CONFIG["api_secret"]:
        log.error("❌ CoinSwitch API credentials not set. Check GitHub Secrets.")
        sys.exit(1)

    client   = CoinSwitchClient(
        CONFIG["api_key"],
        CONFIG["api_secret"],
        rate_limit_delay=CONFIG.get("request_delay_seconds", 1.0),
    )
    notifier = TelegramNotifier(CONFIG["telegram_token"], CONFIG["telegram_chat_id"])
    scanner  = MarketScanner(CONFIG, client)
    executor = TradeExecutor(CONFIG, client, notifier)

    # ── Step 1: Monitor existing positions ────────────────────────────────────
    log.info("🔍 Monitoring open trades…")
    executor.monitor()

    # ── Step 2: Scan for new signals ─────────────────────────────────────────
    log.info("🔍 Scanning market for new signals…")
    pump_signals, dump_signals = scanner.scan()

    if not pump_signals and not dump_signals:
        log.info("😴 No high-probability pump signals this cycle.")
        notifier.send(
            f"💓 *HEARTBEAT — NO SIGNALS FOUND*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🧠 Bot cycle completed without new pump or dump signals.\n"
            f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        )
    elif not pump_signals:
        log.info("😴 No high-probability pump signals this cycle.")
    else:
        log.info(f"✅ Found {len(pump_signals)} pump signal(s).")
        for signal in pump_signals:
            log.info(
                f"  → {signal['symbol']} | pump={signal['pump_score']} | "
                f"rsi={signal['rsi']} | vol×{signal['vol_ratio']} | roc={signal['roc5']}%"
            )

    # ── Step 3: Exit positions on dump signals ───────────────────────────────
    if dump_signals:
        log.info(f"⚠️  Found {len(dump_signals)} dump signal(s) — checking open trades…")
        for signal in dump_signals:
            log.info(
                f"  → {signal['symbol']} | dump={signal['dump_score']} | "
                f"rsi={signal['rsi']} | vol×{signal['vol_ratio']} | roc={signal['roc5']}%"
            )
        executor.exit_on_dump(dump_signals)

    # ── Step 4: Weekend check — no new trades on Sat/Sun ─────────────────────
    weekday = datetime.now(timezone.utc).weekday()
    if weekday == 0:
        _send_monday_resumption_notice(notifier)

    if weekday in (5, 6):
        log.info("🌙 Weekend — no new trades opened. Existing positions still monitored.")
        if pump_signals:
            notifier.send(
                f"🌙 *WEEKEND — SKIPPING NEW TRADES*\n"
                f"📊 `{len(pump_signals)}` pump signal(s) found but markets are closed for new entries.\n"
                f"⏰ Resuming Monday."
            )
    else:
        for signal in pump_signals:
            executor.open_trade(signal)

    log.info("✅ Cycle complete.\n")


if __name__ == "__main__":
    run()
