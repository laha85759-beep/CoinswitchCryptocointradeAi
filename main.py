"""
AI Crypto Auto-Trader — CoinSwitch Pro
Entry point called by GitHub Actions every 15 minutes.

Each cycle:
  1. Monitor existing open trades (check SL hit / TP filled)
  2. Scan market for new pump signals
  3. Execute new BUY trades if found
"""

import logging
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


def run():
    log.info("=" * 60)
    log.info(f"🤖 CoinSwitch AI Bot — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    log.info("=" * 60)

    if not CONFIG["api_key"] or not CONFIG["api_secret"]:
        log.error("❌ CoinSwitch API credentials not set. Check GitHub Secrets.")
        sys.exit(1)

    client   = CoinSwitchClient(CONFIG["api_key"], CONFIG["api_secret"])
    notifier = TelegramNotifier(CONFIG["telegram_token"], CONFIG["telegram_chat_id"])
    scanner  = MarketScanner(CONFIG, client)
    executor = TradeExecutor(CONFIG, client, notifier)

    # ── Step 1: Monitor existing positions ────────────────────────────────────
    log.info("🔍 Monitoring open trades…")
    executor.monitor()

    # ── Step 2: Scan for new signals ─────────────────────────────────────────
    log.info("🔍 Scanning market for new signals…")
    pump_signals, dump_signals = scanner.scan()

    if not pump_signals:
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

    # ── Step 4: Open new trades ───────────────────────────────────────────────
    for signal in pump_signals:
        executor.open_trade(signal)

    log.info("✅ Cycle complete.\n")


if __name__ == "__main__":
    run()
