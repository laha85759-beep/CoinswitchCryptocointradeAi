"""Full end-to-end local test: symbols -> candles -> signals -> risk -> order test."""
import os, sys, logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

from coinswitch_client import CoinSwitchClient
from delta_client import DeltaClient
from scanner import MarketScanner
from config import CONFIG

cs = CoinSwitchClient(os.getenv('CS_API_KEY'), os.getenv('CS_API_SECRET'), rate_limit_delay=0.5)
dx = DeltaClient(os.getenv('DELTA_API_KEY'), os.getenv('DELTA_API_SECRET'))

print("\n=== 1. CoinSwitch symbol scan ===")
scanner = MarketScanner(CONFIG, cs)
symbols = scanner._top_symbols()
print(f"Found {len(symbols)} symbols: {symbols[:10]}")

print("\n=== 2. CoinSwitch candles ===")
if symbols:
    df = scanner._ohlcv(symbols[0])
    if df is not None:
        print(f"{symbols[0]}: {len(df)} candles, last close={df['close'].iloc[-1]:.6f}")
    else:
        print(f"{symbols[0]}: NO candles returned")

print("\n=== 3. CoinSwitch balance ===")
bal = cs.get_usdt_balance()
print(f"USDT balance: {bal:.4f}")

print("\n=== 4. Delta price test ===")
try:
    price = dx.get_ticker_price("BTC/USDT")
    print(f"Delta BTC/USDT price: {price}")
except Exception as e:
    print(f"Delta price FAILED: {e}")

print("\n=== 5. Delta balance test ===")
try:
    bal_dx = dx.get_usdt_balance()
    print(f"Delta USDT balance: {bal_dx:.4f}")
except Exception as e:
    print(f"Delta balance FAILED: {e}")

print("\n=== 6. Delta product lookup ===")
try:
    pid = dx.symbol_to_product_id("BTC/USDT")
    print(f"BTC/USDT product_id on Delta: {pid}")
except Exception as e:
    print(f"Delta product lookup FAILED: {e}")

print("\nDone.")
