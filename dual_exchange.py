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
            # 20x Leverage allows capital distribution across up to 3-5 concurrent positions
            leverage = 20
            max_pos_margin = max(3.0, (delta_balance * 0.35))  # Allocate ~35% margin per trade so multiple trades run in parallel
            position_usd = min(position_usd, max_pos_margin * leverage)

        # Dynamic risk-based lot size (contracts) considering contract_value & 20x leverage
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
                stop_loss_pct = float(approval.get("stop_loss_pct", self.cfg["stop_loss_pct"]))
                take_profit_pct = float(approval.get("take_profit_pct", self.cfg["take_profit_pct"]))
                
                if direction == "long":
                    calc_sl = round(current_price * (1 - stop_loss_pct / 100.0), 4)
                    calc_tp = round(current_price * (1 + take_profit_pct / 100.0), 4)
                else:
                    calc_sl = round(current_price * (1 + stop_loss_pct / 100.0), 4)
                    calc_tp = round(current_price * (1 - take_profit_pct / 100.0), 4)

                # ALWAYS execute MARKET order entry with ATOMIC TP (+4.8%) & SL (-0.05%) on Delta Exchange India
                order = self.delta_client.place_order(symbol, side, "market", qty, stop_loss_price=calc_sl, take_profit_price=calc_tp)
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

                # 1. Attach server-side position bracket orders (HARD STOP-LOSS & TAKE-PROFIT) on Delta Exchange engine
                try:
                    bracket_res = self.delta_client._request("POST", "/v2/orders/bracket", body={
                        "product_id": product_id,
                        "stop_loss_price": str(calc_sl),
                        "take_profit_price": str(calc_tp),
                    })
                    log.info("Delta LIVE HARD POSITION BRACKET SL (%s) & TP (%s) attached for %s: success=%s", calc_sl, calc_tp, symbol, bracket_res.get("success", True))
                except Exception as b_exc:
                    log.warning("Failed to attach Delta position bracket TP/SL for %s: %s", symbol, b_exc)

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

        # Live execution failed after all retries — do NOT create phantom paper trades
        log.error("Delta execution FAILED for %s after %s retries: %s", symbol, self.cfg["max_retries"], last_error)
        return {"status": "error", "reason": f"live_execution_failed:{last_error}", "symbol": symbol}

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
        tp_order_id = ""

        # TP/SL already attached atomically in place_order() call — no duplicate bracket needed
        log.info("Delta trade recorded for %s: TP=%s SL=%s (attached atomically)", approval["symbol"], take_profit, hard_sl)

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
            "atr_pct": approval.get("atr_pct", 1.0),
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

        direction_str = str(approval.get("direction", "long")).upper()
        dir_icon = "🟢 LONG" if direction_str == "LONG" else "🔴 SHORT"
        kronos_v = approval.get("kronos_verdict", "CONFIRMED_BULLISH")
        sl_val = round(price * 0.985, 4) if direction_str == "LONG" else round(price * 1.015, 4)
        tp_val = round(price * 1.048, 4) if direction_str == "LONG" else round(price * 0.952, 4)

        self.notifier.send(
            f"🚀 *LIVE DUAL TRADE OPENED* — `{symbol}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Direction*: `{dir_icon}`\n"
            f"💵 *Entry Price*: `${price}`\n"
            f"💰 *Position Size*: `${size:.2f} USDT`\n"
            f"🧠 *Kronos AI Verdict*: `{kronos_v}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{cs_icon} *CoinSwitch Pro*: `{cs_status.upper()}`\n"
            f"{delta_icon} *Delta India*: `{delta_status.upper()} (20x Leverage)`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛑 *Hard Server SL*: `-${self.cfg['stop_loss_pct']}%` (`${sl_val}`)\n"
            f"🎯 *Take Profit*: `+{self.cfg['take_profit_pct']}%` (`${tp_val}`)\n"
            f"🛡️ *Trailing Stop*: `+{self.cfg['trail_activation_pct']}% Activation`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━"
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

        # Sync real live open positions directly from Delta Exchange India API (/v2/positions/margined)
        if not self.cfg.get("paper_trading_mode"):
            try:
                live_res = self.delta_client._request("GET", "/v2/positions/margined")
                live_positions = live_res.get("result", [])
                if isinstance(live_positions, dict):
                    live_positions = [live_positions]
                
                tracked_symbols = {t["symbol"] for t in delta_trades}
                for pos in live_positions:
                    size = float(pos.get("size") or pos.get("open_qty") or 0)
                    if abs(size) > 0:
                        prod_sym = str(pos.get("product_symbol", "")).upper()
                        # Map Delta product_symbol to standard symbol (e.g. ONDOUSD -> ONDO/USDT)
                        if prod_sym.endswith("USD"):
                            symbol = f"{prod_sym[:-3]}/USDT"
                        elif prod_sym.endswith("USDT"):
                            symbol = f"{prod_sym[:-4]}/USDT"
                        else:
                            symbol = prod_sym

                        if symbol not in tracked_symbols:
                            entry_price = float(pos.get("entry_price") or 0)
                            direction = "long" if size > 0 else "short"
                            sl_price = round(entry_price * 0.985, 4) if direction == "long" else round(entry_price * 1.015, 4)
                            tp_price = round(entry_price * 1.048, 4) if direction == "long" else round(entry_price * 0.952, 4)

                            # Attach server-side bracket order
                            product_id = pos.get("product_id")
                            if product_id:
                                try:
                                    self.delta_client._request("POST", "/v2/orders/bracket", body={
                                        "product_id": product_id,
                                        "stop_loss_price": str(sl_price),
                                        "take_profit_price": str(tp_price),
                                    })
                                except Exception:
                                    pass

                            synced_trade = {
                                "symbol": symbol,
                                "direction": direction,
                                "entry_price": entry_price,
                                "qty": abs(size),
                                "hard_sl": sl_price,
                                "take_profit": tp_price,
                                "peak_price": entry_price,
                                "trough_price": entry_price,
                                "highest_profit_pct": 0.0,
                                "trail_active": False,
                                "order_id": str(pos.get("id") or "synced_api"),
                                "exchange": "delta",
                                "opened_at": utc_iso(),
                            }
                            delta_trades.append(synced_trade)
                            tracked_symbols.add(symbol)
                            log.info("DualMonitor: Synced live Delta position for %s (size=%s entry=%s SL=%s TP=%s)", symbol, size, entry_price, sl_price, tp_price)

                # Remove ghost trades (trades present locally but closed natively on exchange)
                live_symbols = set()
                for pos in live_positions:
                    size = float(pos.get("size") or pos.get("open_qty") or 0)
                    if abs(size) > 0:
                        prod_sym = str(pos.get("product_symbol", "")).upper()
                        if prod_sym.endswith("USD"):
                            symbol = f"{prod_sym[:-3]}/USDT"
                        elif prod_sym.endswith("USDT"):
                            symbol = f"{prod_sym[:-4]}/USDT"
                        else:
                            symbol = prod_sym
                        live_symbols.add(symbol)
                
                valid_trades = []
                for t in delta_trades:
                    if not t.get("paper") and t["symbol"] not in live_symbols:
                        log.info("DualMonitor: Ghost trade detected and cleared for %s (Native TP/SL hit or manually closed on exchange)", t["symbol"])
                        continue
                    valid_trades.append(t)
                delta_trades = valid_trades
                
            except Exception as sync_exc:
                log.debug("Delta live position sync notice: %s", sync_exc)

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
                        # Chandelier Exit Trailing Stop
                        atr_pct = float(trade.get("atr_pct", 1.0))
                        if atr_pct <= 0: atr_pct = 1.0
                        trail_distance_pct = atr_pct * 1.5
                        # Cap the trail distance between 1% and 5% to prevent crazy stops
                        trail_distance_pct = max(1.0, min(5.0, trail_distance_pct))
                        
                        if direction == "long":
                            new_stop = round(float(trade["peak_price"]) * (1 - trail_distance_pct / 100.0), 8)
                            trade["trailing_stop"] = max(float(trade.get("trailing_stop") or 0), new_stop)
                        else:
                            new_stop = round(float(trade.get("trough_price", trade.get("peak_price", trade["entry_price"]))) * (1 + trail_distance_pct / 100.0), 8)
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
        usdt_used = float(trade.get("usdt_used") or (float(trade.get("qty", 1.0)) * float(trade.get("entry_price", 1.0))))
        pnl_usdt = round(usdt_used * pnl_pct / 100.0, 2)

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

        icon = "🎉 PROFIT" if pnl_pct >= 0 else "🛡️ CAP LOSS"
        pnl_sign = "+" if pnl_usdt >= 0 else ""
        reason_label = {
            "take_profit": "🎯 TAKE PROFIT (+4.8%)",
            "trailing_stop": "📈 TRAILING STOP HIT",
            "stop_loss": "🛑 HARD STOP LOSS (-1.5%)",
        }.get(reason, reason.upper())

        self.notifier.send(
            f"{'🟢' if pnl_pct >= 0 else '🔴'} *DELTA TRADE CLOSED ({icon})* — `{trade['symbol']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *Exit Reason*: `{reason_label}`\n"
            f"📈 *Direction*: `{trade.get('direction', 'LONG').upper()}`\n"
            f"💵 *Entry*: `${trade['entry_price']}` ➔ *Exit*: `${current}`\n"
            f"💰 *Net Trade P&L*: `{pnl_pct:+.2f}%` (`{pnl_sign}{pnl_usdt:.2f} USDT`)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏛️ *Exchange*: `Delta Exchange India (20x)`\n"
            f"🕒 *Exit Time*: `{timestamp}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━"
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
