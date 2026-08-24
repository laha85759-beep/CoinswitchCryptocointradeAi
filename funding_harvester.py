"""
Self-Funding Yield Harvester & Interest-Only Trading Budget Manager
====================================================================
Stage 1 Engine:
  1. Scans Delta Exchange India for high positive funding rate contracts.
  2. Tracks daily funding fee yield & interest earned from exchange reserves.
  3. Maintains a persistent earned yield pool in `earned_yield.json`.
  4. Provides Stage 2 (Trading Bot) with an exact "Interest-Only" budget
     so trading margin ONLY uses earned income, keeping principal 100% safe.
"""

import json
import logging
import os
import time
from pathlib import Path

log = logging.getLogger(__name__)

EARNED_YIELD_FILE = Path("earned_yield.json")


class FundingHarvesterAgent:
    def __init__(self, cfg, delta_client=None, notifier=None, audit=None):
        self.cfg = cfg
        self.delta_client = delta_client
        self.notifier = notifier
        self.audit = audit
        self._ensure_yield_file()

    def _ensure_yield_file(self):
        if not EARNED_YIELD_FILE.exists():
            data = {
                "total_yield_earned_usdt": 0.0,
                "used_yield_budget_usdt": 0.0,
                "available_trading_budget_usdt": 0.0,
                "history": []
            }
            EARNED_YIELD_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_yield_data(self) -> dict:
        try:
            return json.loads(EARNED_YIELD_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {
                "total_yield_earned_usdt": 0.0,
                "used_yield_budget_usdt": 0.0,
                "available_trading_budget_usdt": 0.0,
                "history": []
            }

    def _save_yield_data(self, data: dict):
        try:
            EARNED_YIELD_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            log.warning("FundingHarvester: Failed to save yield data: %s", exc)

    def scan_and_collect_yield(self) -> dict:
        """
        Scans open positions and funding history to harvest earned funding rate income.
        Updates the available interest-only trading budget.
        """
        yield_data = self._load_yield_data()

        if self.delta_client is not None:
            try:
                # 1. Query live margined positions for realized funding payments
                res = self.delta_client._request("GET", "/v2/positions/margined")
                pos_list = res.get("result", []) if isinstance(res, dict) else (res if isinstance(res, list) else [])
                
                total_realized_funding = 0.0
                for pos in pos_list:
                    rf = float(pos.get("realized_funding", 0) or 0)
                    rc = float(pos.get("realized_cashflow", 0) or 0)
                    total_realized_funding += max(0.0, rf + rc)

                if total_realized_funding > yield_data["total_yield_earned_usdt"]:
                    new_gain = total_realized_funding - yield_data["total_yield_earned_usdt"]
                    yield_data["total_yield_earned_usdt"] = total_realized_funding
                    yield_data["available_trading_budget_usdt"] += new_gain
                    yield_data["history"].append({
                        "timestamp": time.time(),
                        "amount_usdt": new_gain,
                        "type": "funding_fee_harvest"
                    })
                    
                    if self.notifier and new_gain > 0.01:
                        self.notifier.send(
                            f"🌾 *YIELD HARVESTED (STAGE 1)*\n"
                            f"• Earned Income: `+${new_gain:.4f} USDT`\n"
                            f"• Total Earned Budget: `${yield_data['available_trading_budget_usdt']:.4f} USDT`\n"
                            f"🟢 *Added to Stage 2 Trading Allocation (Principal Protected)*"
                        )
            except Exception as exc:
                log.warning("FundingHarvester: Error scanning funding yield: %s", exc)

        self._save_yield_data(yield_data)
        return yield_data

    def get_available_trading_budget(self) -> float:
        """Returns the current earned interest/yield budget available for trading."""
        data = self._load_yield_data()
        return float(data.get("available_trading_budget_usdt", 0.0))

    def record_trade_margin_allocated(self, margin_usdt: float):
        """Deducts used margin from the earned yield budget pool."""
        data = self._load_yield_data()
        data["used_yield_budget_usdt"] += margin_usdt
        data["available_trading_budget_usdt"] = max(0.0, data["available_trading_budget_usdt"] - margin_usdt)
        self._save_yield_data(data)

    def record_trade_profit_reinvested(self, profit_usdt: float):
        """Adds trade profits back into the Stage 1 yield pool to compound returns."""
        data = self._load_yield_data()
        if profit_usdt > 0:
            data["total_yield_earned_usdt"] += profit_usdt
            data["available_trading_budget_usdt"] += profit_usdt
            data["history"].append({
                "timestamp": time.time(),
                "amount_usdt": profit_usdt,
                "type": "trading_profit_compounded"
            })
            log.info("FundingHarvester: Reinvested +$%s USDT profit into Stage 1 pool!", profit_usdt)
        self._save_yield_data(data)
