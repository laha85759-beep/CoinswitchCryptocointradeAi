"""
Multi-agent pump/dump pipeline for CoinSwitch.
Strategy: Momentum scalping with adaptive trailing stop for small capital.

Key improvements over v1:
  - Signal requires 3/4 conditions (not 4/4) — fires on real moves
  - Confidence formula tuned to realistic 0.40–0.75 range
  - Tighter slippage check tolerates GitHub Actions 15-min scheduling lag
  - Detailed Telegram notifications with P&L context
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from coinswitch_client import CoinSwitchClient
from notifier import TelegramNotifier
from scanner import MarketScanner, SignalEngine, ConsolidationBreakoutEngine

log = logging.getLogger(__name__)


OPEN_TRADES_FILE = Path("open_trades.json")
AUDIT_LOG_FILE = Path("agent_audit.jsonl")
PROCESSED_SIGNALS_FILE = Path("processed_signals.json")
DAILY_PNL_FILE = Path("daily_pnl.json")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso() -> str:
    return utc_now().isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        log.warning("Could not read %s: %s", path, exc)
        return default


def save_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)


class AuditLogger:
    def __init__(self, path: Path = AUDIT_LOG_FILE):
        self.path = path

    def write(self, agent: str, payload: dict) -> None:
        row = {"timestamp": utc_iso(), "agent": agent, "payload": payload}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")


@dataclass
class CircuitBreaker:
    cfg: dict
    audit: AuditLogger
    path: Path = Path("circuit_breaker.json")

    def load(self) -> dict:
        return load_json(self.path, {"consecutive_errors": 0, "execution_halted": False})

    def record_success(self) -> None:
        save_json(self.path, {"consecutive_errors": 0, "execution_halted": False})

    def record_error(self, reason: str) -> dict:
        state = self.load()
        state["consecutive_errors"] = int(state.get("consecutive_errors", 0)) + 1
        state["last_error"] = reason
        state["last_error_at"] = utc_iso()
        if state["consecutive_errors"] >= self.cfg["circuit_breaker_error_limit"]:
            state["execution_halted"] = True
        save_json(self.path, state)
        self.audit.write("CircuitBreaker", state)
        return state

    def is_halted(self) -> bool:
        return bool(self.load().get("execution_halted"))


class DataCollectorAgent:
    def __init__(self, cfg: dict, client: CoinSwitchClient, audit: AuditLogger):
        self.cfg = cfg
        self.client = client
        self.audit = audit
        self.scanner = MarketScanner(cfg, client)
        self.consol_engine = ConsolidationBreakoutEngine(cfg)

    def symbols(self) -> list[str]:
        watchlist = [s.strip().upper() for s in self.cfg.get("watchlist", []) if s.strip()]
        if watchlist:
            return [s if "/" in s else f"{s}/{self.cfg['quote_currency']}" for s in watchlist]
        return self.scanner._top_symbols()

    def collect(self) -> list[dict]:
        out = []
        symbols = self.symbols()
        log.info("Data Collector: collecting %s symbols", len(symbols))
        if not symbols:
            log.warning("Data Collector: 0 symbols returned from scanner. Check CoinSwitch API / c2c2 tickers.")
            self.audit.write("DataCollector", {"count": 0, "items": [], "error": "zero_symbols_from_scanner"})
            return out
        try:
            tickers = self.client.get_all_tickers(self.cfg.get("exchange", "c2c2"))
        except Exception as exc:
            log.warning("Ticker snapshot failed: %s", exc)
            tickers = {}
        for symbol in symbols:
            try:
                df = self.scanner._ohlcv(symbol)
                if df is None or len(df) < 50:
                    out.append({"symbol": symbol, "error": "insufficient_ohlcv", "timestamp": utc_iso()})
                    continue

                close = df["close"].astype(float)
                high = df["high"].astype(float)
                low = df["low"].astype(float)
                volume = df["volume"].astype(float)
                price = float(close.iloc[-1])

                change_5m = pct_change(close.iloc[-1], close.iloc[-2])
                change_1h = pct_change(close.iloc[-1], close.iloc[-13]) if len(close) >= 13 else 0.0
                change_4h = pct_change(close.iloc[-1], close.iloc[-49]) if len(close) >= 49 else 0.0
                change_24h = pct_change(close.iloc[-1], close.iloc[-1 - min(len(close) - 1, 288)])

                # Volume z-score over 84-candle window (7h of 5m candles)
                vol_window = volume.tail(min(len(volume), 84))
                vol_mean = float(vol_window.mean() or 0)
                vol_std = float(vol_window.std() or 0)
                volume_zscore = 0.0 if vol_std <= 0 else float((volume.iloc[-1] - vol_mean) / vol_std)

                rolling_avg = float(volume.tail(20).mean() or 0)
                volume_ratio = 1.0 if rolling_avg <= 0 else float(volume.iloc[-1] / rolling_avg)

                # ATR-based volatility (14-period)
                tr = pd.concat([
                    high - low,
                    (high - close.shift(1)).abs(),
                    (low - close.shift(1)).abs()
                ], axis=1).max(axis=1)
                atr = float(tr.ewm(span=14, adjust=False).mean().iloc[-1])
                atr_pct = (atr / price * 100) if price > 0 else 0.0

                orderbook_imbalance = synthetic_imbalance(change_5m, volume_ratio)
                trade_freq_5m = int(max(1, round(volume_ratio * 100)))

                ticker = tickers.get(symbol, {})
                # c2c2 has empty quoteVolume — compute from baseVolume * price
                quote_volume = safe_float(ticker.get("quoteVolume"))
                if quote_volume <= 0:
                    base_vol = safe_float(ticker.get("baseVolume"))
                    quote_volume = base_vol * price if base_vol > 0 else 0.0
                if quote_volume <= 0:
                    quote_volume = float(volume.tail(min(len(volume), 288)).sum()) * price

                item = {
                    "symbol": symbol,
                    "price": price,
                    "change_5m": round(change_5m, 4),
                    "change_1h": round(change_1h, 4),
                    "change_4h": round(change_4h, 4),
                    "change_24h": round(change_24h, 4),
                    "volume_24h": round(quote_volume, 4),
                    "volume_zscore": round(volume_zscore, 4),
                    "volume_ratio": round(volume_ratio, 4),
                    "atr_pct": round(atr_pct, 4),
                    "orderbook_imbalance": round(orderbook_imbalance, 4),
                    "trade_freq_5m": trade_freq_5m,
                    "trade_freq_ratio": round(volume_ratio, 4),
                    "timestamp": utc_iso(),
                    "data_notes": ["orderbook_imbalance_and_trade_frequency_are_ohlcv_proxies"],
                }

                # ── Consolidation + Breakout detection (1h candles) ──────────
                try:
                    df_1h = self.scanner._ohlcv_1h(symbol, 48)
                    if df_1h is not None and len(df_1h) >= 24:
                        consol = self.consol_engine.detect(df_1h, df)
                        if consol is not None:
                            item["consolidation_breakout"] = consol
                            log.info(
                                "Consolidation breakout detected: %s | %s | strength=%s",
                                symbol, consol["type"], consol.get("strength", 0),
                            )
                except Exception as exc:
                    log.debug("Consolidation check failed for %s: %s", symbol, exc)

                out.append(item)
            except Exception as exc:
                out.append({"symbol": symbol, "error": str(exc), "timestamp": utc_iso()})

        self.audit.write("DataCollector", {"count": len(out), "items": out})
        return out


class SignalDetectorAgent:
    """
    Improved signal detector.

    Pump signal fires when 3 out of 4 conditions are met (not 4/4).
    This makes the detector realistic for 5m momentum moves while
    still requiring multiple confirmations to avoid false signals.

    Conditions:
      1. up_move   — significant price move up on 5m or 1h candle
      2. high_vol  — volume z-score above threshold (genuine spike)
      3. imbalance — synthetic buy-side pressure > threshold
      4. freq_spike — current candle volume ≥ 2x rolling average

    Confidence is scored 0.0–1.0 using move strength, volume strength,
    4h trend alignment, and how many conditions were met.
    """

    def __init__(self, cfg: dict, audit: AuditLogger):
        self.cfg = cfg
        self.audit = audit
        self.legacy_engine = SignalEngine(cfg["weights"])

    def classify(self, items: list[dict]) -> list[dict]:
        signals = []
        for item in items:
            symbol = item.get("symbol", "")
            if item.get("error"):
                signals.append(self._signal(symbol, "insufficient_data", 0.0, "incomplete_market_data", item))
                continue

            # ── Consolidation / trendline breakout (new strategy) ───────────
            consol = item.get("consolidation_breakout")
            if consol:
                strength  = consol.get("strength", 0)
                confidence = min(1.0, 0.55 + strength / 300)
                min_score  = self.cfg.get("consolidation_breakout_score_min", 0.55)
                if confidence >= min_score:
                    signals.append(self._signal(
                        symbol, "pump", confidence,
                        consol.get("type", "consolidation_breakout"), item,
                    ))
                    continue

            # ── Existing momentum signal detection ───────────────────────────
            up_move = (
                item["change_5m"] > self.cfg["pump_change_5m_pct"]
                or item["change_1h"] > self.cfg["pump_change_1h_pct"]
            )
            down_move = (
                item["change_5m"] < -self.cfg["dump_change_5m_pct"]
                or item["change_1h"] < -self.cfg["dump_change_1h_pct"]
            )
            high_volume = item["volume_zscore"] > self.cfg["volume_zscore_min"]
            buy_dominance = item["orderbook_imbalance"] > self.cfg["buy_imbalance_min"]
            sell_dominance = item["orderbook_imbalance"] < (1.0 - self.cfg["sell_imbalance_min"])
            trade_spike = item.get("trade_freq_ratio", 0) >= self.cfg["trade_frequency_spike_ratio"]

            # 4h trend filter: prefer entries aligned with medium-term trend
            trend_up = item.get("change_4h", 0) > 0
            trend_down = item.get("change_4h", 0) < 0

            pump_conditions = [up_move, high_volume, buy_dominance, trade_spike]
            dump_conditions = [down_move, high_volume, sell_dominance, trade_spike]
            pump_count = sum(bool(x) for x in pump_conditions)
            dump_count = sum(bool(x) for x in dump_conditions)

            signal = "normal"
            # Relaxed pump/dump detection:
            #   3/4 conditions (any trend) → pump/dump
            #   2/4 conditions + aligned 4h trend → pump/dump
            #   2/4 conditions (no trend) → watch
            if pump_count >= 3:
                signal = "pump"
            elif pump_count >= 2 and trend_up:
                signal = "pump"
            elif dump_count >= 3:
                signal = "dump"
            elif dump_count >= 2 and trend_down:
                signal = "dump"
            elif max(pump_count, dump_count) >= self.cfg["watch_condition_count"]:
                signal = "watch"

            confidence = confidence_score(item, pump_count if signal != "dump" else dump_count, trend_up if signal != "dump" else trend_down)
            cause = suspected_cause(item, high_volume, trade_spike)
            signals.append(self._signal(symbol, signal, confidence, cause, item))

        self.audit.write("SignalDetector", {"count": len(signals), "signals": signals})
        return signals

    def _signal(self, symbol: str, signal: str, confidence: float, cause: str, supporting: dict) -> dict:
        basis = f"{symbol}:{signal}:{supporting.get('timestamp', utc_iso())[:16]}"
        signal_id = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:20]
        return {
            "signal_id": signal_id,
            "symbol": symbol,
            "signal": signal,
            "confidence": round(float(confidence), 4),
            "suspected_cause": cause,
            "supporting_data": supporting,
            "timestamp": utc_iso(),
        }


class RiskManagerAgent:
    def __init__(self, cfg: dict, client: CoinSwitchClient, audit: AuditLogger):
        self.cfg = cfg
        self.client = client
        self.audit = audit

    def evaluate(self, signals: list[dict], execution_halted: bool = False) -> list[dict]:
        approvals = []
        for signal in signals:
            approvals.append(self._evaluate_one(signal, execution_halted))
        self.audit.write("RiskManager", {"count": len(approvals), "approvals": approvals})
        return approvals

    def _evaluate_one(self, signal: dict, execution_halted: bool) -> dict:
        symbol = signal["symbol"]
        if execution_halted:
            return risk_reject(signal, "circuit_breaker_halted_execution")
        # Accept pump signals and high-confidence watch signals
        if signal["signal"] == "pump":
            pass  # continue to evaluation
        elif signal["signal"] == "watch" and signal["confidence"] >= 0.50:
            pass  # high-confidence watch = tradeable
        else:
            return risk_reject(signal, f"signal_is_{signal['signal']}")
        if signal["confidence"] < self.cfg["min_confidence"]:
            return risk_reject(signal, "confidence_below_minimum")

        supporting = signal.get("supporting_data", {})
        vol_24h = float(supporting.get("volume_24h", 0) or 0)
        if vol_24h < self.cfg["min_liquidity_usd"]:
            return risk_reject(signal, f"liquidity_{vol_24h:.0f}_below_min")

        # Skip high-volatility pairs (ATR > 5% means too risky for small capital)
        atr_pct = float(supporting.get("atr_pct", 0) or 0)
        if atr_pct > 5.0:
            return risk_reject(signal, f"atr_{atr_pct:.2f}pct_too_volatile")

        trades = load_json(OPEN_TRADES_FILE, [])
        if any(t.get("symbol") == symbol for t in trades):
            return risk_reject(signal, "symbol_already_open")

        processed = load_json(PROCESSED_SIGNALS_FILE, [])
        if signal["signal_id"] in processed:
            return risk_reject(signal, "duplicate_signal_id")

        if trades_this_hour(trades) >= self.cfg["max_trades_per_hour"]:
            return risk_reject(signal, "max_trades_per_hour_reached")

        max_open_trades = int(self.cfg.get("max_open_trades", 1))
        if len([t for t in trades if t.get("paper", False) == self.cfg["paper_trading_mode"]]) >= max_open_trades:
            return risk_reject(signal, "max_open_trades_reached")

        portfolio_usdt = self._portfolio_usdt()
        if portfolio_usdt <= 0:
            return risk_reject(signal, "zero_portfolio_balance")

        total_exposure = sum(float(t.get("usdt_used", 0) or 0) for t in trades)
        max_total = portfolio_usdt * self.cfg["max_total_exposure_pct"] / 100.0
        if total_exposure >= max_total:
            return risk_reject(signal, "max_total_exposure_reached")

        pnl = load_json(DAILY_PNL_FILE, {})
        today = utc_now().date().isoformat()
        day_loss = float(pnl.get(today, {}).get("realized_pnl_usdt", 0) or 0)
        if day_loss < -(portfolio_usdt * self.cfg["daily_max_drawdown_pct"] / 100.0):
            return risk_reject(signal, "daily_drawdown_limit_reached")

        max_position = portfolio_usdt * self.cfg["max_position_pct"] / 100.0
        remaining_exposure = max(0.0, max_total - total_exposure)
        position_size = min(max_position, remaining_exposure)
        if position_size < self.cfg["min_order_usdt"]:
            return risk_reject(signal, f"position_{position_size:.2f}_below_min_order")

        return {
            "signal_id": signal["signal_id"],
            "symbol": symbol,
            "approved": True,
            "reason": "approved",
            "position_size_usd": round(position_size, 2),
            "stop_loss_pct": self.cfg["stop_loss_pct"],
            "take_profit_pct": self.cfg["take_profit_pct"],
            "order_type": self.cfg["risk_order_type"],
            "direction": "long",
            "approval_token": hashlib.sha256(
                f"{signal['signal_id']}:{utc_iso()}".encode("utf-8")
            ).hexdigest()[:24],
            "signal": signal,
            "timestamp": utc_iso(),
        }

    def _portfolio_usdt(self) -> float:
        if self.cfg["paper_trading_mode"]:
            return float(self.cfg["paper_portfolio_usdt"])
        try:
            return max(float(self.client.get_usdt_balance()), 0.0)
        except Exception as exc:
            log.warning("USDT balance failed: %s", exc)
            return 0.0


class ExecutionAgent:
    def __init__(self, cfg: dict, client: CoinSwitchClient, audit: AuditLogger):
        self.cfg = cfg
        self.client = client
        self.audit = audit

    def execute(self, approvals: list[dict]) -> list[dict]:
        results = []
        for approval in approvals:
            if approval.get("approved") is not True:
                continue
            results.append(self._execute_one(approval))
        self.audit.write("ExecutionAgent", {"count": len(results), "results": results})
        return results

    def _execute_one(self, approval: dict) -> dict:
        signal = approval["signal"]
        symbol = approval["symbol"]
        price_at_signal = float(signal["supporting_data"]["price"])

        try:
            current_price = float(self.client.get_ticker_price(symbol))
        except Exception as exc:
            return execution_result(symbol, "error", f"price_fetch_failed:{exc}", signal, approval)

        if current_price <= 0:
            return execution_result(symbol, "error", "zero_current_price", signal, approval)

        slippage = abs(pct_change(current_price, price_at_signal))
        if slippage > self.cfg["slippage_tolerance_pct"]:
            log.warning("Stale signal %s: slippage=%.2f%%", symbol, slippage)
            return execution_result(symbol, "rejected", f"stale_signal_slippage_{slippage:.2f}pct", signal, approval)

        qty = round(float(approval["position_size_usd"]) / current_price, 6)
        if qty <= 0:
            return execution_result(symbol, "rejected", "zero_quantity", signal, approval)

        if self.cfg["paper_trading_mode"]:
            order_id = f"PAPER-{approval['signal_id']}"
            result = execution_result(
                symbol, "filled", "paper_trade_filled", signal, approval,
                order_id=order_id, filled_price=current_price, filled_qty=qty,
            )
            self._record_open_trade(approval, result)
            self._notify_entry(approval, result, current_price)
            return result

        last_error = None
        for attempt in range(1, self.cfg["max_retries"] + 1):
            try:
                limit_price = round(current_price * (1 + self.cfg["limit_slippage_offset_pct"] / 100.0), 8)
                order = self.client.place_order(symbol, "buy", approval["order_type"], qty, price=limit_price)
                order_id = order.get("order_id") or order.get("id")
                if not order_id:
                    return execution_result(symbol, "error", "missing_order_id", signal, approval)

                filled, filled_qty = False, 0.0
                for _ in range(5):
                    status = self.client.get_order(order_id)
                    filled, filled_qty = self.client.order_fill_status(status)
                    if filled:
                        break
                    time.sleep(2)

                if not filled:
                    return execution_result(symbol, "partial", "order_pending", signal, approval, order_id=order_id)

                result = execution_result(
                    symbol, "filled", "live_trade_filled", signal, approval,
                    order_id=order_id,
                    filled_price=current_price,
                    filled_qty=round(filled_qty or qty, 6),
                )
                self._record_open_trade(approval, result)
                self._notify_entry(approval, result, current_price)
                return result
            except Exception as exc:
                last_error = str(exc)
                log.warning("Execution attempt %s failed for %s: %s", attempt, symbol, exc)
                time.sleep(2)

        return execution_result(symbol, "error", last_error or "execution_failed", signal, approval)

    def _notify_entry(self, approval: dict, result: dict, price: float) -> None:
        """Send a rich Telegram entry notification."""
        from notifier import TelegramNotifier
        # notifier not injected into ExecutionAgent — use audit log only
        # (MonitorReporter sends trade-closed notifications)
        log.info(
            "TRADE OPENED %s | qty=%.6f | price=%.8f | size=$%.2f | sl=%.1f%% | tp=%.1f%%",
            approval["symbol"],
            result["filled_qty"],
            price,
            approval["position_size_usd"],
            approval["stop_loss_pct"],
            approval["take_profit_pct"],
        )

    def _record_open_trade(self, approval: dict, result: dict) -> None:
        signal = approval["signal"]
        price = float(result["filled_price"])
        hard_sl = round(price * (1 - approval["stop_loss_pct"] / 100.0), 8)
        take_profit = round(price * (1 + approval["take_profit_pct"] / 100.0), 8)
        trade = {
            "symbol": approval["symbol"],
            "coin": approval["symbol"].split("/")[0],
            "qty": result["filled_qty"],
            "entry_price": price,
            "peak_price": price,
            "hard_sl": hard_sl,
            "take_profit": take_profit,
            "trail_active": False,
            "trailing_stop": None,
            "buy_id": result["order_id"],
            "opened_at": utc_iso(),
            "usdt_used": approval["position_size_usd"],
            "score": round(signal["confidence"] * 100, 2),
            "highest_profit_pct": 0.0,
            "paper": self.cfg["paper_trading_mode"],
            "signal_id": approval["signal_id"],
            "approval_token": approval["approval_token"],
        }
        trades = load_json(OPEN_TRADES_FILE, [])
        trades.append(trade)
        save_json(OPEN_TRADES_FILE, trades)
        processed = load_json(PROCESSED_SIGNALS_FILE, [])
        processed.append(approval["signal_id"])
        save_json(PROCESSED_SIGNALS_FILE, sorted(set(processed))[-500:])


class MonitorReporterAgent:
    def __init__(self, cfg: dict, client: CoinSwitchClient, notifier: TelegramNotifier, audit: AuditLogger):
        self.cfg = cfg
        self.client = client
        self.notifier = notifier
        self.audit = audit

    def monitor(self) -> dict:
        trades = load_json(OPEN_TRADES_FILE, [])
        if not trades:
            report = {"open_positions": 0, "closed": [], "timestamp": utc_iso()}
            self.audit.write("MonitorReporter", report)
            log.info("Monitor: no open positions")
            return report

        remaining, closed = [], []
        for trade in trades:
            try:
                current = float(self.client.get_ticker_price(trade["symbol"]))
                if current <= 0:
                    remaining.append(trade)
                    continue

                pnl_pct = pct_change(current, float(trade["entry_price"]))
                trade["highest_profit_pct"] = round(
                    max(float(trade.get("highest_profit_pct", 0)), pnl_pct), 4
                )

                # Update peak price
                if current > float(trade.get("peak_price", trade["entry_price"])):
                    trade["peak_price"] = current

                # Activate trailing stop when profit threshold reached
                if not trade.get("trail_active") and pnl_pct >= self.cfg["trail_activation_pct"]:
                    trade["trail_active"] = True
                    log.info("Trail ACTIVATED for %s at +%.2f%%", trade["symbol"], pnl_pct)
                    self.notifier.send(
                        f"🎯 *TRAILING STOP ACTIVATED* `{trade['symbol']}`\n"
                        f"Profit: `+{pnl_pct:.2f}%` | Peak: `{trade['peak_price']}`\n"
                        f"Stop now trails `{self.cfg['trail_pct']}%` below peak"
                    )

                # Ratchet trailing stop upward
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
                    closed.append(self._close_trade(trade, current, pnl_pct, reason))
                else:
                    log.info(
                        "HOLD %s | price=%.8f | pnl=%+.2f%% | stop=%.8f | trail=%s",
                        trade["symbol"], current, pnl_pct, active_stop,
                        "ON" if trade.get("trail_active") else "OFF",
                    )
                    remaining.append(trade)

            except Exception as exc:
                log.warning("Monitor failed for %s: %s", trade.get("symbol"), exc)
                trade["last_monitor_error"] = str(exc)
                remaining.append(trade)

        save_json(OPEN_TRADES_FILE, remaining)
        report = {
            "open_positions": len(remaining),
            "closed": closed,
            "timestamp": utc_iso(),
            "paper_trading_mode": self.cfg["paper_trading_mode"],
        }
        self.audit.write("MonitorReporter", report)
        return report

    def _close_trade(self, trade: dict, current: float, pnl_pct: float, reason: str) -> dict:
        pnl_usdt = round(float(trade["usdt_used"]) * pnl_pct / 100.0, 2)

        if not trade.get("paper"):
            sell_price = round(current * (1 - self.cfg["limit_slippage_offset_pct"] / 100.0), 8)
            try:
                self.client.place_order(
                    trade["symbol"], "sell", self.cfg["risk_order_type"],
                    float(trade["qty"]), price=sell_price,
                )
            except Exception as exc:
                log.error("SELL failed for %s: %s", trade["symbol"], exc)

        today = utc_now().date().isoformat()
        pnl = load_json(DAILY_PNL_FILE, {})
        pnl.setdefault(today, {"realized_pnl_usdt": 0.0, "closed_trades": 0})
        pnl[today]["realized_pnl_usdt"] = round(float(pnl[today]["realized_pnl_usdt"]) + pnl_usdt, 2)
        pnl[today]["closed_trades"] = int(pnl[today]["closed_trades"]) + 1
        save_json(DAILY_PNL_FILE, pnl)

        icon = "✅" if pnl_pct >= 0 else "🔴"
        reason_label = {
            "take_profit": "🎯 TAKE PROFIT",
            "trailing_stop": "📈 TRAILING STOP",
            "stop_loss": "🛑 STOP LOSS",
        }.get(reason, reason.upper())

        self.notifier.send(
            f"{icon} *TRADE CLOSED* `{trade['symbol']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"Reason : `{reason_label}`\n"
            f"Entry  : `{trade['entry_price']}`\n"
            f"Exit   : `{current}`\n"
            f"Peak   : `{trade['peak_price']}`\n"
            f"P&L    : `{pnl_pct:+.2f}%`  (`{pnl_usdt:+.2f}` USDT)\n"
            f"Best   : `+{trade.get('highest_profit_pct', 0):.2f}%`\n"
            f"Mode   : `{'paper' if trade.get('paper') else 'LIVE'}`"
        )
        log.info(
            "CLOSED %s | reason=%s | pnl=%.2f%% | pnl_usdt=%.2f",
            trade["symbol"], reason, pnl_pct, pnl_usdt,
        )
        return {
            "symbol": trade["symbol"],
            "reason": reason,
            "entry": trade["entry_price"],
            "exit": current,
            "pnl_pct": round(pnl_pct, 4),
            "pnl_usdt": pnl_usdt,
            "paper": bool(trade.get("paper")),
        }


# ── Helper functions ──────────────────────────────────────────────────────────

def pct_change(new: float, old: float) -> float:
    old = float(old)
    if old == 0:
        return 0.0
    return (float(new) - old) / old * 100.0


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def synthetic_imbalance(change_5m: float, volume_ratio: float) -> float:
    """
    Synthetic order-book imbalance derived from OHLCV.
    Returns 0.0–1.0 where >0.5 = buy pressure, <0.5 = sell pressure.
    Calibrated so realistic buy signals sit around 0.55–0.70.
    """
    directional = max(-0.35, min(0.35, change_5m / 10.0))
    volume_boost = max(0.0, min(0.15, (volume_ratio - 1.0) / 15.0))
    return max(0.0, min(1.0, 0.5 + directional + (volume_boost if change_5m >= 0 else -volume_boost)))


def confidence_score(item: dict, matched_conditions: int, trend_aligned: bool = False) -> float:
    """
    Confidence score 0.0–1.0.

    Components:
      35% — move strength  (how big is the 5m/1h price move)
      30% — volume strength (how strong is the volume spike)
      25% — condition match (how many of 4 conditions fired)
      10% — trend alignment (4h candle in same direction)

    Tuned so:
      3/4 conditions + moderate volume → ~0.45–0.55
      4/4 conditions + strong volume   → ~0.65–0.80
    """
    move_strength = min(1.0, max(
        abs(float(item.get("change_5m", 0))) / 3.0,
        abs(float(item.get("change_1h", 0))) / 5.0,
    ))
    volume_strength = min(1.0, max(0.0, float(item.get("volume_zscore", 0)) / 3.0))
    condition_strength = matched_conditions / 4.0
    trend_bonus = 0.10 if trend_aligned else 0.0
    raw = (
        0.35 * move_strength
        + 0.30 * volume_strength
        + 0.25 * condition_strength
        + trend_bonus
    )
    return min(1.0, max(0.0, raw))


def suspected_cause(item: dict, high_volume: bool, trade_spike: bool) -> str:
    change_5m = abs(float(item.get("change_5m", 0)))
    if high_volume and trade_spike and change_5m > 2.0:
        return "coordinated_volume_spike"
    if high_volume and change_5m > 1.0:
        return "whale_accumulation"
    if trade_spike and change_5m > 1.0:
        return "momentum_breakout"
    if high_volume:
        return "volume_divergence"
    if trade_spike:
        return "social_hype"
    return "unknown"


def risk_reject(signal: dict, reason: str) -> dict:
    log.info("REJECT %s: %s", signal.get("symbol"), reason)
    return {
        "signal_id": signal.get("signal_id"),
        "symbol": signal.get("symbol"),
        "approved": False,
        "reason": reason,
        "position_size_usd": 0.0,
        "stop_loss_pct": 0.0,
        "take_profit_pct": 0.0,
        "order_type": "none",
        "direction": "none",
        "signal": signal,
        "timestamp": utc_iso(),
    }


def trades_this_hour(trades: list[dict]) -> int:
    now = utc_now()
    count = 0
    for trade in trades:
        opened = trade.get("opened_at")
        if not opened:
            continue
        try:
            dt = datetime.fromisoformat(opened)
            if (now - dt).total_seconds() <= 3600:
                count += 1
        except Exception:
            continue
    return count


def execution_result(
    symbol: str,
    status: str,
    reason: str,
    signal: dict,
    approval: dict,
    order_id: str | None = None,
    filled_price: float = 0.0,
    filled_qty: float = 0.0,
) -> dict:
    return {
        "symbol": symbol,
        "order_id": order_id or "",
        "status": status,
        "reason": reason,
        "filled_price": round(float(filled_price), 8),
        "filled_qty": round(float(filled_qty), 8),
        "stop_loss_order_id": "",
        "take_profit_order_id": "",
        "approval_token": approval.get("approval_token", ""),
        "signal_id": signal.get("signal_id", ""),
        "timestamp": utc_iso(),
    }
