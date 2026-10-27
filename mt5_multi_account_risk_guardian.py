"""
Multi-Account Risk Guardian & Daily Loss Tracker
Enforces strict prop-firm risk management on EVERY connected MT5 account every day:
  1. Master Account (#116810 - Goat Funded / CK Capital $10K):
     - Daily Loss Limit: $300.00
     - Max Drawdown Floor: $9,500.00
     - Max Open Trades: 3
  2. Follower Account (#655344 - EquityEdge-Trade $50K):
     - Daily Loss Limit: $1,500.00 (3% cap)
     - Max Drawdown Floor: $47,000.00
     - Max Open Trades: 5
     - Max Lot Size: 0.20 lots
"""

import os
import json
import time
import logging
from datetime import datetime, timezone

log = logging.getLogger("MultiAccountRiskGuardian")
DAILY_TRACKER_FILE = os.path.join(os.path.dirname(__file__), "mt5_daily_risk_ledger.json")

class MultiAccountRiskGuardian:
    def __init__(self, ledger_file=DAILY_TRACKER_FILE):
        self.ledger_file = ledger_file
        self.rules = {
            "116810": {
                "name": "CK Capital $10K (MT5 Master)",
                "platform": "MetaTrader 5",
                "starting_balance": 10000.0,
                "daily_loss_limit_usd": 300.0,
                "mll_floor_usd": 9500.0,
                "max_open_trades": 3,
                "max_lot_per_trade": 0.05
            },
            "655344": {
                "name": "EquityEdge $50K (MT5 Follower)",
                "platform": "MetaTrader 5",
                "starting_balance": 50000.0,
                "daily_loss_limit_usd": 1500.0,
                "mll_floor_usd": 47000.0,
                "max_open_trades": 5,
                "max_lot_per_trade": 0.20
            },
            "DELTA_INDIA": {
                "name": "Delta Exchange India (F&O & Perps)",
                "platform": "Delta India",
                "starting_balance": 500.0,
                "daily_loss_limit_usd": 25.0,
                "mll_floor_usd": 200.0,
                "max_open_trades": 5,
                "max_lot_per_trade": 1.0
            },
            "COINSWITCH": {
                "name": "CoinSwitch Pro (Spot Crypto)",
                "platform": "CoinSwitch",
                "starting_balance": 100.0,
                "daily_loss_limit_usd": 10.0,
                "mll_floor_usd": 50.0,
                "max_open_trades": 5,
                "max_lot_per_trade": 1.0
            },
            "MYFUNDEDPERPETUALS": {
                "name": "MyFundedPerpetuals ($2.5K Challenge)",
                "platform": "MFP Prop",
                "starting_balance": 2500.0,
                "daily_loss_limit_usd": 75.0,
                "mll_floor_usd": 2350.0,
                "max_open_trades": 5,
                "max_lot_per_trade": 0.5
            }
        }

    def _today_str(self):
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def load_ledger(self):
        if not os.path.exists(self.ledger_file):
            return {}
        try:
            with open(self.ledger_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_ledger(self, data):
        try:
            with open(self.ledger_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            log.error("Failed to save daily risk ledger: %s", e)

    def update_account_telemetry(self, login_id, current_equity, current_balance, open_positions_count=0):
        """Records daily telemetry snapshot and calculates daily drawdown."""
        login_id = str(login_id)
        today = self._today_str()
        ledger = self.load_ledger()

        if today not in ledger:
            ledger[today] = {}

        rule = self.rules.get(login_id, {
            "name": f"Account {login_id}",
            "starting_balance": current_balance,
            "daily_loss_limit_usd": current_balance * 0.03,
            "mll_floor_usd": current_balance * 0.90,
            "max_open_trades": 5,
            "max_lot_per_trade": 0.10
        })

        if login_id not in ledger[today]:
            ledger[today][login_id] = {
                "name": rule["name"],
                "day_start_balance": current_balance,
                "lowest_equity": current_equity,
                "highest_equity": current_equity,
                "current_equity": current_equity,
                "current_balance": current_balance,
                "open_positions": open_positions_count,
                "realized_daily_pnl": 0.0,
                "unrealized_daily_pnl": 0.0,
                "trading_halted": False,
                "halt_reason": None,
                "last_sync": time.time()
            }
        else:
            acc_data = ledger[today][login_id]
            acc_data["current_equity"] = current_equity
            acc_data["current_balance"] = current_balance
            acc_data["open_positions"] = open_positions_count
            acc_data["lowest_equity"] = min(acc_data["lowest_equity"], current_equity)
            acc_data["highest_equity"] = max(acc_data["highest_equity"], current_equity)
            acc_data["last_sync"] = time.time()

            # Calculate daily drawdown against day_start_balance
            start_bal = acc_data.get("day_start_balance", current_balance)
            daily_loss = start_bal - current_equity
            acc_data["unrealized_daily_loss"] = round(daily_loss, 2)

            # Check Circuit Breakers
            if daily_loss >= rule["daily_loss_limit_usd"]:
                acc_data["trading_halted"] = True
                acc_data["halt_reason"] = f"DAILY_LOSS_LIMIT_EXCEEDED: -${daily_loss:.2f} >= -${rule['daily_loss_limit_usd']:.2f}"
            elif current_equity <= rule["mll_floor_usd"]:
                acc_data["trading_halted"] = True
                acc_data["halt_reason"] = f"HARD_MLL_FLOOR_BREACH: Equity ${current_equity:.2f} <= Floor ${rule['mll_floor_usd']:.2f}"

        self.save_ledger(ledger)
        return ledger[today][login_id]

    def can_account_trade(self, login_id):
        """Pre-trade risk check before placing any trade on this account."""
        login_id = str(login_id)
        today = self._today_str()
        ledger = self.load_ledger()
        rule = self.rules.get(login_id)

        if not rule:
            return True, "No strict rule, trade permitted"

        acc_data = ledger.get(today, {}).get(login_id)
        if not acc_data:
            return True, "Day starting, trade permitted"

        if acc_data.get("trading_halted", False):
            return False, acc_data.get("halt_reason", "HALTED_BY_RISK_GUARDIAN")

        if acc_data.get("open_positions", 0) >= rule.get("max_open_trades", 5):
            return False, f"MAX_OPEN_POSITIONS_REACHED ({acc_data.get('open_positions')}/{rule['max_open_trades']})"

        return True, "RISK_APPROVED"

    def get_all_accounts_daily_status(self):
        """Returns consolidated live health report of all managed accounts."""
        today = self._today_str()
        ledger = self.load_ledger().get(today, {})
        report = []

        for acc_id, rule in self.rules.items():
            acc_data = ledger.get(acc_id, {
                "name": rule["name"],
                "current_balance": rule["starting_balance"],
                "current_equity": rule["starting_balance"],
                "open_positions": 0,
                "trading_halted": False,
                "halt_reason": "SYNCING",
                "lowest_equity": rule["starting_balance"]
            })

            daily_room = rule["daily_loss_limit_usd"] - (acc_data.get("day_start_balance", rule["starting_balance"]) - acc_data["current_equity"])
            floor_room = acc_data["current_equity"] - rule["mll_floor_usd"]

            report.append({
                "account_id": acc_id,
                "name": rule["name"],
                "current_balance": acc_data["current_balance"],
                "current_equity": acc_data["current_equity"],
                "daily_loss_limit": rule["daily_loss_limit_usd"],
                "daily_loss_room_remaining": max(0.0, round(daily_room, 2)),
                "mll_floor": rule["mll_floor_usd"],
                "mll_cushion_remaining": max(0.0, round(floor_room, 2)),
                "open_positions": acc_data.get("open_positions", 0),
                "max_positions": rule["max_open_trades"],
                "trading_status": "HALTED" if acc_data.get("trading_halted") else "SAFE_TRADING",
                "halt_reason": acc_data.get("halt_reason")
            })

        return report
