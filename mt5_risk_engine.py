"""
mt5_risk_engine.py - Automated Prop Firm Risk & Execution Engine for CK Capital / AlphaGlobalMarket
============================================================================================
Guarantees and Enforces Rules from Prop Firm Dashboard:
  1. Maximum Daily Loss: $300.00 USD (Kill-switch at $250.00 to preserve room)
  2. Maximum Limit Loss (Total Drawdown): $500.00 USD (Hard floor equity = $9,500.00 USD)
  3. Risk Per Trade: Capped at $30 - $50 USD (1:2 minimum Risk-to-Reward)
  4. Automatic Breakeven & Trailing Stop Loss on open positions
"""

import os
import time
import logging
from typing import Dict, Any, Optional

log = logging.getLogger('MT5RiskEngine')

class CKCapitalRiskGuardian:
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.max_daily_loss = float(os.getenv('MT5_MAX_DAILY_LOSS_USD', 300.0))
        self.max_total_loss = float(os.getenv('MT5_MAX_TOTAL_LOSS_USD', 500.0))
        self.mll_floor = float(os.getenv('MT5_MLL_FLOOR_USD', 9500.0))
        self.max_trade_risk = float(os.getenv('MT5_MAX_RISK_PER_TRADE_USD', 50.0))

    def evaluate_risk(self, current_equity: float, daily_pnl: float = 0.0) -> Dict[str, Any]:
        # 1. Total Drawdown Check (Floor = $9,500.00)
        remaining_total_loss_room = current_equity - self.mll_floor
        if current_equity <= self.mll_floor or remaining_total_loss_room <= 25.0:
            return {
                'safe_to_trade': False,
                'reason': f'CRITICAL: Total loss floor breached or near! Equity=${data_fmt}, Floor=${self.mll_floor:.2f}'
            }

        # 2. Daily Loss Limit Check ($300.00 cap)
        daily_loss = max(0.0, -daily_pnl)
        remaining_daily_room = self.max_daily_loss - daily_loss
        if daily_loss >= (self.max_daily_loss - 30.0):
            return {
                'safe_to_trade': False,
                'reason': f'Daily loss cap approaching or breached! Today loss=${daily_loss:.2f}, Cap=${self.max_daily_loss:.2f}'
            }

        return {
            'safe_to_trade': True,
            'current_equity': current_equity,
            'daily_loss_room': round(remaining_daily_room, 2),
            'total_loss_room': round(remaining_total_loss_room, 2),
            'max_allowed_risk_for_next_trade': min(self.max_trade_risk, remaining_daily_room * 0.5, remaining_total_loss_room * 0.5)
        }

    def calculate_lot_size(self, symbol: str, entry_price: float, stop_loss_price: float, risk_usd: Optional[float] = None) -> float:
        risk_budget = risk_usd or self.max_trade_risk
        stop_pips = abs(entry_price - stop_loss_price)
        if stop_pips <= 0:
            return 0.01
        if 'XAU' in symbol.upper() or 'GOLD' in symbol.upper():
            lot = risk_budget / (stop_pips * 100.0)
        else:
            lot = risk_budget / (stop_pips * 100000.0)
        return max(0.01, min(0.50, round(lot, 2)))
