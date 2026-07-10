"""
CoinSwitch multi-agent pump/dump bot.

GitHub Actions runs one cycle every 15 minutes:
Monitor -> Data Collector -> Signal Detector -> Risk Manager -> Execution.
"""

import logging
import os
import sys
from datetime import datetime, timezone

from agents import (
    AuditLogger,
    CircuitBreaker,
    DataCollectorAgent,
    ExecutionAgent,
    MonitorReporterAgent,
    RiskManagerAgent,
    SignalDetectorAgent,
)
from coinswitch_client import CoinSwitchClient
from config import CONFIG
from notifier import TelegramNotifier

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
            "*WEEKEND RESUMPTION*\n"
            "Markets are open again and the bot is back online."
        )
        with open(MONDAY_NOTICE_FILE, "w", encoding="utf-8") as handle:
            handle.write(today)


def _is_weekend_utc() -> bool:
    return datetime.now(timezone.utc).weekday() in (5, 6)


def run() -> None:
    log.info("=" * 60)
    log.info("CoinSwitch Multi-Agent Bot - %s", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    log.info("=" * 60)

    if not CONFIG["api_key"] or not CONFIG["api_secret"]:
        log.error("CoinSwitch API credentials not set. Check GitHub Secrets.")
        sys.exit(1)

    client = CoinSwitchClient(
        CONFIG["api_key"],
        CONFIG["api_secret"],
        rate_limit_delay=CONFIG.get("request_delay_seconds", 1.0),
    )
    notifier = TelegramNotifier(CONFIG["telegram_token"], CONFIG["telegram_chat_id"])
    audit = AuditLogger()
    circuit_breaker = CircuitBreaker(CONFIG, audit)

    monitor = MonitorReporterAgent(CONFIG, client, notifier, audit)
    collector = DataCollectorAgent(CONFIG, client, audit)
    detector = SignalDetectorAgent(CONFIG, audit)
    risk_manager = RiskManagerAgent(CONFIG, client, audit)
    executor = ExecutionAgent(CONFIG, client, audit)

    log.info("Mode: %s", "PAPER" if CONFIG["paper_trading_mode"] else "LIVE")

    # Agent 5 is intentionally run before new entries so existing positions are
    # protected before the cycle considers fresh trades.
    log.info("Monitor/Reporter: checking open positions")
    monitor_report = monitor.monitor()
    log.info("Monitor/Reporter: open_positions=%s", monitor_report["open_positions"])

    log.info("Data Collector: fetching market data")
    market_data = collector.collect()
    errors = [item for item in market_data if item.get("error")]
    if market_data and len(errors) == len(market_data):
        state = circuit_breaker.record_error("all_collector_items_failed")
        log.error("Circuit breaker state: %s", state)
    else:
        circuit_breaker.record_success()

    log.info("Signal Detector: classifying symbols")
    signals = detector.classify(market_data)
    pump_signals = [s for s in signals if s["signal"] == "pump"]
    dump_signals = [s for s in signals if s["signal"] == "dump"]
    watch_signals = [s for s in signals if s["signal"] == "watch"]
    other_count = len(signals) - len(pump_signals) - len(dump_signals) - len(watch_signals)

    log.info(
        "Signals: pump=%s dump=%s watch=%s normal_or_other=%s",
        len(pump_signals),
        len(dump_signals),
        len(watch_signals),
        other_count,
    )
    for signal in sorted(pump_signals + dump_signals + watch_signals, key=lambda x: x["confidence"], reverse=True)[:10]:
        log.info(
            "  %s | %s | confidence=%.2f | cause=%s",
            signal["symbol"],
            signal["signal"],
            signal["confidence"],
            signal["suspected_cause"],
        )

    weekday = datetime.now(timezone.utc).weekday()
    if weekday == 0:
        _send_monday_resumption_notice(notifier)

    if _is_weekend_utc():
        log.info("Weekend: no new trades opened. Existing positions still monitored.")
        if pump_signals:
            notifier.send(
                "*WEEKEND - SKIPPING NEW TRADES*\n"
                f"`{len(pump_signals)}` pump signal(s) found but new entries are blocked.\n"
                "Resuming Monday."
            )
    else:
        log.info("Risk Manager: evaluating all signals")
        approvals = risk_manager.evaluate(signals, execution_halted=circuit_breaker.is_halted())
        approved = [a for a in approvals if a["approved"]]
        log.info("Risk Manager: approved=%s rejected=%s", len(approved), len(approvals) - len(approved))

        log.info("Execution Agent: executing approved trades")
        results = executor.execute(approved)
        filled = [r for r in results if r["status"] == "filled"]
        log.info("Execution Agent: filled=%s attempted=%s", len(filled), len(results))

    if not pump_signals:
        notifier.send(
            "*HEARTBEAT - NO PUMP SIGNALS FOUND*\n"
            f"Watch signals: `{len(watch_signals)}`\n"
            f"Mode: `{'paper' if CONFIG['paper_trading_mode'] else 'live'}`\n"
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        )

    log.info("Cycle complete.\n")


if __name__ == "__main__":
    run()
