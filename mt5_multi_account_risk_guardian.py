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
                "max_open_trades": 2,
                "max_lot_per_trade": 0.05
            },
            "655344": {
                "name": "EquityEdge $50K (MT5 Follower)",
                "platform": "MetaTrader 5",
                "starting_balance": 50000.0,
                "daily_loss_limit_usd": 1500.0,
                "mll_floor_usd": 47000.0,
                "max_open_trades": 2,
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
        """
        Records daily telemetry snapshot with TRAILING Daily Loss and TRAILING Maximum Loss (High-Water Mark MLL).
        - Trailing Daily Loss = Highest Equity of the Day minus Current Equity (or Day-Start Balance minus Current Equity)
        - Trailing Maximum Loss = Lifetime/Session Peak Equity (High-Water Mark) minus Current Equity, locking in profit
        """
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
            "max_open_trades": 2,
            "max_lot_per_trade": 0.10
        })

        if login_id not in ledger[today]:
            # Baseline day start to the theoretical initial starting balance or previous balance
            init_baseline = rule["starting_balance"] if (rule.get("starting_balance") and rule["starting_balance"] > current_balance) else current_balance
            peak_hwm = max(current_equity, current_balance, rule["starting_balance"])
            
            # Initial trailing calculations
            initial_daily_loss = max(0.0, init_baseline - current_equity)
            initial_floor = rule["mll_floor_usd"]
            floor_breached = current_equity <= initial_floor
            daily_breached = initial_daily_loss >= rule["daily_loss_limit_usd"]

            ledger[today][login_id] = {
                "name": rule["name"],
                "day_start_balance": init_baseline,
                "lowest_equity": current_equity,
                "highest_equity": max(current_equity, init_baseline),
                "peak_high_water_mark": peak_hwm,
                "current_equity": current_equity,
                "current_balance": current_balance,
                "open_positions": open_positions_count,
                "unrealized_daily_loss": round(initial_daily_loss, 2),
                "trailing_daily_drawdown": round(initial_daily_loss, 2),
                "trailing_mll_floor": initial_floor,
                "trailing_mll_room": round(max(0.0, current_equity - initial_floor), 2),
                "trading_halted": daily_breached or floor_breached,
                "halt_reason": ("TRAILING_DAILY_LOSS_EXCEEDED" if daily_breached else "TRAILING_MLL_FLOOR_BREACH") if (daily_breached or floor_breached) else None,
                "last_sync": time.time()
            }
        else:
            acc_data = ledger[today][login_id]
            acc_data["current_equity"] = current_equity
            acc_data["current_balance"] = current_balance
            acc_data["open_positions"] = open_positions_count
            acc_data["lowest_equity"] = min(acc_data.get("lowest_equity", current_equity), current_equity)
            acc_data["highest_equity"] = max(acc_data.get("highest_equity", current_equity), current_equity)
            
            # 1. Update Lifetime/Session Peak Equity (High-Water Mark)
            prev_peak = acc_data.get("peak_high_water_mark", max(current_equity, rule["starting_balance"]))
            new_peak = max(prev_peak, current_equity)
            acc_data["peak_high_water_mark"] = new_peak
            
            # 2. Dynamic Trailing MLL Floor:
            # As account equity grows, trailing floor moves UP by profit made, never moves down
            profit_cushion = max(0.0, new_peak - rule["starting_balance"])
            trailing_floor = rule["mll_floor_usd"] + profit_cushion
            acc_data["trailing_mll_floor"] = round(trailing_floor, 2)
            
            # 3. Trailing Daily Drawdown:
            # Measures pullback from today's highest equity peak
            # Baseline balance is the maximum of recorded day_start_balance and account's starting balance
            start_bal = max(acc_data.get("day_start_balance", current_balance), rule["starting_balance"])
            acc_data["day_start_balance"] = start_bal
            day_peak = max(acc_data.get("highest_equity", current_equity), start_bal)
            acc_data["highest_equity"] = day_peak
            
            # Cumulative loss from starting baseline
            cumulative_loss = max(0.0, start_bal - current_equity)
            # Pullback from today's equity peak
            peak_pullback = max(0.0, day_peak - current_equity)
            trailing_daily_dd = max(cumulative_loss, peak_pullback)
            
            acc_data["unrealized_daily_loss"] = round(cumulative_loss, 2)
            acc_data["trailing_daily_drawdown"] = round(trailing_daily_dd, 2)

            # 4. Trailing Maximum Loss Room Remaining
            trailing_mll_room = current_equity - trailing_floor
            acc_data["trailing_mll_room"] = round(trailing_mll_room, 2)
            acc_data["last_sync"] = time.time()

            # 5. Enforce Trailing Circuit Breakers:
            if trailing_daily_dd >= rule["daily_loss_limit_usd"]:
                acc_data["trading_halted"] = True
                acc_data["halt_reason"] = f"TRAILING_DAILY_LOSS_EXCEEDED: Peak DD ${trailing_daily_dd:.2f} >= Limit ${rule['daily_loss_limit_usd']:.2f}"
            elif current_equity <= trailing_floor:
                acc_data["trading_halted"] = True
                acc_data["halt_reason"] = f"TRAILING_MLL_FLOOR_BREACH: Equity ${current_equity:.2f} <= Trailing Floor ${trailing_floor:.2f}"
            else:
                acc_data["trading_halted"] = False
                acc_data["halt_reason"] = None

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
            acc_data = ledger.get(acc_id)
            if not acc_data:
                acc_data = {
                    "name": rule["name"],
                    "current_balance": rule["starting_balance"],
                    "current_equity": rule["starting_balance"],
                    "open_positions": 0,
                    "trading_halted": False,
                    "halt_reason": "SYNCING",
                    "lowest_equity": rule["starting_balance"],
                    "highest_equity": rule["starting_balance"],
                    "peak_high_water_mark": rule["starting_balance"],
                    "trailing_daily_drawdown": 0.0,
                    "trailing_mll_floor": rule["mll_floor_usd"]
                }

            # Accurately compute daily loss including any drawdown below $10,000 / starting baseline
            start_bal = max(acc_data.get("day_start_balance", rule["starting_balance"]), rule["starting_balance"])
            actual_loss = max(acc_data.get("trailing_daily_drawdown", 0.0), max(0.0, start_bal - acc_data["current_equity"]))
            daily_room = max(0.0, rule["daily_loss_limit_usd"] - actual_loss)
            trailing_floor = acc_data.get("trailing_mll_floor", rule["mll_floor_usd"])
            floor_room = max(0.0, acc_data["current_equity"] - trailing_floor)

            report.append({
                "account_id": acc_id,
                "name": rule["name"],
                "current_balance": acc_data["current_balance"],
                "current_equity": acc_data["current_equity"],
                "day_peak_equity": acc_data.get("highest_equity", acc_data["current_equity"]),
                "peak_high_water_mark": acc_data.get("peak_high_water_mark", acc_data["current_equity"]),
                "daily_loss_limit": rule["daily_loss_limit_usd"],
                "trailing_daily_loss": round(actual_loss, 2),
                "daily_loss_room_remaining": round(daily_room, 2),
                "mll_floor": rule["mll_floor_usd"],
                "trailing_mll_floor": trailing_floor,
                "mll_cushion_remaining": round(floor_room, 2),
                "open_positions": acc_data.get("open_positions", 0),
                "max_positions": rule["max_open_trades"],
                "trading_status": "HALTED" if acc_data.get("trading_halted") else "SAFE_TRADING",
                "halt_reason": acc_data.get("halt_reason")
            })

        return report
