"""
Trade Executor + Trailing Stop Monitor  (CoinSwitch Spot v2)
"""

import json, logging, os, time
from datetime import datetime, timezone

from coinswitch_client import CoinSwitchClient
from notifier import TelegramNotifier

log = logging.getLogger(__name__)
STATE_FILE = "open_trades.json"

SLIP_PCT = 0.5  # aggressive limit price offset to simulate market order


class TradeExecutor:
    def __init__(self, config: dict, client: CoinSwitchClient, notifier: TelegramNotifier):
        self.cfg      = config
        self.client   = client
        self.notifier = notifier

    def open_trade(self, signal: dict):
        symbol = signal["symbol"]
        coin   = symbol.split("/")[0]
        score  = signal["pump_score"]
        price  = signal["price"]

        log.info(f"  📈 BUY signal: {symbol} | score={score}")
        trades = self._load()

        if len(trades) >= self.cfg["max_open_trades"]:
            log.warning(f"  ⚠️  Max trades reached. Skip {symbol}.")
            return
        if any(t["symbol"] == symbol for t in trades):
            log.info(f"  ⏭️  Already holding {symbol}. Skip.")
            return

        try:
            usdt_free = self._usdt_balance()
        except Exception as e:
            log.error(f"  Balance fetch failed: {e}")
            return

        if usdt_free < 10:
            log.warning("  ⚠️  USDT < $10. Skip.")
            return

        usdt_to_use = usdt_free * (self.cfg["max_capital_pct"] / 100.0)
        qty         = round(usdt_to_use / price, 6)
        hard_sl     = round(price * (1 - self.cfg["hard_sl_pct"] / 100), 8)
        buy_price   = round(price * (1 + SLIP_PCT / 100), 8)

        try:
            order = self.client.place_order(symbol, "buy", "limit", qty, price=buy_price)
            buy_id = order.get("order_id") or order.get("id") or "N/A"
            log.info(f"  ✅ BUY placed: {buy_id}")

            if buy_id != "N/A":
                filled = False
                filled_qty = 0.0
                for _ in range(3):
                    try:
                        order_status = self.client.get_order(buy_id)
                        filled, filled_qty = self.client.order_fill_status(order_status)
                        if filled:
                            break
                    except Exception as exc:
                        log.debug(f"  Order status check failed for {buy_id}: {exc}")
                    time.sleep(2)

                if not filled:
                    log.warning(f"  ⏳ BUY order {buy_id} is still pending; skipping trade state.")
                    return

                qty = round(filled_qty or qty, 6)
            else:
                log.warning("  ⚠️  Order ID missing; skipping trade state until fill is confirmed.")
                return

            trade = {
                "symbol":             symbol,
                "coin":               coin,
                "qty":                qty,
                "entry_price":        price,
                "peak_price":         price,
                "hard_sl":            hard_sl,
                "trail_active":       False,
                "trailing_stop":      None,
                "buy_id":             buy_id,
                "opened_at":          datetime.now(timezone.utc).isoformat(),
                "usdt_used":          round(usdt_to_use, 2),
                "score":              score,
                "highest_profit_pct": 0.0,
            }
            trades.append(trade)
            self._save(trades)

            self.notifier.send(
                f"🚀 *BUY SIGNAL — TRADE OPENED*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 *Symbol*     : `{symbol}`\n"
                f"🎯 *Score*      : `{score}/100`\n"
                f"💵 *Entry*      : `{price}`\n"
                f"📦 *Qty*        : `{qty} {coin}`\n"
                f"💰 *Capital*    : `${usdt_to_use:.2f}` USDT\n"
                f"🛑 *Hard SL*    : `{hard_sl}` (-{self.cfg['hard_sl_pct']}%)\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📈 *Exit Strategy:*\n"
                f"  ▸ Trail activates at +{self.cfg['trail_activation_pct']}% profit\n"
                f"  ▸ Trails {self.cfg['trail_pct']}% below peak\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏰ `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}`"
            )
        except Exception as e:
            log.error(f"  ❌ Trade failed for {symbol}: {e}")

    def monitor(self):
        trades = self._load()
        if not trades:
            log.info("  📭 No open trades to monitor.")
            return

        remaining = []
        for t in trades:
            symbol     = t["symbol"]
            entry      = t["entry_price"]
            peak       = t["peak_price"]
            hard_sl    = t["hard_sl"]
            qty        = t["qty"]
            trail_on   = t["trail_active"]
            trail_stop = t["trailing_stop"]

            try:
                current    = self.client.get_ticker_price(symbol)
                profit_pct = (current - entry) / entry * 100

                log.info(
                    f"  👀 {symbol} | current={current} | P&L={profit_pct:+.2f}% | "
                    f"peak={peak} | trail={'ON' if trail_on else 'OFF'} | "
                    f"stop={trail_stop or hard_sl}"
                )

                if current > peak:
                    t["peak_price"] = current
                    peak = current

                if profit_pct > t["highest_profit_pct"]:
                    t["highest_profit_pct"] = round(profit_pct, 2)

                if not trail_on and profit_pct >= self.cfg["trail_activation_pct"]:
                    t["trail_active"]  = True
                    trail_on           = True
                    trail_stop         = round(peak * (1 - self.cfg["trail_pct"] / 100), 8)
                    t["trailing_stop"] = trail_stop
                    log.info(f"  🎯 Trail ACTIVATED for {symbol}: stop={trail_stop}")
                    self.notifier.send(
                        f"🎯 *TRAILING STOP ACTIVATED*\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"📊 *Symbol*     : `{symbol}`\n"
                        f"💰 *Profit*     : `+{profit_pct:.2f}%` ✅\n"
                        f"📈 *Peak*       : `{peak}`\n"
                        f"🔒 *Trail Stop* : `{trail_stop}`\n"
                        f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"↗️ Stop rises as price rises — locking profits!"
                    )

                if trail_on:
                    new_stop = round(peak * (1 - self.cfg["trail_pct"] / 100), 8)
                    if new_stop > (t["trailing_stop"] or 0):
                        t["trailing_stop"] = new_stop
                        trail_stop = new_stop
                        log.info(f"  ⬆️  Trail stop raised -> {trail_stop}")

                if trail_on and current <= trail_stop:
                    log.warning(f"  📉 TRAIL STOP HIT: {symbol} @ {current} (stop={trail_stop})")
                    self._exit(t, current, "TRAILING STOP", round(profit_pct, 2))
                    continue

                if current <= hard_sl:
                    log.warning(f"  🛑 HARD SL HIT: {symbol} @ {current}")
                    self._exit(t, current, "HARD STOP LOSS", round(profit_pct, 2))
                    continue

                remaining.append(t)

            except Exception as e:
                log.error(f"  ❌ Monitor error {symbol}: {e}")
                remaining.append(t)

        self._save(remaining)

    def exit_on_dump(self, dump_signals: list[dict]):
        trades = self._load()
        dump_symbols = {s["symbol"] for s in dump_signals}
        remaining = []
        for t in trades:
            if t["symbol"] in dump_symbols:
                try:
                    current = self.client.get_ticker_price(t["symbol"])
                    profit_pct = (current - t["entry_price"]) / t["entry_price"] * 100
                    log.warning(f"  ⚠️ DUMP SIGNAL for {t['symbol']} — exiting early")
                    self._exit(t, current, "DUMP SIGNAL ⚠️", round(profit_pct, 2))
                except Exception as e:
                    log.error(f"  ❌ Dump exit error {t['symbol']}: {e}")
                    remaining.append(t)
            else:
                remaining.append(t)
        self._save(remaining)

    def _exit(self, trade: dict, current: float, reason: str, pnl_pct: float):
        symbol   = trade["symbol"]
        qty      = trade["qty"]
        entry    = trade["entry_price"]
        usdt     = trade["usdt_used"]
        pnl_usdt = round(usdt * pnl_pct / 100, 2)
        sell_price = round(current * (1 - SLIP_PCT / 100), 8)

        try:
            self.client.place_order(symbol, "sell", "limit", qty, price=sell_price)
            log.info(f"  📤 SELL placed: {symbol}")
        except Exception as e:
            log.error(f"  ❌ SELL failed {symbol}: {e}")

        try:
            opened = datetime.fromisoformat(trade["opened_at"])
            mins   = int((datetime.now(timezone.utc) - opened).total_seconds() / 60)
            held   = f"\n⏱️  Held: {mins} min"
        except Exception:
            held = ""

        icon = "💰" if pnl_pct > 0 else "📉"
        label = "✅ PROFIT" if pnl_pct > 0 else "🔴 LOSS"
        self.notifier.send(
            f"{icon} *TRADE CLOSED — {reason}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Symbol*     : `{symbol}`\n"
            f"💵 *Entry*      : `{entry}`\n"
            f"💵 *Exit*       : `{current}`\n"
            f"📈 *Peak*       : `{trade['peak_price']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{label} *P&L* : `{pnl_pct:+.2f}%`  (`${pnl_usdt:+.2f}`)\n"
            f"🏆 *Best*       : +{trade['highest_profit_pct']}%\n"
            f"🎯 *Score*      : `{trade['score']}/100`"
            f"{held}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )

    def _usdt_balance(self) -> float:
        return self.client.get_usdt_balance()

    @staticmethod
    def _load() -> list:
        return json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else []

    @staticmethod
    def _save(data: list):
        with open(STATE_FILE, "w") as f:
            json.dump(data, f, indent=2)
