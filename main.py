"""
CoinSwitch Multi-Agent Momentum Bot (v2 — Trailing Stop)

GitHub Actions runs one cycle every 15 minutes, 24/7:
  Monitor → Data Collector → Signal Detector → Risk Manager → Execution

Strategy: 3/4-condition momentum signal, 40% position sizing,
          hard SL 1.5%, trailing stop activates at +1.5%, TP at 4%.
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
try:
    logging.getLogger().handlers[0].stream.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass
log = logging.getLogger(__name__)

MONDAY_NOTICE_FILE = "last_monday_notice.txt"


def _send_monday_resumption_notice(notifier: TelegramNotifier) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    last_date = ""
    if os.path.exists(MONDAY_NOTICE_FILE):
        with open(MONDAY_NOTICE_FILE, encoding="utf-8") as f:
            last_date = f.read().strip()
    if last_date != today:
        notifier.send(
            "*🟢 WEEKEND RESUMPTION*\n"
            "Markets are open — bot is back online and scanning."
        )
        with open(MONDAY_NOTICE_FILE, "w", encoding="utf-8") as f:
            f.write(today)


def _is_weekend_utc() -> bool:
    return datetime.now(timezone.utc).weekday() in (5, 6)


def _notify_trade_opened(notifier: TelegramNotifier, result: dict, approval: dict, cfg: dict) -> None:
    """Rich Telegram notification when a trade is filled."""
    if result.get("status") != "filled":
        return
    symbol = result["symbol"]
    price = result["filled_price"]
    qty = result["filled_qty"]
    size_usd = approval["position_size_usd"]
    sl_pct = approval["stop_loss_pct"]
    tp_pct = approval["take_profit_pct"]
    sl_price = round(price * (1 - sl_pct / 100.0), 8)
    tp_price = round(price * (1 + tp_pct / 100.0), 8)
    mode = "📄 PAPER" if cfg["paper_trading_mode"] else "🔴 LIVE"
    notifier.send(
        f"🚀 *TRADE OPENED* `{symbol}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Mode   : `{mode}`\n"
        f"Entry  : `{price}`\n"
        f"Qty    : `{qty}`\n"
        f"Size   : `${size_usd:.2f}` USDT\n"
        f"Hard SL: `{sl_price}` (-{sl_pct}%)\n"
        f"TP     : `{tp_price}` (+{tp_pct}%)\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Trail activates at +{cfg['trail_activation_pct']}%, "
        f"trails {cfg['trail_pct']}% below peak"
    )


def run() -> None:
    log.info("=" * 60)
    log.info(
        "CoinSwitch Momentum Bot — %s",
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    log.info("=" * 60)

    if not CONFIG["api_key"] or not CONFIG["api_secret"]:
        log.error("CoinSwitch API credentials not set. Check GitHub Secrets / .env")
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

    mode_str = "PAPER" if CONFIG["paper_trading_mode"] else "LIVE"
    log.info("Mode: %s | Capital: $%.2f", mode_str, CONFIG["paper_portfolio_usdt"])

    # ── Step 1: Monitor existing positions first ──────────────────────────────
    log.info("Step 1/5 — Monitor open positions")
    monitor_report = monitor.monitor()
    log.info("Open positions: %s | Closed this cycle: %s",
             monitor_report["open_positions"], len(monitor_report.get("closed", [])))

    # ── Step 2: Collect market data ───────────────────────────────────────────
    log.info("Step 2/5 — Collect market data")
    market_data = collector.collect()
    errors = [item for item in market_data if item.get("error")]
    valid = len(market_data) - len(errors)
    log.info("Collected: valid=%s errors=%s", valid, len(errors))

    if market_data and len(errors) == len(market_data):
        state = circuit_breaker.record_error("all_collector_items_failed")
        log.error("All data collection failed. Circuit breaker: %s", state)
    else:
        circuit_breaker.record_success()

    # ── Step 3: Detect signals ────────────────────────────────────────────────
    log.info("Step 3/5 — Detect signals")
    signals = detector.classify(market_data)
    pump_signals = [s for s in signals if s["signal"] == "pump"]
    dump_signals = [s for s in signals if s["signal"] == "dump"]
    watch_signals = [s for s in signals if s["signal"] == "watch"]
    log.info("Signals: pump=%s dump=%s watch=%s", len(pump_signals), len(dump_signals), len(watch_signals))

    top_signals = sorted(
        pump_signals + watch_signals,
        key=lambda x: x["confidence"],
        reverse=True,
    )[:8]
    for s in top_signals:
        log.info(
            "  %-15s | %-5s | conf=%.3f | %s",
            s["symbol"], s["signal"], s["confidence"], s["suspected_cause"],
        )

    # ── Monday resumption notice ──────────────────────────────────────────────
    if datetime.now(timezone.utc).weekday() == 0:
        _send_monday_resumption_notice(notifier)

    # ── Step 4 & 5: Risk + Execution (weekdays only) ──────────────────────────
    if _is_weekend_utc():
        log.info("Weekend — skipping new entries. Monitoring continues.")
        if pump_signals:
            notifier.send(
                f"*⏸ WEEKEND — SIGNALS FOUND BUT BLOCKED*\n"
                f"`{len(pump_signals)}` pump signal(s) detected.\n"
                f"New entries resume Monday."
            )
    else:
        log.info("Step 4/5 — Risk evaluation")
        approvals = risk_manager.evaluate(signals, execution_halted=circuit_breaker.is_halted())
        approved = [a for a in approvals if a["approved"]]
        rejected = [a for a in approvals if not a["approved"]]
        log.info("Approved: %s | Rejected: %s", len(approved), len(rejected))

        # Log rejection reasons for debugging
        reject_reasons: dict[str, int] = {}
        for r in rejected:
            reason = r.get("reason", "unknown")
            reject_reasons[reason] = reject_reasons.get(reason, 0) + 1
        for reason, count in sorted(reject_reasons.items(), key=lambda x: -x[1])[:5]:
            log.info("  Reject reason: %s × %s", reason, count)

        log.info("Step 5/5 — Execute trades")
        results = executor.execute(approved)
        filled = [r for r in results if r["status"] == "filled"]
        log.info("Filled: %s / attempted: %s", len(filled), len(results))

        # Send Telegram notification for each filled trade
        approval_map = {a["symbol"]: a for a in approved}
        for result in filled:
            approval = approval_map.get(result["symbol"], {})
            _notify_trade_opened(notifier, result, approval, CONFIG)

    # ── Heartbeat when no pumps found ─────────────────────────────────────────
    if not pump_signals:
        notifier.send(
            f"*💓 HEARTBEAT — NO PUMP SIGNALS*\n"
            f"Watch: `{len(watch_signals)}` | Mode: `{mode_str}`\n"
            f"`{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}`"
        )

    log.info("Cycle complete.\n")


if __name__ == "__main__":
    run()
