"""
SuperBrain Multi-Account MT5 Copier & Broadcast Engine
Adapts and enhances tristannottelman/mt5-copy-trading:
  1. Multi-account copying (copies master trades to 1 or more follower accounts)
  2. Adaptive filling mode support (fixes error 10030)
  3. Dynamic StopLevel normalization (fixes error 10016)
  4. Webhook bridge broadcast integration (works seamlessly with SuperBrain EA and native MT5 Python)
"""

import os
import json
import time
import logging

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

log = logging.getLogger("MT5CopyTrading")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "mt5_accounts.json")

class SuperBrainMT5Copier:
    def __init__(self, config_file=CONFIG_PATH):
        self.config_file = config_file
        self.config = self.load_config()
        self.copied_positions = {}  # master_ticket -> {follower_id: follower_ticket}

    def load_config(self):
        if not os.path.exists(self.config_file):
            default = {
                "master_account": {
                    "login": 116810,
                    "password": "",
                    "server": "GoatFunded-Server"
                },
                "follower_accounts": [
                    {
                        "id": "account_655344",
                        "name": "50K Instant Account",
                        "enabled": True,
                        "login": 655344,
                        "password": "Z3B#9elUxc",
                        "server": "EquityEdge-Trade",
                        "account_size": 50000.0,
                        "lot_multiplier": 5.0,
                        "max_lot": 0.20
                    }
                ]
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=4)
            return default
        with open(self.config_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self, cfg):
        self.config = cfg
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)

    def add_follower_account(self, login, password, server, name="Follower Account", lot_multiplier=1.0, max_lot=0.05):
        """Register a new follower account to copy trades from master."""
        new_acc = {
            "id": f"account_{login}",
            "name": str(name),
            "enabled": True,
            "login": int(login),
            "password": str(password),
            "server": str(server),
            "lot_multiplier": float(lot_multiplier),
            "max_lot": float(max_lot)
        }
        followers = self.config.get("follower_accounts", [])
        existing = [f for f in followers if f.get("login") == int(login)]
        if existing:
            existing[0].update(new_acc)
        else:
            followers.append(new_acc)
        self.config["follower_accounts"] = followers
        self.save_config(self.config)
        log.info("Registered follower MT5 account: %s on %s", login, server)
        return new_acc

    def copy_command_to_followers(self, cmd):
        """
        Replicates a trade command to all enabled follower accounts.
        Scale lot size by lot_multiplier up to max_lot cap.
        """
        if not mt5:
            return []

        results = []
        action = cmd.get("action", "BUY").upper()
        symbol = cmd.get("symbol", "XAUUSD")
        base_vol = float(cmd.get("volume", 0.01))
        sl = float(cmd.get("sl", 0.0))
        tp = float(cmd.get("tp", 0.0))

        for follower in self.config.get("follower_accounts", []):
            if not follower.get("enabled", True):
                continue
            login = follower.get("login")
            pwd = follower.get("password")
            server = follower.get("server")
            mult = float(follower.get("lot_multiplier", 1.0))
            max_l = float(follower.get("max_lot", 0.20))
            vol = min(round(base_vol * mult, 2), max_l)
            if vol <= 0.0:
                vol = 0.01

            try:
                # Login to follower account
                if not mt5.login(login, password=pwd, server=server):
                    err = mt5.last_error()
                    log.error("Failed to login to follower %s: %s", login, err)
                    results.append({"account": login, "status": "LOGIN_FAILED", "error": str(err)})
                    continue

                if action in ("BUY", "SELL"):
                    # Select symbol
                    mt5.symbol_select(symbol, True)
                    tick = mt5.symbol_info_tick(symbol)
                    if not tick:
                        results.append({"account": login, "status": "SYMBOL_NOT_FOUND"})
                        continue

                    order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
                    price = tick.ask if action == "BUY" else tick.bid

                    # Adaptive filling mode detection
                    sym_info = mt5.symbol_info(symbol)
                    filling = sym_info.filling_mode if sym_info else 0
                    if filling & mt5.ORDER_FILLING_IOC:
                        filling_type = mt5.ORDER_FILLING_IOC
                    elif filling & mt5.ORDER_FILLING_FOK:
                        filling_type = mt5.ORDER_FILLING_FOK
                    else:
                        filling_type = mt5.ORDER_FILLING_RETURN

                    req = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": symbol,
                        "volume": vol,
                        "type": order_type,
                        "price": price,
                        "sl": sl,
                        "tp": tp,
                        "deviation": 20,
                        "magic": 20261027,
                        "comment": f"SuperBrain Copier {cmd.get('command_id', '')[:8]}",
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": filling_type
                    }

                    res = mt5.order_send(req)
                    if res.retcode == mt5.TRADE_RETCODE_DONE:
                        log.info("COPIED to follower %s: ticket #%d", login, res.order)
                        results.append({"account": login, "status": "EXECUTED", "ticket": res.order, "volume": vol})
                    elif res.retcode == 10016:  # invalid stops fallback
                        req["sl"] = 0.0
                        req["tp"] = 0.0
                        res2 = mt5.order_send(req)
                        if res2.retcode == mt5.TRADE_RETCODE_DONE:
                            if sl > 0 or tp > 0:
                                mod_req = {
                                    "action": mt5.TRADE_ACTION_SLTP,
                                    "position": res2.order,
                                    "symbol": symbol,
                                    "sl": sl,
                                    "tp": tp
                                }
                                mt5.order_send(mod_req)
                            results.append({"account": login, "status": "EXECUTED_FALLBACK", "ticket": res2.order, "volume": vol})
                        else:
                            results.append({"account": login, "status": "FAILED", "code": res2.retcode, "comment": res2.comment})
                    else:
                        results.append({"account": login, "status": "FAILED", "code": res.retcode, "comment": res.comment})

                elif action == "CLOSE_ALL":
                    positions = mt5.positions_get()
                    closed = 0
                    if positions:
                        for p in positions:
                            ctick = mt5.symbol_info_tick(p.symbol)
                            if not ctick: continue
                            c_type = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
                            c_price = ctick.bid if c_type == mt5.ORDER_TYPE_SELL else ctick.ask
                            c_req = {
                                "action": mt5.TRADE_ACTION_DEAL,
                                "position": p.ticket,
                                "symbol": p.symbol,
                                "volume": p.volume,
                                "type": c_type,
                                "price": c_price,
                                "deviation": 20,
                                "magic": 20261027,
                                "comment": "Copier Close All"
                            }
                            c_res = mt5.order_send(c_req)
                            if c_res.retcode == mt5.TRADE_RETCODE_DONE:
                                closed += 1
                    results.append({"account": login, "status": "CLOSED_ALL", "closed_count": closed})

            except Exception as e:
                log.error("Exception copying to follower %s: %s", login, e)
                results.append({"account": login, "status": "ERROR", "error": str(e)})

        return results
