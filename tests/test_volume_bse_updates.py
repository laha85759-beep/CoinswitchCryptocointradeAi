import unittest
from volume_strategy_agent import VolumeStrategyAgent
from indian_market_agent import IndianMarketAgent, DEFAULT_STOCKS
from config import CONFIG

class TestVolumeStrategyAndBSE(unittest.TestCase):
    def setUp(self):
        self.cfg = dict(CONFIG)

    def test_volume_strategy_high_rvol(self):
        agent = VolumeStrategyAgent(self.cfg)
        
        # 25 candles with average volume 1000, last candle has volume 3500 (RVOL 3.5x)
        candles = []
        base = 65000.0
        for i in range(25):
            c_open = base + i * 10
            c_close = c_open + (400.0 if i == 24 else 15.0)
            candles.append({
                "open": c_open,
                "high": c_close + 50,
                "low": c_open - 20,
                "close": c_close,
                "volume": 1000.0 if i < 24 else 3500.0
            })
            
        rvol = agent.calculate_rvol(candles, period=20)
        self.assertGreaterEqual(rvol, 3.0)
        
        market_data = {
            "symbol": "BTC/USDT",
            "candles": candles
        }
        signal = agent.evaluate_symbol(market_data)
        self.assertIsNotNone(signal)
        self.assertEqual(signal["direction"], "long")
        self.assertGreaterEqual(signal["confidence"], 0.76)
        self.assertGreater(signal["take_profit"], signal["entry_price"])
        self.assertLess(signal["hard_sl"], signal["entry_price"])

    def test_indian_market_bse_stocks(self):
        agent = IndianMarketAgent()
        stocks = agent.cached_stocks
        self.assertGreaterEqual(len(stocks), 20)
        
        bse_stocks = [s for s in stocks if s.get("exchange") == "BSE"]
        nse_stocks = [s for s in stocks if s.get("exchange") == "NSE"]
        
        self.assertGreaterEqual(len(bse_stocks), 10)
        self.assertGreaterEqual(len(nse_stocks), 12)
        
        # Check BSE momentum stocks have RVOL and targets
        for s in bse_stocks:
            self.assertIn("rvol", s)
            self.assertIn("target1", s)
            self.assertIn("stop_loss", s)

if __name__ == "__main__":
    unittest.main()
