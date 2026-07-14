"""
Dual-Exchange Execution Layer
==============================
Mirrors every approved trade on BOTH CoinSwitch AND Delta Exchange India.

Architecture:
  - Same signal → same direction → placed on both exchanges independently
  - Each exchange has its own open_trades file suffix (_cs / _delta)
  - If one exchange fails, the other still executes (best-effort)
  - Monitor checks both files independently each cycle
  - P&L tracked per exchange

Trade files:
  open_trades_cs.json     — CoinSwitch open positions
  open_trades_delta.json  — Delta Exchange India open positions
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from agents import (
    AuditLogger,
    ExecutionAgent,
    MonitorReporterAgent,
    execution_result,
    load_json,
    pct_change,
    save_json,
    utc_iso,
)
from coinswitch_client import CoinSwitchClient
from delta_client import DeltaClient
from notifier import TelegramNotifier

log = logging.getLogger(__name__)

CS_TRADES_FILE    = Path("open_trades_cs.json")
DELTA_TRADES_FILE = Path("open_trades_delta.json")


class DualExecutionAgent:
    """
    Wraps CoinSwitch ExecutionAgent + Delta direct execution.
    For each approval:
      1. Execute on CoinSwitch (original logic)
      2. Execute same trade on Delta Exchange India
      3. Record both results independently
    """

    def __init__(
        self,
        cfg: dict,
        cs_client: CoinSwitchClient,
        delta_client: DeltaClient,
        notifier: TelegramNotifier,
        audit: AuditLogger,
    ):
        self.cfg = cfg
        self.cs_client = cs_client
        self.delta_client = delta_client
        self.notifier = notifier
        self.audit = audit
        # Patch the file paths for each exchange
        self._cs_executor = ExecutionAgent(cfg, cs_client, audit)
        self._cs_executor._trades_file = CS_TRADES_FILE

    def execute(self, approvals: list[dict]) -> list[dict]:
        """Execute all approved trades on both exchanges."""
        all_results = []
        for approval in approvals:
            if approval.get("approved") is not True:
                continue
            cs_result = self._execute_coinswitch(approval)
            delta_result = self._execute_delta(approval)
            combined = {
                "symbol": approval["symbol"],
                "coinswitch": cs_result,
                "delta": delta_result,
                "timestamp": utc_iso(),
            }
            all_results.append(combined)
            self._notify_dual_entry(approval, cs_result, delta_result)

        self.audit.write("DualExecutionAgent", {"count": len(all_results), "results": all_results})
        return all_results

    # ── CoinSwitch execution ─────────────────────────────────────────────────

    def _execute_coinswitch(self, approval: dict) -> dict:
        """Execute on CoinSwitch using original logic, saving to CS-specific file."""
        import agents as _agents
        original_file = _agents.OPEN_TRADES_FILE
        _agents.OPEN_TRADES_FILE = CS_TRADES_FILE
        try:
            results = self._cs_executor.execute([approval])
            return results[0] if results else {"status": "no_result"}
        except Exception as exc:
            log.error("CoinSwitch execution failed for %s: %s", approval["symbol"], exc)
            return {"status": "error", "reason": str(exc), "symbol": approval["symbol"]}
        finally:
            _agents.OPEN_TRADES_FILE = original_file

    # ── Delta Exchange execution ─────────────────────────────────────────────

    def _execute_delta(self, approval: dict) -> dict:
        """Execute the same trade on Delta Exchange India."""
        signal = approval["signal"]
        symbol = approval["symbol"]

        try:
            price_at_signal = float(signal["supporting_data"]["price"])
            current_price = float(self.delta_client.get_ticker_price(symbol))
        except Exception as exc:
            log.error("Delta price fetch failed for %s: %s", symbol, exc)
            return {"status": "error", "reason": f"price_fetch:{exc}", "symbol": symbol}

        if current_price <= 0:
            return {"status": "error", "reason": "zero_price", "symbol": symbol}

        slippage = abs(pct_change(current_price, price_at_signal))
        if slippage > self.cfg["slippage_tolerance_pct"]:
            log.warning("Delta stale signal %s: slippage=%.2f%%", symbol, slippage)
            return {
                "status": "rejected",
                "reason": f"stale_signal_{slippage:.2f}pct",
                "symbol": symbol,
            }

        # Delta uses integer contract sizes — calculate qty
        position_usd = float(approval["position_size_usd"])

        # Get Delta balance for position sizing
        if not self.cfg["paper_trading_mode"]:
            try:
                delta_balance = max(self.delta_client.get_usdt_balance(), 0.0)
            except Exception as exc:
                log.warning("Delta balance fetch failed: %s", exc)
                delta_balance = 0.0
            if delta_balance < self.cfg["min_order_usdt"]:
                return {
                    "status": "rejected",
                    "reason": f"delta_balance_{delta_balance:.2f}_too_low",
                    "symbol": symbol,
                }
            # Scale position to Delta balance
            position_usd = min(
                position_usd,
                delta_balance * self.cfg["max_position_pct"] / 100.0,
            )

        qty = round(position_usd / current_price, 6)
        if qty <= 0:
            return {"status": "rejected", "reason": "zero_quantity", "symbol": symbol}

        if self.cfg["paper_trading_mode"]:
            order_id = f"DELTA-PAPER-{approval['signal_id']}"
            result = {
                "status": "filled",
                "reason": "delta_paper_trade",
                "symbol": symbol,
                "order_id": order_id,
                "filled_price": current_price,
                "filled_qty": qty,
                "exchange": "delta",
            }
            self._record_delta_trade(approval, result, current_price, qty)
            return result

        # Live Delta execution
        last_error = None
        for attempt in range(1, self.cfg["max_retries"] + 1):
            try:
                limit_price = round(
                    current_price * (1 + self.cfg["limit_slippage_offset_pct"] / 100.0), 8
                )
                order = self.delta_client.place_order(
                    symbol, "buy", self.cfg["risk_order_type"], qty, price=limit_price
                )
                order_id = order.get("id") or order.get("order_id")
                if not order_id:
                    return {"status": "error", "reason": "missing_order_id", "symbol": symbol}

                # Poll for fill
                filled, filled_qty = False, 0.0
                product_id = self.delta_client.symbol_to_product_id(symbol)
                for _ in range(5):
                    status = self.delta_client.get_order(order_id, product_id)
                    filled, filled_qty = self.delta_client.order_fill_status(status)
                    if filled:
                        break
                    time.sleep(2)

                if not filled:
                    return {
                        "status": "partial",
                        "reason": "order_pending",
                        "symbol": symbol,
                        "order_id": str(order_id),
                    }

                result = {
                    "status": "filled",
                    "reason": "delta_live_filled",
                    "symbol": symbol,
                    "order_id": str(order_id),
                    "filled_price": current_price,
                    "filled_qty": round(filled_qty or qty, 6),
                    "exchange": "delta",
                }
                self._record_delta_trade(approval, result, current_price, filled_qty or qty)
                return result

            except Exception as exc:
                last_error = str(exc)
                log.warning("Delta execution attempt %s failed for %s: %s", attempt, symbol, exc)
                time.sleep(2)

        return {"status": "error", "reason": last_error or "execution_failed", "symbol": symbol}

    def _record_delta_trade(
        self, approval: dict, result: dict, price: float, qty: float
    ) -> None:
        signal = approval["signal"]
        hard_sl = round(price * (1 - approval["stop_loss_pct"] / 100.0), 8)
        take_profit = round(price * (1 + approval["take_profit_pct"] / 100.0), 8)

        # Get Delta product_id for this symbol
        product_id = self.delta_client.symbol_to_product_id(approval["symbol"])

        trade = {
            "symbol": approval["symbol"],
            "coin": approval["symbol"].split("/")[0],
            "qty": round(qty, 6),
            "entry_price": price,
            "peak_price": price,
            "hard_sl": hard_sl,
            "take_profit": take_profit,
            "trail_active": False,
            "trailing_stop": None,
            "buy_id": result.get("order_id", ""),
            "opened_at": utc_iso(),
            "usdt_used": approval["position_size_usd"],
            "score": round(signal["confidence"] * 100, 2),
            "highest_profit_pct": 0.0,
            "paper": self.cfg["paper_trading_mode"],
            "signal_id": approval["signal_id"],
            "approval_token": approval["approval_token"],
            "exchange": "delta",
            "product_id": product_id,
        }
        trades = load_json(DELTA_TRADES_FILE, [])
        trades.append(trade)
        save_json(DELTA_TRADES_FILE, trades)

    def _notify_dual_entry(
        self, approval: dict, cs_result: dict, delta_result: dict
    ) -> None:
        symbol = approval["symbol"]
        cs_status = cs_result.get("status", "?")
        delta_status = delta_result.get("status", "?")
        price = delta_result.get("filled_price") or cs_result.get("filled_price", 0)
        size = approval["position_size_usd"]
        mode = "📄 PAPER" if self.cfg["paper_trading_mode"] else "🔴 LIVE"

        cs_icon = "✅" if cs_status == "filled" else "❌"
        delta_icon = "✅" if delta_status == "filled" else "❌"

        self.notifier.send(
            f"🚀 *DUAL TRADE OPENED* `{symbol}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Mode      : `{mode}`\n"
            f"Entry     : `{price}`\n"
            f"Size      : `${size:.2f}` USDT each\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{cs_icon} CoinSwitch : `{cs_status}`\n"
            f"{delta_icon} Delta India: `{delta_status}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"SL: -{self.cfg['stop_loss_pct']}% | "
            f"TP: +{self.cfg['take_profit_pct']}% | "
            f"Trail: +{self.cfg['trail_activation_pct']}%"
        )


class DualMonitorAgent:
    """
    Monitors open positions on BOTH exchanges each cycle.
    Checks CS trades file and Delta trades file separately.
    """

    def __init__(
        self,
        cfg: dict,
        cs_client: CoinSwitchClient,
        delta_client: DeltaClient,
        notifier: TelegramNotifier,
        audit: AuditLogger,
    ):
        self.cfg = cfg
        self.cs_client = cs_client
        self.delta_client = delta_client
        self.notifier = notifier
        self.audit = audit

    def monitor(self) -> dict:
        import agents as _agents
        import math

        total_open = 0
        total_closed = []

        # ── Monitor CoinSwitch positions ─────────────────────────────────────
        cs_trades = load_json(CS_TRADES_FILE, [])
        if cs_trades:
            original = _agents.OPEN_TRADES_FILE
            _agents.OPEN_TRADES_FILE = CS_TRADES_FILE
            monitor = MonitorReporterAgent(
                self.cfg, self.cs_client, self.notifier, self.audit
            )
            cs_report = monitor.monitor()
            _agents.OPEN_TRADES_FILE = original
            total_open += cs_report.get("open_positions", 0)
            total_closed.extend(cs_report.get("closed", []))

        # ── Monitor Delta positions ───────────────────────────────────────────
        delta_trades = load_json(DELTA_TRADES_FILE, [])
        if delta_trades:
            remaining, closed = [], []
            for trade in delta_trades:
                try:
                    current = float(self.delta_client.get_ticker_price(trade["symbol"]))
                    if current <= 0:
                        remaining.append(trade)
                        continue

                    pnl_pct = pct_change(current, float(trade["entry_price"]))
                    trade["highest_profit_pct"] = round(
                        max(float(trade.get("highest_profit_pct", 0)), pnl_pct), 4
                    )
                    if current > float(trade.get("peak_price", trade["entry_price"])):
                        trade["peak_price"] = current

                    if not trade.get("trail_active") and pnl_pct >= self.cfg["trail_activation_pct"]:
                        trade["trail_active"] = True
                        log.info("Delta trail ACTIVATED for %s at +%.2f%%", trade["symbol"], pnl_pct)

                    if trade.get("trail_active"):
                        new_stop = round(
                            float(trade["peak_price"]) * (1 - self.cfg["trail_pct"] / 100.0), 8
                        )
                        trade["trailing_stop"] = max(float(trade.get("trailing_stop") or 0), new_stop)

                    active_stop = float(trade.get("trailing_stop") or trade["hard_sl"])
                    reason = None
                    if current <= active_stop:
                        reason = "trailing_stop" if trade.get("trail_active") else "stop_loss"
                    elif current >= float(trade.get("take_profit", math.inf)):
                        reason = "take_profit"

                    if reason:
                        closed_trade = self._close_delta_trade(trade, current, pnl_pct, reason)
                        closed.append(closed_trade)
                        total_closed.append(closed_trade)
                    else:
                        remaining.append(trade)

                except Exception as exc:
                    log.warning("Delta monitor failed for %s: %s", trade.get("symbol"), exc)
                    trade["last_monitor_error"] = str(exc)
                    remaining.append(trade)

            save_json(DELTA_TRADES_FILE, remaining)
            total_open += len(remaining)

        report = {
            "open_positions": total_open,
            "closed": total_closed,
            "timestamp": utc_iso(),
        }
        self.audit.write("DualMonitorAgent", report)
        log.info(
            "DualMonitor: open=%s closed_this_cycle=%s",
            total_open, len(total_closed),
        )
        return report

    def _close_delta_trade(
        self, trade: dict, current: float, pnl_pct: float, reason: str
    ) -> dict:
        from agents import load_json, save_json, DAILY_PNL_FILE, utc_now
        pnl_usdt = round(float(trade["usdt_used"]) * pnl_pct / 100.0, 2)

        if not trade.get("paper"):
            sell_price = round(current * (1 - self.cfg["limit_slippage_offset_pct"] / 100.0), 8)
            try:
                self.delta_client.place_order(
                    trade["symbol"], "sell", self.cfg["risk_order_type"],
                    float(trade["qty"]), price=sell_price,
                )
            except Exception as exc:
                log.error("Delta SELL failed for %s: %s", trade["symbol"], exc)

        today = utc_now().date().isoformat()
        pnl = load_json(DAILY_PNL_FILE, {})
        pnl.setdefault(today, {"realized_pnl_usdt": 0.0, "closed_trades": 0})
        pnl[today]["realized_pnl_usdt"] = round(
            float(pnl[today]["realized_pnl_usdt"]) + pnl_usdt, 2
        )
        pnl[today]["closed_trades"] = int(pnl[today]["closed_trades"]) + 1
        save_json(DAILY_PNL_FILE, pnl)

        icon = "✅" if pnl_pct >= 0 else "🔴"
        reason_label = {
            "take_profit": "🎯 TAKE PROFIT",
            "trailing_stop": "📈 TRAILING STOP",
            "stop_loss": "🛑 STOP LOSS",
        }.get(reason, reason.upper())

        self.notifier.send(
            f"{icon} *DELTA TRADE CLOSED* `{trade['symbol']}`\n"
            f"Reason : `{reason_label}`\n"
            f"Entry  : `{trade['entry_price']}` → Exit: `{current}`\n"
            f"P&L    : `{pnl_pct:+.2f}%` (`{pnl_usdt:+.2f}` USDT)\n"
            f"Mode   : `{'paper' if trade.get('paper') else 'LIVE'}`"
        )
        log.info(
            "DELTA CLOSED %s | reason=%s | pnl=%.2f%% | pnl_usdt=%.2f",
            trade["symbol"], reason, pnl_pct, pnl_usdt,
        )
        return {
            "symbol": trade["symbol"],
            "exchange": "delta",
            "reason": reason,
            "entry": trade["entry_price"],
            "exit": current,
            "pnl_pct": round(pnl_pct, 4),
            "pnl_usdt": pnl_usdt,
        }
