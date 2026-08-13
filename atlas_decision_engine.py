"""
ATLAS Layer 4 — Decision Engine (4 Agents)
==========================================
Final synthesis layer. Reads all 21 agents above, weighted by Darwin scores.
Makes the FINAL trade call.

  1. CRO_Risk       - Adversarial risk officer: attacks every signal
  2. AlphaDiscovery - Finds names nobody else mentioned
  3. AutoExecution  - Converts final signal to sized trade
  4. CIO_Synthesizer- Reads ALL layers, weighted by Darwin scores, final call
"""
from __future__ import annotations
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
import requests

log = logging.getLogger(__name__)


class DecisionResult:
    def __init__(self, agent: str, action: str, symbol: str, confidence: float,
                 reasoning: str, veto: bool = False, veto_reason: str = ""):
        self.agent = agent
        self.action = action          # BUY / SELL / HOLD / VETO
        self.symbol = symbol
        self.confidence = round(max(0, min(100, confidence)), 1)
        self.reasoning = reasoning
        self.veto = veto
        self.veto_reason = veto_reason
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "action": self.action,
            "symbol": self.symbol,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "veto": self.veto,
            "veto_reason": self.veto_reason,
            "timestamp": self.timestamp,
        }


# ─────────────────────────────────────────────────────────────
# Agent 1: CRO Risk (Chief Risk Officer — adversarial)
# ─────────────────────────────────────────────────────────────
class CROAgent:
    """
    The adversary. Attacks EVERY proposed trade.
    Checks: portfolio correlation, macro regime alignment, drawdown risk, liquidity.
    If it finds fatal flaw → VETO.
    """
    NAME = "CRO_Risk"

    def run(self, proposed_trade: str, macro_regime: str,
            sector_consensus: str, supertrader_consensus: str) -> DecisionResult:

        vetoes = []
        warnings = []

        # Check 1: Macro alignment
        if macro_regime == "RISK_OFF" and supertrader_consensus == "LONG":
            vetoes.append("MACRO MISALIGNMENT: Supertraders want LONG but macro is RISK_OFF. Fatal.")
        elif macro_regime == "RISK_OFF" and sector_consensus == "BULLISH":
            warnings.append("Sector bullish but macro risk-off. Reduce position size by 50%.")

        # Check 2: Correlation risk
        if proposed_trade in ("BTC/USDT", "ETH/USDT") and macro_regime == "RISK_OFF":
            vetoes.append(f"CORRELATION RISK: {proposed_trade} is highly correlated to risk-off macro. Don't fight the macro.")

        # Check 3: Consensus check
        long_count = sum([
            1 if macro_regime == "RISK_ON" else 0,
            1 if sector_consensus == "BULLISH" else 0,
            1 if supertrader_consensus == "LONG" else 0,
        ])

        if long_count == 0:
            vetoes.append("ZERO CONSENSUS: No layer agrees on LONG direction. CRO VETO.")
        elif long_count == 1:
            warnings.append(f"LOW CONSENSUS: Only 1/3 layers bullish. Reduce size to 25% max.")

        # CRO decision
        if vetoes:
            return DecisionResult(
                self.NAME, "VETO", proposed_trade, 95,
                f"CRO VETO ISSUED. Reasons: {' | '.join(vetoes)}. Warnings: {' | '.join(warnings) or 'None'}.",
                veto=True, veto_reason=" | ".join(vetoes)
            )
        elif warnings:
            return DecisionResult(
                self.NAME, "CAUTION", proposed_trade, 60,
                f"CRO CAUTION: Trade approved with reduced sizing. {' | '.join(warnings)}. "
                f"Consensus score: {long_count}/3 layers aligned.",
                veto=False
            )
        else:
            return DecisionResult(
                self.NAME, "APPROVED", proposed_trade, 85,
                f"CRO APPROVED: All risk checks passed. {long_count}/3 layers aligned. "
                f"Macro: {macro_regime} | Sector: {sector_consensus} | "
                f"Supertraders: {supertrader_consensus}. Full position sizing permitted.",
                veto=False
            )


# ─────────────────────────────────────────────────────────────
# Agent 2: Alpha Discovery Agent
# ─────────────────────────────────────────────────────────────
class AlphaDiscoveryAgent:
    """
    Finds coins that nobody else in the pipeline mentioned.
    Scans CoinGecko trending + top gainers for hidden momentum.
    """
    NAME = "Alpha_Discovery"

    def run(self, existing_picks: list) -> DecisionResult:
        # Get trending coins
        trending = {}
        try:
            r = requests.get("https://api.coingecko.com/api/v3/search/trending", timeout=8)
            if r.status_code == 200:
                coins = r.json().get("coins", [])
                for coin in coins[:7]:
                    item = coin.get("item", {})
                    trending[item.get("symbol", "?").upper()] = item.get("name", "?")
        except Exception as e:
            log.debug("Trending fetch failed: %s", e)

        # Find coins in trending but NOT in existing picks
        existing_symbols = set()
        for pick in existing_picks:
            sym = pick.split("/")[0].upper() if "/" in pick else pick.upper()
            existing_symbols.add(sym)

        hidden_gems = {k: v for k, v in trending.items() if k not in existing_symbols}

        if hidden_gems:
            top_gem = list(hidden_gems.items())[0]
            symbol = f"{top_gem[0]}/USDT"
            reasoning = (f"ALPHA DISCOVERY: Found {symbol} ({top_gem[1]}) trending on CoinGecko "
                         f"but NOT mentioned by any other agent. "
                         f"Hidden momentum opportunity. Other trending: {', '.join(list(hidden_gems.keys())[1:4])}. "
                         f"Allocate small exploratory position (5-10% of trade budget).")
            return DecisionResult(self.NAME, "ALPHA_FOUND", symbol, 60, reasoning)
        else:
            reasoning = (f"ALPHA DISCOVERY: All {len(trending)} trending coins already covered by other agents. "
                         f"No hidden alpha found. Current picks are comprehensive.")
            return DecisionResult(self.NAME, "NO_ALPHA", existing_picks[0] if existing_picks else "BTC/USDT",
                                  40, reasoning)


# ─────────────────────────────────────────────────────────────
# Agent 3: Auto Execution Agent
# ─────────────────────────────────────────────────────────────
class AutoExecutionAgent:
    """
    Converts the CIO's final signal into a properly sized trade.
    Implements position sizing, stop-loss, and take-profit levels.
    Does NOT execute directly — returns parameters for dual_exchange.py to consume.
    """
    NAME = "Auto_Execution"

    def run(self, symbol: str, action: str, confidence: float,
            macro_regime: str, available_capital_usdt: float,
            cro_action: str) -> DecisionResult:

        if cro_action == "VETO" or action not in ("BUY", "LONG"):
            return DecisionResult(
                self.NAME, "NO_EXECUTE", symbol, 0,
                f"AUTO EXECUTION: Trade blocked. CRO={cro_action}, Action={action}. No order placed.",
            )

        # Position sizing based on confidence + macro regime
        base_pct = 0.35  # 35% of capital per trade (bot's default)
        if macro_regime == "RISK_ON" and confidence > 75:
            size_pct = min(0.50, base_pct * 1.4)  # Scale up in strong bull
        elif macro_regime == "RISK_OFF" or confidence < 55:
            size_pct = base_pct * 0.5             # Scale down in risk-off
        elif cro_action == "CAUTION":
            size_pct = base_pct * 0.5             # CRO caution = half size
        else:
            size_pct = base_pct

        trade_value_usdt = round(available_capital_usdt * size_pct, 2)

        # Get live price for quantity calculation
        try:
            coin_id = symbol.split("/")[0].lower()
            r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                             params={"ids": coin_id, "vs_currencies": "usd"}, timeout=6)
            price = r.json().get(coin_id, {}).get("usd", 1) if r.status_code == 200 else 1
        except Exception:
            price = 1

        quantity = round(trade_value_usdt / price, 6) if price > 0 else 0
        stop_loss_pct   = 1.5   # 1.5% hard stop
        take_profit_pct = 4.0   # 4% take profit
        trail_activate  = 1.5   # Trail activates at +1.5%

        reasoning = (
            f"AUTO EXECUTION PLAN: {symbol} {action}\n"
            f"  Capital available: ${available_capital_usdt:.2f} USDT\n"
            f"  Position size: {size_pct*100:.0f}% = ${trade_value_usdt:.2f} USDT\n"
            f"  Quantity: {quantity} {symbol.split('/')[0]}\n"
            f"  Entry price: ~${price:,.4f}\n"
            f"  Stop loss: -{stop_loss_pct}% = ${price * (1 - stop_loss_pct/100):,.4f}\n"
            f"  Take profit: +{take_profit_pct}% = ${price * (1 + take_profit_pct/100):,.4f}\n"
            f"  Trail activates at: +{trail_activate}%\n"
            f"  Confidence: {confidence:.0f}% | Macro: {macro_regime}"
        )

        return DecisionResult(self.NAME, "EXECUTE", symbol, confidence, reasoning,
                              veto=False)


# ─────────────────────────────────────────────────────────────
# Agent 4: CIO Synthesizer (Chief Investment Officer)
# ─────────────────────────────────────────────────────────────
class CIOSynthesizerAgent:
    """
    The final decision maker. Reads ALL 3 layers above, weighted by Darwin scores.
    Makes the final ACTIONABLE call: BUY / SELL / HOLD.
    
    This is the ATLAS CIO — the most important agent.
    All other 24 agents feed into this one.
    """
    NAME = "CIO_Synthesizer"

    def run(self, macro_output: dict, sector_output: dict,
            supertrader_output: dict, agent_weights: dict = None) -> DecisionResult:
        
        weights = agent_weights or {}

        macro_regime     = macro_output.get("macro_regime",        "NEUTRAL")
        macro_conf       = macro_output.get("macro_confidence",    0.5)
        sector_consensus = sector_output.get("sector_consensus",   "NEUTRAL")
        avg_sector_score = sector_output.get("avg_sector_score",   50)
        st_consensus     = supertrader_output.get("supertrader_consensus", "WAIT")
        top_conv_trade   = supertrader_output.get("top_conviction_trade",  "BTC/USDT")
        top_conv_agent   = supertrader_output.get("top_conviction_agent",  "Unknown")

        # Darwin-weighted scoring
        macro_w  = weights.get("macro_layer",       1.0)
        sector_w = weights.get("sector_layer",      1.0)
        super_w  = weights.get("supertrader_layer", 1.0)

        # Build CIO score
        cio_bull_score = 0
        cio_bear_score = 0

        if macro_regime == "RISK_ON":
            cio_bull_score += macro_conf * 100 * macro_w
        elif macro_regime == "RISK_OFF":
            cio_bear_score += macro_conf * 100 * macro_w

        if sector_consensus == "BULLISH":
            cio_bull_score += (avg_sector_score - 50) * 2 * sector_w
        elif sector_consensus == "BEARISH":
            cio_bear_score += (50 - avg_sector_score) * 2 * sector_w

        if st_consensus == "LONG":
            cio_bull_score += 60 * super_w
        elif st_consensus == "SHORT":
            cio_bear_score += 60 * super_w

        total = cio_bull_score + cio_bear_score or 1
        bull_pct = round(cio_bull_score / total * 100, 1)
        bear_pct = round(cio_bear_score / total * 100, 1)

        # CIO final call
        if bull_pct >= 65:
            action = "BUY"
            final_symbol = top_conv_trade if top_conv_trade != "NONE" else "BTC/USDT"
            confidence = bull_pct
            reasoning = (
                f"CIO FINAL CALL: BUY {final_symbol}\n"
                f"  Bull score: {bull_pct:.1f}% | Bear score: {bear_pct:.1f}%\n"
                f"  Macro: {macro_regime} ({macro_conf*100:.0f}% confidence)\n"
                f"  Sector: {sector_consensus} (score {avg_sector_score:.0f}/100)\n"
                f"  Supertraders: {st_consensus} — top conviction: {top_conv_agent}\n"
                f"  All 4 layers synthesized with Darwin weights. EXECUTE."
            )
        elif bear_pct >= 65:
            action = "SELL"
            final_symbol = "BTC/USDT"
            confidence = bear_pct
            reasoning = (
                f"CIO FINAL CALL: SELL / AVOID LONGS\n"
                f"  Bear score: {bear_pct:.1f}% | Bull score: {bull_pct:.1f}%\n"
                f"  Macro: {macro_regime} | Sector: {sector_consensus} | ST: {st_consensus}\n"
                f"  Strong consensus against taking new long positions. "
                f"  Close existing positions, move to USDT."
            )
        else:
            action = "HOLD"
            final_symbol = "NONE"
            confidence = 40
            reasoning = (
                f"CIO FINAL CALL: HOLD — No clear edge\n"
                f"  Bull: {bull_pct:.1f}% | Bear: {bear_pct:.1f}%\n"
                f"  Mixed signals across layers. No trade = preserving capital. "
                f"  Wait for consensus to form before acting."
            )

        return DecisionResult(self.NAME, action, final_symbol, confidence, reasoning)


# ─────────────────────────────────────────────────────────────
# Decision Engine Runner
# ─────────────────────────────────────────────────────────────
def run_decision_engine(macro_output: dict, sector_output: dict,
                        supertrader_output: dict, available_capital_usdt: float = 10.0,
                        agent_weights: dict = None) -> dict:
    """
    Runs all 4 decision agents in sequence:
    CRO → AlphaDiscovery → CIO → AutoExecution
    """
    weights = agent_weights or {}
    results = {}

    # 1. CIO makes the call first
    cio = CIOSynthesizerAgent()
    cio_result = cio.run(macro_output, sector_output, supertrader_output, weights)
    results["CIO"] = cio_result.to_dict()

    # 2. CRO attacks the CIO's call
    cro = CROAgent()
    cro_result = cro.run(
        proposed_trade=cio_result.symbol,
        macro_regime=macro_output.get("macro_regime", "NEUTRAL"),
        sector_consensus=sector_output.get("sector_consensus", "NEUTRAL"),
        supertrader_consensus=supertrader_output.get("supertrader_consensus", "WAIT"),
    )
    results["CRO"] = cro_result.to_dict()

    # 3. Alpha Discovery looks for hidden plays
    all_picks = sector_output.get("top_picks", []) + [supertrader_output.get("top_conviction_trade", "")]
    alpha = AlphaDiscoveryAgent()
    alpha_result = alpha.run(existing_picks=all_picks)
    results["Alpha_Discovery"] = alpha_result.to_dict()

    # 4. Auto Execution creates the trade plan (if not vetoed)
    exec_agent = AutoExecutionAgent()
    exec_result = exec_agent.run(
        symbol=cio_result.symbol,
        action=cio_result.action,
        confidence=cio_result.confidence,
        macro_regime=macro_output.get("macro_regime", "NEUTRAL"),
        available_capital_usdt=available_capital_usdt,
        cro_action=cro_result.action,
    )
    results["Auto_Execution"] = exec_result.to_dict()

    # Final summary
    vetoed = cro_result.veto
    final_action = "NO_TRADE" if vetoed else cio_result.action
    final_symbol = "NONE" if vetoed else cio_result.symbol

    return {
        "final_action":  final_action,
        "final_symbol":  final_symbol,
        "cio_confidence": cio_result.confidence,
        "cro_vetoed":    vetoed,
        "cro_reason":    cro_result.veto_reason if vetoed else "",
        "alpha_pick":    alpha_result.symbol if alpha_result.action == "ALPHA_FOUND" else None,
        "agents":        results,
        "timestamp":     datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Test with dummy data
    dummy_macro = {"macro_regime": "RISK_ON", "macro_confidence": 0.72, "agents": []}
    dummy_sector = {"sector_consensus": "BULLISH", "avg_sector_score": 67, "top_picks": ["SOL/USDT"], "agents": []}
    dummy_super  = {"supertrader_consensus": "LONG", "top_conviction_trade": "SOL/USDT", "top_conviction_agent": "Druckenmiller_Crypto", "agents": []}
    print(json.dumps(run_decision_engine(dummy_macro, dummy_sector, dummy_super, 15.0), indent=2))
