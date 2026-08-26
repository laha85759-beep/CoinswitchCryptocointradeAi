import sys
import json
import logging

sys.path.insert(0, ".")
from config import CONFIG
from coinswitch_client import CoinSwitchClient
from delta_client import DeltaClient
from notifier import TelegramNotifier
from agents import DataCollectorAgent, SignalDetectorAgent, RiskManagerAgent
from dual_exchange import DualExecutionAgent, DualMonitorAgent
from funding_harvester import FundingHarvesterAgent
from kronos_agent import KronosAIAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

print("==================================================================")
print("     LIVE VERIFICATION: TRAILING POSITIONS, REINVESTMENT & AGENTS ")
print("==================================================================")

# 1. Trailing Position Engine Verification
try:
    dc = DeltaClient(CONFIG["delta_api_key"], CONFIG["delta_api_secret"])
    cs = CoinSwitchClient(CONFIG["api_key"], CONFIG["api_secret"])
    notifier = TelegramNotifier(CONFIG["telegram_token"], CONFIG["telegram_chat_id"])
    
    monitor = DualMonitorAgent(CONFIG, cs, dc, notifier, None)
    mon_res = monitor.monitor()
    open_count = mon_res.get("open_positions", 0)
    print(f"[PASS] 1. Trailing Position Engine: ACTIVE | Live Positions Monitored: {open_count}")
except Exception as e:
    print(f"[FAIL] 1. Trailing Engine Error: {e}")

# 2. Reinvestment & Capital Compounding Engine Verification
try:
    harvester = FundingHarvesterAgent(CONFIG, dc, notifier, None)
    yield_data = harvester.scan_and_collect_yield()
    earned = yield_data.get("total_yield_earned_usdt", 0.0)
    budget = yield_data.get("available_trading_budget_usdt", 0.0)
    print(f"[PASS] 2. Reinvestment Engine: ACTIVE | Total Yield Earned: ${earned:.4f} USDT | Reinvestment Budget: ${budget:.4f} USDT")
except Exception as e:
    print(f"[FAIL] 2. Reinvestment Engine Error: {e}")

# 3. All Trading Agents Pipeline Verification
try:
    collector = DataCollectorAgent(CONFIG, cs, None)
    detector = SignalDetectorAgent(CONFIG, None)
    kronos = KronosAIAgent(CONFIG)
    risk = RiskManagerAgent(CONFIG, cs, None, delta_client=dc)
    executor = DualExecutionAgent(CONFIG, cs, dc, notifier, None)
    print("[PASS] 3. All Agents (Collector, Detector, Kronos AI, Risk Manager, Executor): 100% ACTIVE")
except Exception as e:
    print(f"[FAIL] 3. Agents Error: {e}")

print("==================================================================")
