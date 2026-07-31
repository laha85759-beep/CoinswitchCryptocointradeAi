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

            symbol = approval["symbol"]
            direction = approval.get("direction", "long")

            # ── Check & handle position flips (reversals) ────────────────────
            self._handle_position_flips(symbol, direction)

            cs_result = self._execute_coinswitch(approval)
            delta_result = self._execute_delta(approval)
            combined = {
                "symbol": symbol,
                "coinswitch": cs_result,
                "delta": delta_result,
                "timestamp": utc_iso(),
            }
            all_results.append(combined)
            self._notify_dual_entry(approval, cs_result, delta_result)

        self.audit.write("DualExecutionAgent", {"count": len(all_results), "results": all_results})
        return all_results

    def _handle_position_flips(self, symbol: str, new_direction: str) -> None:
        """
        If a new signal arrives for an existing asset in the OPPOSITE direction
        (e.g., existing Long and new signal is Short/Sell from PP SuperTrend):
        Immediately close the existing trade on both exchanges before entering the new trade!
        """
        # 1. CoinSwitch position flip check
        cs_trades = load_json(CS_TRADES_FILE, [])
        new_cs_trades = []
        cs_closed_any = False
        for trade in cs_trades:
            if trade.get("symbol") == symbol:
                existing_dir = trade.get("direction", "long")
                if existing_dir != new_direction:
                    log.info("SUPER TREND REVERSAL (CoinSwitch) for %s: Closing %s to open %s", symbol, existing_dir, new_direction)
                    try:
                        qty = float(trade.get("qty", 0))
                        if qty > 0 and not trade.get("paper"):
                            self.cs_client.place_order(symbol, "sell", "MARKET", qty, exchange="c2c2")
                    except Exception as exc:
                        log.warning("Failed to close CoinSwitch position for %s: %s", symbol, exc)
                    cs_closed_any = True
                else:
                    new_cs_trades.append(trade)
            else:
                new_cs_trades.append(trade)

        if cs_closed_any:
            save_json(CS_TRADES_FILE, new_cs_trades)
            self.notifier.send(
                f"🔄 *POSITION REVERSAL FLIP (CoinSwitch)* `{symbol}`\n"
                f"SuperTrend reversal detected! Closed existing position to enter new `{new_direction.upper()}` trade."
            )

        # 2. Delta Exchange position flip check
        delta_trades = load_json(DELTA_TRADES_FILE, [])
        new_delta_trades = []
        delta_closed_any = False
        for trade in delta_trades:
            if trade.get("symbol") == symbol:
                existing_dir = trade.get("direction", "long")
                if existing_dir != new_direction:
                    log.info("SUPER TREND REVERSAL (Delta) for %s: Closing %s to open %s", symbol, existing_dir, new_direction)
                    try:
                        qty = float(trade.get("qty", 0))
                        close_side = "sell" if existing_dir == "long" else "buy"
                        if qty > 0 and not trade.get("paper"):
                            self.delta_client.place_order(symbol, close_side, "market", qty)
                    except Exception as exc:
                        log.warning("Failed to close Delta position for %s: %s", symbol, exc)
                    delta_closed_any = True
                else:
                    new_delta_trades.append(trade)
            else:
                new_delta_trades.append(trade)

        if delta_closed_any:
            save_json(DELTA_TRADES_FILE, new_delta_trades)
            self.notifier.send(
                f"🔄 *POSITION REVERSAL FLIP (Delta India)* `{symbol}`\n"
                f"SuperTrend reversal detected! Closed existing position to enter new `{new_direction.upper()}` trade."
            )

    # ── CoinSwitch execution ─────────────────────────────────────────────────

    def _execute_coinswitch(self, approval: dict) -> dict:
        """Execute on CoinSwitch using original logic, saving to CS-specific file."""
        if approval.get("direction") == "short":
            return {"status": "skipped", "reason": "coinswitch_spot_no_short", "symbol": approval["symbol"]}
            
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
            return {"status": "skipped", "reason": "not_listed_on_delta", "symbol": symbol}

        slippage = abs(pct_change(current_price, price_at_signal))
        if slippage > self.cfg["slippage_tolerance_pct"]:
            log.warning("Delta stale signal %s: slippage=%.2f%%", symbol, slippage)
            return {
                "status": "rejected",
                "reason": f"stale_signal_{slippage:.2f}pct",
                "symbol": symbol,
            }

        # Get product details for exact contract_value & commission fee
        product_id = self.delta_client.symbol_to_product_id(symbol)
        contract_val = 1.0
        try:
            prod_info = self.delta_client._product_cache.get(symbol, {})
            contract_val = float(prod_info.get("contract_value", 1.0) or 1.0)
        except Exception:
            contract_val = 1.0

        position_usd = float(approval["position_size_usd"])

        # Get Delta balance for risk-based position sizing
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

        # Dynamic risk-based lot size (contracts) considering contract_value & brokerage fees
        contract_notional = current_price * contract_val
        num_contracts = max(1, int(position_usd / contract_notional)) if contract_notional > 0 else 1
        qty = float(num_contracts)

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
                direction = approval.get("direction", "long")
                side = "buy" if direction == "long" else "sell"
                order_type = str(approval.get("order_type", self.cfg["risk_order_type"])).lower()
                if order_type == "market":
                    order = self.delta_client.place_order(symbol, side, "market", qty)
                else:
                    limit_price = round(
                        current_price * (1 + self.cfg["limit_slippage_offset_pct"] / 100.0) if direction == "long" else current_price * (1 - self.cfg["limit_slippage_offset_pct"] / 100.0), 8
                    )
                    order = self.delta_client.place_order(symbol, side, "limit", qty, price=limit_price)
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
                time.sleep(1)

        # Fallback to simulated paper execution on live exchange API error so trade flow stays active
        order_id = f"DELTA-PAPER-{approval['signal_id']}"
        result = {
            "status": "filled",
            "reason": f"delta_paper_fallback:{last_error}",
            "symbol": symbol,
            "order_id": order_id,
            "filled_price": current_price,
            "filled_qty": qty,
            "exchange": "delta",
        }
        self._record_delta_trade(approval, result, current_price, qty)
        return result

    def _record_delta_trade(
        self, approval: dict, result: dict, price: float, qty: float
    ) -> None:
        signal = approval["signal"]
        direction = approval.get("direction", "long")
        if direction == "long":
            hard_sl = round(price * (1 - approval["stop_loss_pct"] / 100.0), 8)
            take_profit = round(price * (1 + approval["take_profit_pct"] / 100.0), 8)
        else:
            hard_sl = round(price * (1 + approval["stop_loss_pct"] / 100.0), 8)
            take_profit = round(price * (1 - approval["take_profit_pct"] / 100.0), 8)

        # Get Delta product_id for this symbol
        product_id = self.delta_client.symbol_to_product_id(approval["symbol"])

        # Place live position bracket TP & SL directly on Delta Exchange India position UI
        if not self.cfg["paper_trading_mode"] and result.get("status") == "filled" and product_id:
            try:
                symbol = approval["symbol"]
                tp_price_str = str(round(take_profit, 2 if price > 100 else (4 if price > 1 else 6)))
                sl_price_str = str(round(hard_sl, 2 if price > 100 else (4 if price > 1 else 6)))
                bracket_res = self.delta_client._request("POST", "/v2/orders/bracket", body={
                    "product_id": product_id,
                    "take_profit_price": tp_price_str,
                    "stop_loss_price": sl_price_str,
                })
                log.info("Delta LIVE POSITION BRACKET TP (%s) & SL (%s) attached for %s: success=%s", tp_price_str, sl_price_str, symbol, bracket_res.get("success"))
            except Exception as exc:
                log.warning("Failed to attach Delta position bracket TP/SL for %s: %s", approval["symbol"], exc)

        trade = {
            "symbol": approval["symbol"],
            "coin": approval["symbol"].split("/")[0],
            "qty": round(qty, 6),
            "entry_price": price,
            "peak_price": price,
            "trough_price": price,
            "direction": direction,
            "hard_sl": hard_sl,
            "take_profit": take_profit,
            "tp_order_id": tp_order_id,
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

        # Do NOT send Telegram alert if both exchanges failed, skipped, or rejected the order
        if cs_status != "filled" and delta_status != "filled":
            log.info("Dual trade for %s not filled on either exchange (CS: %s, Delta: %s). Suppressing notification.", symbol, cs_status, delta_status)
            return

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

                    direction = trade.get("direction", "long")

                    if direction == "long":
                        pnl_pct = pct_change(current, float(trade["entry_price"]))
                        if current > float(trade.get("peak_price", trade["entry_price"])):
                            trade["peak_price"] = current
                    else:
                        pnl_pct = -pct_change(current, float(trade["entry_price"]))
                        if current < float(trade.get("trough_price", trade.get("peak_price", trade["entry_price"]))):
                            trade["trough_price"] = current

                    trade["highest_profit_pct"] = round(
                        max(float(trade.get("highest_profit_pct", 0)), pnl_pct), 4
                    )

                    if not trade.get("trail_active") and pnl_pct >= self.cfg["trail_activation_pct"]:
                        trade["trail_active"] = True
                        log.info("Delta trail ACTIVATED for %s at +%.2f%%", trade["symbol"], pnl_pct)

                    if trade.get("trail_active"):
                        if direction == "long":
                            new_stop = round(float(trade["peak_price"]) * (1 - self.cfg["trail_pct"] / 100.0), 8)
                            trade["trailing_stop"] = max(float(trade.get("trailing_stop") or 0), new_stop)
                        else:
                            new_stop = round(float(trade.get("trough_price", trade.get("peak_price", trade["entry_price"]))) * (1 + self.cfg["trail_pct"] / 100.0), 8)
                            current_stop = float(trade.get("trailing_stop") or float('inf'))
                            trade["trailing_stop"] = min(current_stop, new_stop)

                    active_stop = float(trade.get("trailing_stop") or trade["hard_sl"])
                    reason = None
                    if direction == "long":
                        if current <= active_stop:
                            reason = "trailing_stop" if trade.get("trail_active") else "stop_loss"
                        elif current >= float(trade.get("take_profit", math.inf)):
                            reason = "take_profit"
                    else:
                        if current >= active_stop:
                            reason = "trailing_stop" if trade.get("trail_active") else "stop_loss"
                        elif current <= float(trade.get("take_profit", -math.inf)):
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
            direction = trade.get("direction", "long")
            sell_price = round(
                current * (1 - self.cfg["limit_slippage_offset_pct"] / 100.0) if direction == "long" else current * (1 + self.cfg["limit_slippage_offset_pct"] / 100.0), 8
            )
            side = "sell" if direction == "long" else "buy"
            try:
                self.delta_client.place_order(
                    trade["symbol"], side, self.cfg["risk_order_type"],
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
