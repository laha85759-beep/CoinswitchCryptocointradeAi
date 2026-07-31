"""
CoinSwitch + Delta Exchange India — Dual-Exchange Momentum Bot (v3)

Every cycle:
  1. Monitor open positions on BOTH exchanges
  2. Collect market data (CoinSwitch OHLCV — same signal source)
  3. Detect momentum pump signals
  4. Risk-manage approvals
  5. Execute approved trades on BOTH CoinSwitch AND Delta Exchange India

Same signal → same trade → two exchanges → doubled exposure, same strategy.
"""

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agents import (
    AuditLogger,
    CircuitBreaker,
    DataCollectorAgent,
    RiskManagerAgent,
    SignalDetectorAgent,
    load_json,
)
import agents as _agents
from coinswitch_client import CoinSwitchClient
from config import CONFIG
from delta_client import DeltaClient
from dual_exchange import CS_TRADES_FILE, DualExecutionAgent, DualMonitorAgent
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
DAILY_REPORT_FILE = Path("last_daily_report.txt")
IST = timezone(timedelta(hours=5, minutes=30))


def _send_monday_resumption_notice(notifier: TelegramNotifier) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    last_date = ""
    if os.path.exists(MONDAY_NOTICE_FILE):
        with open(MONDAY_NOTICE_FILE, encoding="utf-8") as f:
            last_date = f.read().strip()
    if last_date != today:
        notifier.send(
            "*🟢 WEEKEND RESUMPTION*\n"
            "Markets are open — bot is back online on both exchanges."
        )
        with open(MONDAY_NOTICE_FILE, "w", encoding="utf-8") as f:
            f.write(today)


def _is_weekend_utc() -> bool:
    return datetime.now(timezone.utc).weekday() in (5, 6)


def _send_daily_report_if_due(
    notifier: TelegramNotifier,
    mode_str: str,
    delta_enabled: bool,
    monitor_report: dict,
) -> None:
    now_ist = datetime.now(IST)
    if now_ist.hour < 20:  # Allow daily report from 20:00 IST onwards
        return

    today_ist = now_ist.date().isoformat()
    last_sent = DAILY_REPORT_FILE.read_text(encoding="utf-8").strip() if DAILY_REPORT_FILE.exists() else ""
    if last_sent == today_ist:
        return

    pnl_by_day = load_json(Path("daily_pnl.json"), {})
    today_pnl = pnl_by_day.get(datetime.now(timezone.utc).date().isoformat(), {})
    realized_usdt = float(today_pnl.get("realized_pnl_usdt", 0.0) or 0.0)
    realized_inr = round(realized_usdt * 88.0, 2)
    closed_trades = int(today_pnl.get("closed_trades", 0) or 0)
    wins = int(today_pnl.get("wins", 0) or 0)
    losses = int(today_pnl.get("losses", 0) or 0)
    win_rate = round((wins / closed_trades * 100), 1) if closed_trades > 0 else 100.0

    cs_open = len(load_json(Path("open_trades_cs.json"), []))
    delta_open = len(load_json(Path("open_trades_delta.json"), []))
    closed_this_cycle = len(monitor_report.get("closed", []))

    report = (
        f"📊 *COINSWITCH + DELTA INDIA DAILY REPORT*\n"
        f"📅 *Date*: `{today_ist}` | *Time*: `{now_ist.strftime('%H:%M IST')}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ *DAILY PERFORMANCE*\n"
        f"• Realized PnL   : `{realized_usdt:+.2f} USDT` (`₹{realized_inr:+.2f} INR`)\n"
        f"• Closed Trades  : `{closed_trades}` Today (`{closed_this_cycle}` this cycle)\n"
        f"• Win/Loss Ratio : `{wins} Wins` / `{losses} Losses` (`{win_rate}% Win Rate`)\n"
        f"• Risk Parameters: SL `-0.05%` | TP `+4.8%`\n\n"
        f"🏛️ *LIVE EXCHANGE STATUS*\n"
        f"• CoinSwitch Pro : `ACTIVE` ({cs_open} Open Spot Trades)\n"
        f"• Delta India    : `{'ACTIVE' if delta_enabled else 'OFF'}` ({delta_open} Open Futures Trades)\n\n"
        f"🤖 *ACTIVE AI TRADING AGENTS*\n"
        f"• PP SuperTrend + Ghost Protocol V3\n"
        f"• QuickScalpAgent (2.5x Lot Size | 1m/3m)\n"
        f"• ForexFactoryNewsAgent (High-Impact Economic News)\n\n"
        f"🟢 *STATUS*: `24/7 Live Automation Active via GitHub`"
    )

    notifier.send(report)
    DAILY_REPORT_FILE.write_text(today_ist, encoding="utf-8")


def run() -> None:
    log.info("=" * 60)
    log.info(
        "Dual-Exchange Bot (CS + Delta India) — %s",
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
    log.info("=" * 60)

    # ── Validate credentials ──────────────────────────────────────────────────
    if not CONFIG["api_key"] or not CONFIG["api_secret"]:
        log.error("CoinSwitch API credentials missing. Check GitHub Secrets / .env")
        sys.exit(1)
    if not CONFIG["delta_api_key"] or not CONFIG["delta_api_secret"]:
        log.warning("Delta Exchange API credentials not set — Delta trades will be SKIPPED")

    # ── Initialise clients ────────────────────────────────────────────────────
    cs_client = CoinSwitchClient(
        CONFIG["api_key"],
        CONFIG["api_secret"],
        rate_limit_delay=CONFIG.get("request_delay_seconds", 1.0),
    )
    delta_client = DeltaClient(
        CONFIG["delta_api_key"],
        CONFIG["delta_api_secret"],
        rate_limit_delay=0.5,
    )
    notifier = TelegramNotifier(CONFIG["telegram_token"], CONFIG["telegram_chat_id"])
    audit    = AuditLogger()
    circuit_breaker = CircuitBreaker(CONFIG, audit)

    # ── Initialise agents ────────────────────────────────────────────────────
    dual_monitor  = DualMonitorAgent(CONFIG, cs_client, delta_client, notifier, audit)
    collector     = DataCollectorAgent(CONFIG, cs_client, audit)
    detector      = SignalDetectorAgent(CONFIG, audit)
    risk_manager  = RiskManagerAgent(CONFIG, cs_client, audit, delta_client=delta_client)
    dual_executor = DualExecutionAgent(CONFIG, cs_client, delta_client, notifier, audit)

    mode_str = "PAPER" if CONFIG["paper_trading_mode"] else "LIVE"
    delta_enabled = bool(CONFIG["delta_api_key"] and CONFIG["delta_api_secret"])
    log.info("Mode: %s | CoinSwitch: ✓ | Delta India: %s",
             mode_str, "✓" if delta_enabled else "✗ (no creds)")

    # ── Step 1: Monitor both exchanges ────────────────────────────────────────
    log.info("Step 1/5 — Monitor open positions (CS + Delta)")
    monitor_report = dual_monitor.monitor()
    log.info("Open: %s | Closed this cycle: %s",
             monitor_report["open_positions"], len(monitor_report.get("closed", [])))

    # ── Step 2: Collect market data ───────────────────────────────────────────
    log.info("Step 2/5 — Collect market data")
    market_data = collector.collect()
    errors = [item for item in market_data if item.get("error")]
    valid  = len(market_data) - len(errors)
    log.info("Collected: valid=%s errors=%s", valid, len(errors))

    if market_data and len(errors) == len(market_data):
        state = circuit_breaker.record_error("all_collector_items_failed")
        log.error("All data collection failed. Circuit breaker: %s", state)
    else:
        circuit_breaker.record_success()

    # ── Step 2.5: Forex Factory Economic News Execution ──────────────────────
    try:
        from forex_factory_agent import ForexFactoryNewsAgent
        ff_agent = ForexFactoryNewsAgent(CONFIG, cs_client, delta_client, notifier, audit)
        news_trades = ff_agent.process_and_execute_news_trades()
        if news_trades:
            log.info("ForexFactoryNewsAgent: Executed %s high-impact news trades", len(news_trades))
    except Exception as news_exc:
        log.warning("ForexFactoryNewsAgent notice: %s", news_exc)

    # ── Step 2.6: Quick Scalping Agent Execution ──────────────────────────────
    try:
        from scalp_agent import QuickScalpAgent
        scalp_agent = QuickScalpAgent(CONFIG, cs_client, delta_client, notifier, audit)
        symbols_to_scalp = [d["symbol"] for d in market_data if not d.get("error")]
        scalp_trades = scalp_agent.scan_and_execute_scalps(symbols_to_scalp)
        if scalp_trades:
            log.info("QuickScalpAgent: Executed %s quick scalp trades", len(scalp_trades))
    except Exception as scalp_exc:
        log.warning("QuickScalpAgent notice: %s", scalp_exc)

    # ── Step 3: Detect signals ────────────────────────────────────────────────
    log.info("Step 3/5 — Detect signals")
    signals = detector.classify(market_data)
    pump_signals  = [s for s in signals if s["signal"] == "pump"]
    watch_signals = [s for s in signals if s["signal"] == "watch"]
    dump_signals  = [s for s in signals if s["signal"] == "dump"]
    log.info("Signals: pump=%s dump=%s watch=%s",
             len(pump_signals), len(dump_signals), len(watch_signals))

    for s in sorted(pump_signals + watch_signals, key=lambda x: x["confidence"], reverse=True)[:8]:
        log.info("  %-15s | %-5s | conf=%.3f | %s",
                 s["symbol"], s["signal"], s["confidence"], s["suspected_cause"])

    if datetime.now(timezone.utc).weekday() == 0:
        _send_monday_resumption_notice(notifier)

    # ── Step 4 & 5: Risk + Dual Execution ────────────────────────────────────
    log.info("Step 4/5 — Risk evaluation")
    _original_atf = _agents.OPEN_TRADES_FILE
    _agents.OPEN_TRADES_FILE = CS_TRADES_FILE
    approvals = risk_manager.evaluate(
        signals, execution_halted=circuit_breaker.is_halted()
    )
    _agents.OPEN_TRADES_FILE = _original_atf
    approved = [a for a in approvals if a["approved"]]
    rejected = [a for a in approvals if not a["approved"]]
    log.info("Approved: %s | Rejected: %s", len(approved), len(rejected))

    # Log top rejection reasons
    reject_reasons: dict[str, int] = {}
    for r in rejected:
        k = r.get("reason", "unknown")
        reject_reasons[k] = reject_reasons.get(k, 0) + 1
    for reason, count in sorted(reject_reasons.items(), key=lambda x: -x[1])[:5]:
        log.info("  Reject: %s × %s", reason, count)

    log.info("Step 5/5 — Execute on CoinSwitch + Delta India")
    results = dual_executor.execute(approved)
    cs_filled    = sum(1 for r in results if r.get("coinswitch", {}).get("status") == "filled")
    delta_filled = sum(1 for r in results if r.get("delta", {}).get("status") == "filled")
    log.info("Filled — CoinSwitch: %s | Delta: %s | attempted: %s",
             cs_filled, delta_filled, len(results))

    # ── Step 6: Options Hedge Agent (Delta Exchange India) ───────────────────
    if delta_enabled and CONFIG.get("options_enabled", True):
        try:
            from options_agent import OptionsHedgeAgent, OptionsMonitorAgent
            opt_monitor = OptionsMonitorAgent(CONFIG, delta_client, notifier)
            opt_mon_res = opt_monitor.monitor()
            log.info("Options Monitor — Open: %s | Closed: %s",
                     opt_mon_res.get("open_options", 0), len(opt_mon_res.get("closed", [])))

            opt_agent = OptionsHedgeAgent(CONFIG, delta_client, notifier)
            for asset in CONFIG.get("options_assets", ["ETH", "BTC"]):
                try:
                    price = delta_client.get_ticker_price(f"{asset}/USDT")
                    if price > 0:
                        plan = opt_agent.generate_trade_plan(asset, price)
                        if plan:
                            opt_res = opt_agent.execute_plan(plan)
                            log.info("Options trade result for %s: %s", asset, opt_res.get("status"))
                except Exception as ex:
                    log.warning("Options trade plan error for %s: %s", asset, ex)
        except Exception as opt_exc:
            log.warning("Options Hedge Agent step error: %s", opt_exc)

    # Daily summary report if due
    _send_daily_report_if_due(notifier, mode_str, delta_enabled, monitor_report)

    log.info("Cycle complete.\n")


if __name__ == "__main__":
    run()
