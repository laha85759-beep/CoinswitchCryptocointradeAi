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
        "stop_loss_pct": 3.0,
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

    def tearDown(self):
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


if __name__ == "__main__":
    unittest.main()
