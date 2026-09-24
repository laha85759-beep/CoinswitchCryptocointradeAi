# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from webhook_server import app
from security import create_jwt_token
import json

client = app.test_client()

# 1. Preset Strategies
res = client.get('/api/strategies/preset')
assert res.status_code == 200
data = res.get_json()
assert data['status'] == 'success'
assert len(data['strategies']) == 4
print('1. Preset strategies PASS:', [s['name'] for s in data['strategies']])

# 2. MT5 Validation
token = create_jwt_token({'user_id': 999, 'email': 'test@example.com', 'role': 'trader'})
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

mt5_payload = {
    'exchange': 'mt5',
    'credentials': {
        'server': 'FTMO-Demo',
        'login_id': '8849201',
        'password': 'Password99!'
    }
}
res_mt5 = client.post('/api/user/validate-keys', headers=headers, json=mt5_payload)
assert res_mt5.status_code == 200
data_mt5 = res_mt5.get_json()
assert data_mt5['valid'] == True
print('2. MT5 Validation PASS:', data_mt5['message'])

# 3. Strategy creation & Win Rate calculation
strat_payload = {
    'name': 'Alpha Confluence 15m',
    'timeframe': '15m',
    'indicators': ['rsi', 'ema_ribbon', 'supertrend', 'volume_spike'],
    'stop_loss_pct': 0.8,
    'take_profit_pct': 3.2,
    'trailing_pct': 0.2
}
res_strat = client.post('/api/user/strategies', headers=headers, json=strat_payload)
assert res_strat.status_code == 200
strat_data = res_strat.get_json()
assert strat_data['status'] == 'success'
print('3. Strategy creation PASS! Win Rate:', strat_data['strategy']['win_rate'], 'PF:', strat_data['strategy']['profit_factor'])

# 4. Activate strategy
res_act = client.post('/api/user/strategies/activate', headers=headers, json={'preset_id': 'nvidia_super_brain'})
assert res_act.status_code == 200
print('4. Activate strategy PASS!')

print('\n🎉 ALL 4 CRITICAL TESTS PASSED 100% PERFECTLY!')
sys.exit(0)
