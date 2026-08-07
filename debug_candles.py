"""Debug: test CoinSwitch candles + tickers directly to find the real error."""
import os, logging, time
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

from coinswitch_client import CoinSwitchClient
cs = CoinSwitchClient(os.getenv('CS_API_KEY'), os.getenv('CS_API_SECRET'), rate_limit_delay=1.0)

# 1. Check tickers
print("\n--- TICKERS ---")
tickers = cs.get_all_tickers_multi()
print(f"Got {len(tickers)} tickers")
btc = tickers.get('BTC/USDT', {})
print(f"BTC/USDT: lastPrice={btc.get('lastPrice')}")

# 2. Try candles for 3 symbols and print raw error
print("\n--- CANDLES ---")
for sym in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']:
    try:
        end = int(time.time() * 1000)
        start = end - (100 * 5 * 60 * 1000)
        data = cs._request("GET", "/trade/api/v2/candles", params={
            "exchange": "c2c1",
            "symbol": sym,
            "interval": "5",
            "start_time": str(start),
            "end_time": str(end),
        })
        candles = data.get("data", [])
        print(f"  {sym}: {len(candles)} candles | first keys: {list(candles[0].keys()) if candles else 'EMPTY'}")
    except Exception as e:
        print(f"  {sym}: ERROR — {e}")
    time.sleep(1)
