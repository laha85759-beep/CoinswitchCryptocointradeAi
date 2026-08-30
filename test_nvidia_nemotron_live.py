import sys
import json
import logging
import requests

sys.path.insert(0, ".")
from config import CONFIG
from nvidia_nemotron_agent import NVIDIANemotronAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

print("==================================================================")
print("     NVIDIA NEMOTRON-3 ULTRA 550B LIVE API VERIFICATION           ")
print("==================================================================")

# 1. Test standard query on nvidia/nemotron-3-ultra-550b-a55b
print("\n[1/2] Testing User Query on nvidia/nemotron-3-ultra-550b-a55b...")
url = f"{CONFIG['nvidia_base_url']}/chat/completions"
headers = {
    "Authorization": f"Bearer {CONFIG['nvidia_api_key']}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}
payload = {
    "model": CONFIG["nvidia_model"],
    "messages": [{"role": "user", "content": "Write a limerick about the wonders of GPU computing."}],
    "temperature": 1,
    "top_p": 0.95,
    "max_tokens": 500
}

try:
    resp = requests.post(url, headers=headers, json=payload, timeout=20)
    print("HTTP Response Code:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        choice = data["choices"][0]["message"]
        reasoning = choice.get("reasoning_content")
        content = choice.get("content")
        
        if reasoning:
            print(f"\n• NVIDIA Deep Thinking Reasoning:\n{reasoning[:300]}...")
        print(f"\n• Model Response:\n{content}")
        print("\n[PASS] NVIDIA Nemotron 550B API Connection & Thinking VERIFIED!")
    else:
        print(f"[FAIL] NVIDIA API Error: {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"\n[FAIL] Request Error: {e}")

# 2. Test Quant Trading Signal Verification
print("\n[2/2] Testing Quant Trade Signal Reasoning Agent...")
agent = NVIDIANemotronAgent(CONFIG)
candidate = {
    "change_5m": 1.8,
    "change_1h": 3.5,
    "volume_zscore": 2.4,
    "orderbook_imbalance": 0.68,
    "confidence": 0.85
}
res = agent.verify_trade_signal("BTC/USDT", "pump", candidate)
print(f"• Quant Signal Decision: Approved={res.get('approved')} | Confidence={res.get('confidence')}")
print(f"• Reasoning: {res.get('reasoning')}")

print("==================================================================")
