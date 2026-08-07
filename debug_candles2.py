"""Test different CoinSwitch candle API parameter formats."""
import os, time, logging
logging.basicConfig(level=logging.WARNING)

with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

from coinswitch_client import CoinSwitchClient
cs = CoinSwitchClient(os.getenv('CS_API_KEY'), os.getenv('CS_API_SECRET'), rate_limit_delay=0.5)

now_ms = int(time.time() * 1000)
now_s  = int(time.time())

tests = [
    # (label, params)
    ("ms timestamps + interval=5",    {"exchange":"c2c1","symbol":"BTC/USDT","interval":"5",    "start_time":str(now_ms - 500*60*1000), "end_time":str(now_ms)}),
    ("s timestamps + interval=5",     {"exchange":"c2c1","symbol":"BTC/USDT","interval":"5",    "start_time":str(now_s - 500*60),       "end_time":str(now_s)}),
    ("ms timestamps + interval=5m",   {"exchange":"c2c1","symbol":"BTC/USDT","interval":"5m",   "start_time":str(now_ms - 500*60*1000), "end_time":str(now_ms)}),
    ("ms timestamps + resolution=5",  {"exchange":"c2c1","symbol":"BTC/USDT","resolution":"5",  "start_time":str(now_ms - 500*60*1000), "end_time":str(now_ms)}),
    ("ms timestamps + limit=100",     {"exchange":"c2c1","symbol":"BTC/USDT","interval":"5",    "limit":"100"}),
    ("no exchange param",             {"symbol":"BTC/USDT","interval":"5","start_time":str(now_ms - 500*60*1000),"end_time":str(now_ms)}),
    ("exchange c2c2",                 {"exchange":"c2c2","symbol":"BTC/USDT","interval":"5",    "start_time":str(now_ms - 500*60*1000), "end_time":str(now_ms)}),
]

for label, params in tests:
    try:
        data = cs._request("GET", "/trade/api/v2/candles", params=params)
        candles = data.get("data", [])
        raw_keys = list(data.keys())
        print(f"  [{label}]: {len(candles)} candles | response keys: {raw_keys}")
        if candles:
            print(f"    First candle keys: {list(candles[0].keys())}")
            break
    except Exception as e:
        print(f"  [{label}]: ERROR — {e}")
    time.sleep(0.6)
