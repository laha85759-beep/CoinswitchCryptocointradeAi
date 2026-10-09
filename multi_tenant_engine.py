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
        
        # Check if user has connected at least one exchange (CoinSwitch, Delta, or CCXT Universal)
        from database import get_ccxt_exchange_keys
        ccxt_keys = get_ccxt_exchange_keys(user_id)
        has_ccxt = bool(ccxt_keys and any(k.get("api_key") for k in ccxt_keys))

        is_admin_user = (user.get("role") in ("superadmin", "tradeadmin", "admin") or user_id == 1)
        if not keys["has_cs"] and not keys["has_delta"] and not has_ccxt and not is_admin_user:
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

            # Dynamic Multi-Strategy Fallback:
            # If user's selected strategy matches -> Execute with primary priority
            # If primary strategy fails or setup is triggered by AI Consensus / SMC / Momentum -> fallback to best performing strategy
            strategy_match = (
                user_strategy in ("combined", "all", "best_strategy")
                or user_strategy == sig_strategy
                or "ai_consensus" in str(sig_strategy).lower()
                or "super_brain" in str(user_strategy).lower()
                or confidence >= 0.80  # Quality fallback threshold
            )
            if not strategy_match:
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

            sig_strategy_name = sig.get("strategy") or "Market Structure + VWAP"

            # 1. Execute on CoinSwitch Pro (Exchange 1: Spot INR/USDT)
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
                                INSERT INTO user_trades (user_id, exchange, symbol, direction, entry_price, qty, status, sl_price, tp_price, strategy, opened_at)
                                VALUES (?, 'coinswitch', ?, ?, ?, ?, 'open', ?, ?, ?, ?)
                            ''', (user_id, symbol, direction, price, qty, sl_price, tp_price, sig_strategy_name, now))
                            c_db.commit()
                            c_db.close()
                            total_executed += 1
                            log.info(f"Executed CoinSwitch live trade for User #{user_id} ({user['email']}) on {symbol} (Strategy: {sig_strategy_name})")
                    else:
                        log.debug("User #%s CS USDT balance $%.2f below minimum $0.50", user_id, cs_usdt_bal)
                except Exception as exc:
                    log.warning(f"CoinSwitch execution error for User #{user_id}: {exc}")

            # 2. Execute on Delta Exchange India (Exchange 2: Perpetuals Futures + Native Bracket SL/TP)
            if keys["has_delta"]:
                try:
                    dl_client = DeltaClient(keys["delta_key"], keys["delta_secret"])
                    dl_usdt_bal = max(float(dl_client.get_usdt_balance()), 0.0)
                    if dl_usdt_bal >= 0.20:
                        delta_side = "buy" if direction in ["buy", "long"] else "sell"
                        prod_id = dl_client.symbol_to_product_id(symbol)

                        # Balance-adaptive fallback: If chosen coin requires more margin than balance, route to affordable altcoin perp (e.g. XRPUSD)
                        target_sym = symbol
                        if dl_usdt_bal < 10.0 and symbol in ("BTC/USDT", "BTCUSD", "ETH/USDT", "ETHUSD", "SOL/USDT", "SOLUSD"):
                            alt_pid = dl_client.symbol_to_product_id("XRPUSD")
                            if alt_pid:
                                prod_id = alt_pid
                                target_sym = "XRPUSD"
                                log.info("Small balance ($%.2f) adaptive route: routed %s to XRPUSD", dl_usdt_bal, symbol)

                        target_sl = sl_price
                        target_tp = tp_price
                        target_entry_price = price
                        if target_sym != symbol:
                            target_curr_price = float(dl_client.get_ticker_price(target_sym) or 0.0)
                            if target_curr_price > 0:
                                target_entry_price = target_curr_price
                                target_sl = round(target_curr_price * (1.0 - (hard_sl_pct / 100.0)), 4) if delta_side == "buy" else round(target_curr_price * (1.0 + (hard_sl_pct / 100.0)), 4)
                                target_tp = round(target_curr_price * (1.0 + (take_profit_pct / 100.0)), 4) if delta_side == "buy" else round(target_curr_price * (1.0 - (take_profit_pct / 100.0)), 4)

                        if prod_id:
                            order_res = dl_client.place_order(
                                symbol=target_sym,
                                side=delta_side,
                                order_type="market",
                                quantity=1.0,
                                stop_loss_price=target_sl,
                                take_profit_price=target_tp,
                                leverage=5,
                            )
                            if order_res and (order_res.get("id") or order_res.get("success")):
                                c_db = get_db()
                                c_cur = c_db.cursor()
                                c_cur.execute('''
                                    INSERT INTO user_trades (user_id, exchange, symbol, direction, entry_price, qty, status, sl_price, tp_price, strategy, opened_at)
                                    VALUES (?, 'delta', ?, ?, ?, 1.0, 'open', ?, ?, ?, ?)
                                ''', (user_id, target_sym, direction, target_entry_price, target_sl, target_tp, sig_strategy_name, now))
                                c_db.commit()
                                c_db.close()
                                total_executed += 1
                                log.info(f"Executed Delta live trade for User #{user_id} ({user['email']}) on {target_sym} (Strategy: {sig_strategy_name})")
                    else:
                        log.debug("User #%s Delta USDT balance $%.2f below minimum $0.20", user_id, dl_usdt_bal)
                except Exception as exc:
                    log.warning(f"Delta execution error for User #{user_id}: {exc}")

            # 3. Execute on Universal CCXT (Exchange 3: Binance, Bybit, OKX, Bitget, KuCoin, etc.)
            if has_ccxt:
                for ck in ccxt_keys:
                    ex_id = ck.get("exchange_id", "").lower()
                    if not ex_id or not ck.get("api_key"):
                        continue
                    try:
                        from universal_exchange_engine import UniversalExchangeEngine
                        bal_info = UniversalExchangeEngine.fetch_balance(user_id, ex_id)
                        ex_usdt_bal = float(bal_info.get("free_usdt") or bal_info.get("total_usdt") or 0.0)
                        if ex_usdt_bal >= 1.0:
                            amount_usd = min(ex_usdt_bal * 0.25, 10.0)
                            order_qty_ccxt = round(amount_usd / max(1.0, price), 6)
                            ccxt_res = UniversalExchangeEngine.create_order(
                                user_id=user_id,
                                exchange_id=ex_id,
                                symbol=symbol,
                                side="buy" if direction in ["buy", "long"] else "sell",
                                order_type="market",
                                amount=order_qty_ccxt,
                                stop_loss_price=sl_price,
                                take_profit_price=tp_price,
                                leverage=3,
                            )
                            if ccxt_res and ccxt_res.get("status") not in ("error", None):
                                c_db = get_db()
                                c_cur = c_db.cursor()
                                c_cur.execute('''
                                    INSERT INTO user_trades (user_id, exchange, symbol, direction, entry_price, qty, status, sl_price, tp_price, strategy, opened_at)
                                    VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)
                                ''', (user_id, ex_id, symbol, direction, price, order_qty_ccxt, sl_price, tp_price, sig_strategy_name, now))
                                c_db.commit()
                                c_db.close()
                                total_executed += 1
                                log.info(f"Executed {ex_id.upper()} live trade for User #{user_id} ({user['email']}) on {symbol} (Strategy: {sig_strategy_name})")
                    except Exception as ccxt_err:
                        log.warning(f"Universal CCXT ({ex_id}) execution error for User #{user_id}: {ccxt_err}")

            # 4. Execute on MyFundedPerpetuals (Prop Firm Challenge with strict $75 loss cap)
            if user.get("role") in ("superadmin", "tradeadmin", "admin") or user_id == 1:
                try:
                    from config import CONFIG as _GCFG
                    if _GCFG.get("mfp_enabled"):
                        from myfundedperps_client import MyFundedPerpsClient
                        _mfp = MyFundedPerpsClient(
                            _GCFG.get("mfp_api_key", ""),
                            _GCFG.get("mfp_account_id"),
                            daily_loss_limit_usd=_GCFG.get("mfp_daily_loss_limit_usd", 75.0),
                            total_loss_limit_usd=_GCFG.get("mfp_total_loss_limit_usd", 75.0),
                        )
                        if _mfp.is_active:
                            clean_sym = symbol.replace("/USDT", "").replace("USDT", "").upper()
                            mfp_guard = _mfp.check_risk_guardrails()
                            if mfp_guard.get("safe_to_trade"):
                                mfp_markets = _mfp.get_markets()
                                if clean_sym in mfp_markets:
                                    m_info = mfp_markets[clean_sym]
                                    mfp_price = float(_mfp.get_ticker_price(clean_sym) or price or 1.0)
                                    decimals = int(m_info.get("size_decimals", 3) or 3)
                                    # Target ~$150-$250 notional at 5x leverage
                                    mfp_size = round(150.0 / max(1.0, mfp_price), decimals)
                                    if mfp_size <= 0:
                                        mfp_size = round(10 ** (-decimals), decimals)
                                    mfp_side = "buy" if direction in ["buy", "long"] else "sell"
                                    mfp_sl = round(mfp_price * (1.0 - (hard_sl_pct / 100.0)), 4) if mfp_side == "buy" else round(mfp_price * (1.0 + (hard_sl_pct / 100.0)), 4)
                                    mfp_tp = round(mfp_price * (1.0 + (take_profit_pct / 100.0)), 4) if mfp_side == "buy" else round(mfp_price * (1.0 - (take_profit_pct / 100.0)), 4)
                                    mfp_res = _mfp.place_order(
                                        symbol=clean_sym,
                                        side=mfp_side,
                                        size=mfp_size,
                                        leverage=5,
                                        order_type="market",
                                        take_profit_price=mfp_tp,
                                        stop_loss_price=mfp_sl,
                                        expected_price=mfp_price
                                    )
                                    if mfp_res and mfp_res.get("status") in ("filled", "open"):
                                        c_db = get_db()
                                        c_cur = c_db.cursor()
                                        c_cur.execute('''
                                            INSERT INTO user_trades (user_id, exchange, symbol, direction, entry_price, qty, status, sl_price, tp_price, strategy, opened_at)
                                            VALUES (?, 'mfp', ?, ?, ?, ?, 'open', ?, ?, ?, ?)
                                        ''', (user_id, f"{clean_sym}/USDT", direction, mfp_price, mfp_size, mfp_sl, mfp_tp, sig_strategy_name, now))
                                        c_db.commit()
                                        c_db.close()
                                        total_executed += 1
                                        log.info(f"Executed MyFundedPerpetuals live trade for User #{user_id} on {clean_sym} (Strategy: {sig_strategy_name}, TP: {mfp_tp}, SL: {mfp_sl})")
                except Exception as mfp_err:
                    log.warning(f"MyFundedPerpetuals execution error for User #{user_id}: {mfp_err}")

    return {"users_processed": len(active_users), "trades_executed": total_executed}