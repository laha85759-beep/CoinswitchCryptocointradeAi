"""Check what fields c2c2 tickers have for volume."""
import os, time
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

from coinswitch_client import CoinSwitchClient
cs = CoinSwitchClient(os.getenv('CS_API_KEY'), os.getenv('CS_API_SECRET'), rate_limit_delay=0.5)

tickers = cs.get_all_tickers("c2c2")
print(f"c2c2 tickers: {len(tickers)}")

# Print first ticker to see all fields
first_sym = list(tickers.keys())[0]
print(f"\nFirst ticker ({first_sym}) fields:")
for k, v in tickers[first_sym].items():
    print(f"  {k}: {v}")

# Check volume fields on BTC/USDT
btc = tickers.get("BTC/USDT", {})
print(f"\nBTC/USDT volume fields:")
for k, v in btc.items():
    if 'vol' in k.lower() or 'volume' in k.lower():
        print(f"  {k}: {v}")
print(f"  All keys: {list(btc.keys())}")
