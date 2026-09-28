import os
import tempfile
import unittest
from pathlib import Path

from agents import AuditLogger, ExecutionAgent, RiskManagerAgent, load_json
from config import CONFIG


class FakeClient:
    def __init__(self):
        self.orders = []

    def get_ticker_price(self, symbol):
        return 100.0

    def place_order(self, *args, **kwargs):
        self.orders.append((args, kwargs))
        raise AssertionError("paper execution must not place live orders")


def base_config():
    return {
        "paper_trading_mode": True,
        "paper_portfolio_usdt": 1000.0,
        "min_confidence": 0.7,
        "min_liquidity_usd": 1_000_000.0,
        "max_position_pct": 2.0,
        "max_total_exposure_pct": 15.0,
        "max_trades_per_hour": 2,
        "daily_max_drawdown_pct": 5.0,
        "min_order_usdt": 10.0,
        "min_rr_ratio": 3.0,
        "stop_loss_pct": 1.5,
        "take_profit_pct": 6.0,
        "risk_order_type": "limit",
        "slippage_tolerance_pct": 1.0,
        "limit_slippage_offset_pct": 0.5,
        "max_retries": 2,
    }


def signal(confidence=0.8):
    return {
        "signal_id": "sig-1",
        "symbol": "BTC/USDT",
        "signal": "pump",
        "confidence": confidence,
        "supporting_data": {
            "price": 100.0,
            "volume_24h": 2_000_000.0,
            "timestamp": "2026-07-10T00:00:00+00:00",
        },
        "timestamp": "2026-07-10T00:00:00+00:00",
    }


class AgentSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmp.name)
        # Unit tests exercise risk logic, not the calendar gate — disable weekday gate
        self._old_gate = os.environ.get("TRADING_DAYS_ONLY_WEEKDAYS")
        os.environ["TRADING_DAYS_ONLY_WEEKDAYS"] = "false"

    def tearDown(self):
        if self._old_gate is None:
            os.environ.pop("TRADING_DAYS_ONLY_WEEKDAYS", None)
        else:
            os.environ["TRADING_DAYS_ONLY_WEEKDAYS"] = self._old_gate
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def test_risk_rejects_low_confidence_signal(self):
        risk = RiskManagerAgent(base_config(), FakeClient(), AuditLogger())

        result = risk.evaluate([signal(confidence=0.4)])[0]

        self.assertFalse(result["approved"])
        self.assertEqual(result["reason"], "confidence_below_minimum")

    def test_risk_approves_conservative_paper_position(self):
        risk = RiskManagerAgent(base_config(), FakeClient(), AuditLogger())

        result = risk.evaluate([signal()])[0]

        self.assertTrue(result["approved"])
        self.assertEqual(result["position_size_usd"], 20.0)
        self.assertEqual(result["direction"], "long")
        self.assertTrue(result["approval_token"])

    def test_paper_execution_records_trade_without_live_order(self):
        client = FakeClient()
        cfg = base_config()
        risk = RiskManagerAgent(cfg, client, AuditLogger())
        approval = risk.evaluate([signal()])[0]
        executor = ExecutionAgent(cfg, client, AuditLogger())

        result = executor.execute([approval])[0]

        self.assertEqual(result["status"], "filled")
        self.assertEqual(result["order_id"], "PAPER-sig-1")
        self.assertEqual(client.orders, [])
        trades = load_json(Path("open_trades.json"), [])
        self.assertEqual(len(trades), 1)
        self.assertTrue(trades[0]["paper"])

    def test_production_default_is_live_trading(self):
        self.assertFalse(CONFIG["paper_trading_mode"])

    def test_capital_survival_rejects_rr_below_3(self):
        risk = RiskManagerAgent(base_config(), FakeClient(), AuditLogger())
        low_rr_signal = signal()
        low_rr_signal["hard_sl_pct"] = 2.0
        low_rr_signal["take_profit_pct"] = 3.0  # R:R = 1.5 < 3.0
        result = risk.evaluate([low_rr_signal])[0]
        self.assertFalse(result["approved"])
        self.assertIn("capital_survival_rr_ratio", result["reason"])

    def test_weekend_trading_gate_blocks_trades(self):
        """With the weekday gate ON, weekend days must reject every trade."""
        os.environ["TRADING_DAYS_ONLY_WEEKDAYS"] = "true"
        try:
            risk = RiskManagerAgent(base_config(), FakeClient(), AuditLogger())
            trading_day, reason = risk.is_trading_day()
            result = risk.evaluate([signal()])[0]
            if not trading_day:  # Saturday/Sunday
                self.assertFalse(result["approved"])
                self.assertIn("trading_day_gate", result["reason"])
            else:  # Monday-Friday: gate passes through
                self.assertEqual(reason, "weekday")
                self.assertTrue(result["approved"])
        finally:
            os.environ["TRADING_DAYS_ONLY_WEEKDAYS"] = "false"


if __name__ == "__main__":
    unittest.main()
