"""Find which exchange + symbol combos work for candles on CoinSwitch."""
import os, time, logging
logging.basicConfig(level=logging.WARNING)

with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

from coinswitch_client import CoinSwitchClient
cs = CoinSwitchClient(os.getenv('CS_API_KEY'), os.getenv('CS_API_SECRET'), rate_limit_delay=0.3)

# Get all tickers from c2c2
tickers_c2c2 = cs.get_all_tickers("c2c2")
tickers_c2c1 = cs.get_all_tickers("c2c1")
print(f"c2c1 tickers: {len(tickers_c2c1)} | c2c2 tickers: {len(tickers_c2c2)}")

# Check candles for first 10 symbols from each exchange
now_ms = int(time.time() * 1000)
start_ms = now_ms - (100 * 5 * 60 * 1000)

print("\n--- Testing c2c2 symbols ---")
working_c2c2 = []
for sym in list(tickers_c2c2.keys())[:15]:
    if not sym.endswith('/USDT'):
        continue
    try:
        data = cs._request("GET", "/trade/api/v2/candles", params={
            "exchange": "c2c2", "symbol": sym, "interval": "5",
            "start_time": str(start_ms), "end_time": str(now_ms),
        })
        n = len(data.get("data", []))
        if n > 0:
            working_c2c2.append(sym)
            print(f"  c2c2 {sym}: {n} candles ✅")
        else:
            print(f"  c2c2 {sym}: 0 candles")
    except Exception as e:
        print(f"  c2c2 {sym}: ERROR {str(e)[:60]}")
    time.sleep(0.3)

print(f"\nWorking c2c2 symbols: {working_c2c2}")

print("\n--- Testing c2c1 symbols ---")
for sym in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']:
    try:
        data = cs._request("GET", "/trade/api/v2/candles", params={
            "exchange": "c2c1", "symbol": sym, "interval": "5",
            "start_time": str(start_ms), "end_time": str(now_ms),
        })
        n = len(data.get("data", []))
        print(f"  c2c1 {sym}: {n} candles")
    except Exception as e:
        print(f"  c2c1 {sym}: ERROR {str(e)[:60]}")
    time.sleep(0.3)
