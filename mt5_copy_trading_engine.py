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
                        "id": "follower_1",
                        "enabled": False,
                        "login": 0,
                        "password": "",
                        "server": "",
                        "lot_multiplier": 1.0,
                        "max_lot": 0.05
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

    def add_follower_account(self, login, password, server, lot_multiplier=1.0, max_lot=0.05):
        """Register a new follower account to copy trades from master."""
        new_acc = {
            "id": f"account_{login}",
            "enabled": True,
            "login": int(login),
            "password": str(password),
            "server": str(server),
            "lot_multiplier": float(lot_multiplier),
            "max_lot": float(max_lot)
        }
        # Check if already exists
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
