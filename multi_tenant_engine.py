import logging
import time
from datetime import datetime, timezone
from database import get_db, get_user_api_keys, get_user_settings
from coinswitch_client import CoinSwitchClient
from delta_client import DeltaClient

log = logging.getLogger("multi_tenant_engine")

def dispatch_signals_to_all_users(approved_signals: list[dict], global_cfg: dict = None) -> dict:
    """
    Evaluates approved trading signals across all registered users with autotrading enabled.
    Executes trades using each user's isolated API keys and personal risk preferences.
    """
    if not approved_signals:
        return {"users_processed": 0, "trades_executed": 0}

    cfg = global_cfg or {}
    if cfg.get("weekend_trading_disabled", True):
        now_utc = datetime.now(timezone.utc)
        if now_utc.weekday() in (5, 6):
            log.info("Multi-Tenant Engine: Weekend trading blocked (%s). Trades execute Monday to Friday only.", now_utc.strftime("%A"))
            return {"users_processed": 0, "trades_executed": 0, "reason": "weekend_trading_disabled"}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.email, u.name, s.hard_sl_pct, s.take_profit_pct, s.trail_pct, s.max_capital_pct, s.active_strategy
        FROM users u
        JOIN user_settings s ON u.id = s.user_id
        WHERE u.is_active = 1 AND s.autotrade_enabled = 1
    ''')
    active_users = cursor.fetchall()
    conn.close()

    total_executed = 0
    now = int(time.time())

    for user in active_users:
        user_id = user["id"]
        keys = get_user_api_keys(user_id)
        
        # Check if user has connected at least one exchange
        if not keys["has_cs"] and not keys["has_delta"]:
            continue

        user_strategy = user["active_strategy"] or "ai_consensus"
        hard_sl_pct = float(user["hard_sl_pct"] or 2.0)
        take_profit_pct = float(user["take_profit_pct"] or 15.0)

        for sig in approved_signals:
            symbol = sig.get("symbol", "")
            direction = sig.get("direction", "buy")
            price = float(sig.get("price") or sig.get("signal", {}).get("supporting_data", {}).get("price") or 0.0)
            confidence = float(sig.get("confidence") or sig.get("signal", {}).get("confidence") or 0.0)
            sig_strategy = sig.get("strategy") or sig.get("signal", {}).get("suspected_cause") or "ai_consensus"

            # Strategy Filter
            if user_strategy != "combined" and user_strategy != sig_strategy and confidence < 0.85:
                continue

            # Check open trade duplicate for this user
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM user_trades WHERE user_id = ? AND symbol = ? AND status = 'open'", (user_id, symbol))
            if cursor.fetchone():
                conn.close()
                continue

            sl_price = round(price * (1.0 - (hard_sl_pct / 100.0)), 6) if direction in ["buy", "long"] else round(price * (1.0 + (hard_sl_pct / 100.0)), 6)
            tp_price = round(price * (1.0 + (take_profit_pct / 100.0)), 6) if direction in ["buy", "long"] else round(price * (1.0 - (take_profit_pct / 100.0)), 6)

            # Execute on CoinSwitch if configured (spot only supports BUY)
            if keys["has_cs"] and direction in ["buy", "long"]:
                try:
                    cs_client = CoinSwitchClient(keys["cs_key"], keys["cs_secret"])
                    cs_usdt_bal = max(float(cs_client.get_usdt_balance()), 0.0)
                    if cs_usdt_bal >= 0.5:
                        trade_usdt = min(cs_usdt_bal * 0.95, 2.0)
                        qty = round(trade_usdt / price, 6) if price > 0 else 1.0
                        order_res = cs_client.place_order(symbol, "buy", "MARKET", qty)
                        if order_res and (order_res.get("order_id") or order_res.get("id") or order_res.get("status") in ["filled", "success", "open"]):
                            c_db = get_db()
                            c_cur = c_db.cursor()
                            c_cur.execute('''
                                INSERT INTO user_trades (user_id, exchange, symbol, direction, entry_price, qty, status, sl_price, tp_price, opened_at)
                                VALUES (?, 'coinswitch', ?, ?, ?, ?, 'open', ?, ?, ?)
                            ''', (user_id, symbol, direction, price, qty, sl_price, tp_price, now))
                            c_db.commit()
                            c_db.close()
                            total_executed += 1
                            log.info(f"Executed CoinSwitch live trade for User #{user_id} ({user['email']}) on {symbol}")
                    else:
                        log.debug("User #%s CS USDT balance $%.2f below minimum $0.50", user_id, cs_usdt_bal)
                except Exception as exc:
                    log.warning(f"CoinSwitch execution error for User #{user_id}: {exc}")

            # Execute on Delta if configured
            if keys["has_delta"]:
                try:
                    dl_client = DeltaClient(keys["delta_key"], keys["delta_secret"])
                    dl_usdt_bal = max(float(dl_client.get_usdt_balance()), 0.0)
                    if dl_usdt_bal >= 0.5:
                        delta_side = "buy" if direction in ["buy", "long"] else "sell"
                        prod_id = dl_client.symbol_to_product_id(symbol)
                        if prod_id:
                            order_res = dl_client.place_order(
                                symbol=symbol,
                                side=delta_side,
                                order_type="market",
                                quantity=1.0,
                                stop_loss_price=sl_price,
                                take_profit_price=tp_price,
                                leverage=3,
                            )
                            if order_res and (order_res.get("id") or order_res.get("success")):
                                c_db = get_db()
                                c_cur = c_db.cursor()
                                c_cur.execute('''
                                    INSERT INTO user_trades (user_id, exchange, symbol, direction, entry_price, qty, status, sl_price, tp_price, opened_at)
                                    VALUES (?, 'delta', ?, ?, ?, 1.0, 'open', ?, ?, ?)
                                ''', (user_id, symbol, direction, price, sl_price, tp_price, now))
                                c_db.commit()
                                c_db.close()
                                total_executed += 1
                                log.info(f"Executed Delta live trade for User #{user_id} ({user['email']}) on {symbol}")
                    else:
                        log.debug("User #%s Delta USDT balance $%.2f below minimum $0.50", user_id, dl_usdt_bal)
                except Exception as exc:
                    log.warning(f"Delta execution error for User #{user_id}: {exc}")

    return {"users_processed": len(active_users), "trades_executed": total_executed}