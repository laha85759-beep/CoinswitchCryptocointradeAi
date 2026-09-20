"""
Verification script for Capital Survival Mode & NVIDIA GLM-5.3 Super Brain
"""
import logging
from config import CONFIG
from nvidia_super_brain import NvidiaSuperBrainEngine
from agents import RiskManagerAgent, AuditLogger, load_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifySuperBrain")

def run_verification():
    print("=" * 60)
    print("CAPITAL SURVIVAL MODE & NVIDIA GLM-5.3 VERIFICATION")
    print("=" * 60)

    # 1. Verify Config
    print("\n1. Configuration Check:")
    print(f"  capital_survival_mode: {CONFIG.get('capital_survival_mode')}")
    print(f"  risk_per_trade_pct: {CONFIG.get('risk_per_trade_pct')}%")
    print(f"  max_position_pct: {CONFIG.get('max_position_pct')}%")
    print(f"  max_open_trades: {CONFIG.get('max_open_trades')}")
    print(f"  daily_max_drawdown_pct: {CONFIG.get('daily_max_drawdown_pct')}%")
    print(f"  min_rr_ratio: {CONFIG.get('min_rr_ratio')}")
    print(f"  nvidia_model_glm_5_3: {CONFIG.get('nvidia_model_glm_5_3')}")
    assert CONFIG.get("capital_survival_mode") is True, "Capital survival mode must be enabled"
    assert CONFIG.get("min_rr_ratio") >= 3.0, "Minimum R:R must be >= 3.0"

    # 2. Verify Super Brain Consensus
    brain = NvidiaSuperBrainEngine(CONFIG)
    market_snapshot = {
        "price": 68500.0,
        "volume_24h": 45000000.0,
        "change_24h": 2.8,
        "rsi": 42.0,
        "funding_rate": 0.0001,
        "smc_structure": "bullish_orderblock_mitigation",
        "liquidity_pool": "sell_side_swept",
    }
    
    print("\n2. Evaluating High Conviction Setup with Super Brain (GLM-5.3 Ensemble):")
    base_sig = {"signal": "pump", "confidence": 0.90, "supporting_data": market_snapshot}
    consensus = brain.evaluate_super_brain_consensus("BTC/USDT", base_sig, market_snapshot)
    print(f"  Consensus Approved: {consensus.get('approved')}")
    print(f"  Consensus Score: {consensus.get('consensus_score')}")
    print(f"  Take Profit Target: {consensus.get('take_profit_target')}")
    print(f"  Hard Invalidation SL: {consensus.get('hard_invalidation_sl')}")
    print(f"  GLM-5.3 Conviction: {consensus.get('glm_5_3_conviction')}")

    # 3. Verify RiskManager Fail-Closed on R:R < 3.0
    print("\n3. Testing Risk Manager R:R Gatekeeper:")
    class DummyClient:
        def get_ticker_price(self, s): return 68500.0
        def get_usdt_balance(self): return 1000.0
        def get_inr_balance(self): return 0.0
    
    risk_agent = RiskManagerAgent(CONFIG, DummyClient(), AuditLogger())

    valid_signal = {
        "signal_id": "test-valid-sig",
        "symbol": "BTC/USDT",
        "signal": "pump",
        "confidence": 0.92,
        "hard_sl_pct": 1.2,
        "take_profit_pct": 5.0, # R:R = 4.16 > 3.0
        "supporting_data": {"price": 68500.0, "volume_24h": 50000000.0, "atr_pct": 1.5},
        "timestamp": "2026-09-20T08:00:00+00:00",
    }
    approval_valid = risk_agent.evaluate([valid_signal])[0]
    print(f"  Valid Signal (R:R 4.16) Approved: {approval_valid['approved']}, Reason: {approval_valid['reason']}")
    assert approval_valid['approved'] is True, "High R:R signal must be approved"

    invalid_rr_signal = {
        "signal_id": "test-invalid-sig",
        "symbol": "BTC/USDT",
        "signal": "pump",
        "confidence": 0.92,
        "hard_sl_pct": 2.0,
        "take_profit_pct": 3.0, # R:R = 1.5 < 3.0
        "supporting_data": {"price": 68500.0, "volume_24h": 50000000.0, "atr_pct": 1.5},
        "timestamp": "2026-09-20T08:00:00+00:00",
    }
    approval_invalid = risk_agent.evaluate([invalid_rr_signal])[0]
    print(f"  Invalid Signal (R:R 1.50) Approved: {approval_invalid['approved']}, Reason: {approval_invalid['reason']}")
    assert approval_invalid['approved'] is False, "Low R:R signal must be rejected"
    assert "capital_survival_rr_ratio" in approval_invalid['reason'], "Must reject with capital_survival_rr_ratio"

    print("\n" + "=" * 60)
    print("ALL CAPITAL SURVIVAL PROTOCOL CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_verification()
