import unittest

from coinswitch_client import CoinSwitchClient


class CoinSwitchClientLogicTests(unittest.TestCase):
    def setUp(self):
        self.client = CoinSwitchClient("test-key", "00" * 32)

    def test_order_fill_status_handles_filled_and_partially_filled(self):
        filled, qty = self.client.order_fill_status({"status": "filled"})
        self.assertTrue(filled)
        self.assertEqual(qty, 0.0)

        filled, qty = self.client.order_fill_status({"status": "partially_filled", "filled_quantity": 0.25})
        self.assertTrue(filled)
        self.assertEqual(qty, 0.25)

        filled, qty = self.client.order_fill_status({"status": "pending", "filled_quantity": 0.0})
        self.assertFalse(filled)
        self.assertEqual(qty, 0.0)

    def test_portfolio_balance_parsing_uses_locked_balance(self):
        available, locked, total = self.client._portfolio_balance({
            "currency": "USDT",
            "main_balance": "120.0",
            "locked_balance": "20.0",
        })

        self.assertEqual(available, 100.0)
        self.assertEqual(locked, 20.0)
        self.assertEqual(total, 120.0)


if __name__ == "__main__":
    unittest.main()
