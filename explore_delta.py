import requests
from collections import Counter

r = requests.get('https://cdn.india.deltaex.org/v2/products', timeout=15)
products = r.json().get('result', [])
print('Total products:', len(products))

types = Counter(p.get('contract_type','?') for p in products)
print('Contract types:', dict(types))

# BTC perpetual futures
btc = [p for p in products if 'BTC' in p.get('symbol','') and p.get('contract_type') == 'perpetual_futures']
for p in btc[:5]:
    sym = p.get('symbol','')
    pid = p.get('id','')
    ctype = p.get('contract_type','')
    settle = p.get('settling_asset',{}).get('symbol','?')
    print(f"  id={pid} symbol={sym} type={ctype} settle={settle}")

# Also check SOL, ETH, DOGE perps
for coin in ['ETH', 'SOL', 'DOGE', 'XRP', 'BNB']:
    perps = [p for p in products if coin in p.get('symbol','') and p.get('contract_type') == 'perpetual_futures']
    if perps:
        p = perps[0]
        print(f"  id={p['id']} symbol={p['symbol']} settle={p.get('settling_asset',{}).get('symbol','?')}")
