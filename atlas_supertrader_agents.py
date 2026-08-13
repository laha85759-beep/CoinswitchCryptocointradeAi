"""
ATLAS Layer 3 — Supertrader Agents (4 Agents)
=============================================
Inspired by ATLAS Pro superinvestor agents, adapted for Indian crypto markets.
Each agent has a distinct investment philosophy and analyzes the market through that lens.

  1. Druckenmiller_Crypto  - Macro/momentum: the one asymmetric trade
  2. Soros_Reflexivity     - Self-reinforcing narratives
  3. Simons_Quant          - Pure quant pattern, no bias
  4. Ackman_Conviction     - High-conviction best setup, sized large
"""
from __future__ import annotations
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List
import requests

log = logging.getLogger(__name__)


def _get_prices(coin_ids: str) -> dict:
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                         params={"ids": coin_ids, "vs_currencies": "usd",
                                 "include_24hr_change": "true", "include_7d_change": "true",
                                 "include_market_cap": "true"},
                         timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log.debug("Price fetch failed: %s", e)
    return {}


def _market_chart(coin_id: str, days: int = 14) -> list:
    try:
        r = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
                         params={"vs_currency": "usd", "days": str(days), "interval": "daily"},
                         timeout=10)
        if r.status_code == 200:
            return [p[1] for p in r.json().get("prices", [])]
    except Exception:
        pass
    return []


class SupertraderResult:
    def __init__(self, agent: str, conviction: float, top_trade: str,
                 direction: str, reasoning: str, risk_note: str = ""):
        self.agent = agent
        self.conviction = round(max(0, min(100, conviction)), 1)
        self.top_trade = top_trade
        self.direction = direction  # LONG / SHORT / WAIT
        self.reasoning = reasoning
        self.risk_note = risk_note
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "conviction": self.conviction,
            "top_trade": self.top_trade,
            "direction": self.direction,
            "reasoning": self.reasoning,
            "risk_note": self.risk_note,
            "timestamp": self.timestamp,
        }


# ─────────────────────────────────────────────────────────────
# Agent 1: Druckenmiller Crypto — Macro/Momentum
# ─────────────────────────────────────────────────────────────
class DruckenmillerCryptoAgent:
    """
    Stanley Druckenmiller style: find the ONE asymmetric trade.
    Focus on macro + momentum alignment. "When you see it, bet BIG."
    Never diversifies — finds the single highest-conviction macro trade.
    """
    NAME = "Druckenmiller_Crypto"
    WATCHLIST = "bitcoin,ethereum,solana,chainlink,ondo-finance"

    def run(self) -> SupertraderResult:
        data = _get_prices(self.WATCHLIST)
        
        candidates = {
            "BTC/USDT":  {"24h": data.get("bitcoin",       {}).get("usd_24h_change", 0),
                          "7d":  data.get("bitcoin",       {}).get("usd_7d_change", 0)},
            "ETH/USDT":  {"24h": data.get("ethereum",      {}).get("usd_24h_change", 0),
                          "7d":  data.get("ethereum",      {}).get("usd_7d_change", 0)},
            "SOL/USDT":  {"24h": data.get("solana",        {}).get("usd_24h_change", 0),
                          "7d":  data.get("solana",        {}).get("usd_7d_change", 0)},
            "LINK/USDT": {"24h": data.get("chainlink",     {}).get("usd_24h_change", 0),
                          "7d":  data.get("chainlink",     {}).get("usd_7d_change", 0)},
            "ONDO/USDT": {"24h": data.get("ondo-finance",  {}).get("usd_24h_change", 0),
                          "7d":  data.get("ondo-finance",  {}).get("usd_7d_change", 0)},
        }

        # Druckenmiller signal: short-term pullback in strong 7d uptrend = ENTRY
        best = None
        best_score = -999
        for sym, chg in candidates.items():
            # Momentum score: 7d trend is king, 24h dip is entry opportunity
            score = chg["7d"] * 2 - max(0, -chg["24h"]) * 0.5
            if score > best_score:
                best_score = score
                best = (sym, chg)

        if best and best[1]["7d"] > 8:
            direction = "LONG"
            conviction = min(92, 60 + best[1]["7d"] * 1.5)
            reasoning = (f"DRUCKENMILLER SIGNAL: {best[0]} has {best[1]['7d']:+.1f}% 7-day momentum "
                         f"with {best[1]['24h']:+.1f}% 24h print. This IS the asymmetric trade. "
                         f"Strong macro trend intact. Entry on any intraday dip. "
                         f"Position size: LARGE. This is the ONE trade.")
            risk = f"Stop below 7-day low. If BTC macro turns risk-off, exit immediately."
        elif best and best[1]["7d"] < -10:
            direction = "SHORT"
            conviction = 55
            top_sym = sorted(candidates, key=lambda x: candidates[x]["7d"])[0]
            reasoning = (f"DRUCKENMILLER: No clear LONG setup. Weakest asset is {top_sym} "
                         f"({candidates[top_sym]['7d']:+.1f}% 7d). Considering short but not ideal — "
                         f"Druckenmiller prefers strong uptrends to momentum-short into.")
            risk = "Macro could reverse sharply. Keep position small for shorts."
        else:
            direction = "WAIT"
            conviction = 30
            reasoning = ("DRUCKENMILLER: No asymmetric setup detected right now. "
                         "The best trade is NO trade. Preserve capital. Wait for a clear macro "
                         "regime shift or a strong breakout with volume confirmation.")
            risk = "Patience is the position."

        return SupertraderResult(self.NAME, conviction, best[0] if best else "NONE",
                                 direction, reasoning, risk)


# ─────────────────────────────────────────────────────────────
# Agent 2: Soros Reflexivity Agent
# ─────────────────────────────────────────────────────────────
class SorosReflexivityAgent:
    """
    George Soros style: find self-reinforcing narratives.
    "Markets are always wrong" — find where narrative is feeding price feeding narrative.
    Crypto narratives: AI tokens, ETF inflows, BTC halving cycle, stablecoin supply boom.
    """
    NAME = "Soros_Reflexivity"

    def run(self) -> SupertraderResult:
        data = _get_prices("bitcoin,ethereum,solana,dogecoin,ondo-finance")
        
        # Reflexivity check: is the narrative self-reinforcing?
        # If price is going up + sentiment improving + more buyers entering = reflexive loop
        fng_data = {}
        try:
            r = requests.get("https://api.alternative.me/fng/?limit=7", timeout=6)
            if r.status_code == 200:
                fng_data = r.json()
        except Exception:
            pass

        fng_values = [int(x["value"]) for x in fng_data.get("data", [])]
        fng_trend = (fng_values[0] - fng_values[-1]) if len(fng_values) >= 2 else 0
        btc_7d = data.get("bitcoin", {}).get("usd_7d_change", 0)
        eth_7d = data.get("ethereum", {}).get("usd_7d_change", 0)

        # Soros signal: rising F&G + rising price = reflexive bull loop
        if fng_trend > 10 and btc_7d > 5:
            direction = "LONG"
            conviction = 78
            top_trade = "ETH/USDT" if eth_7d > btc_7d else "BTC/USDT"
            reasoning = (f"SOROS REFLEXIVITY: Fear & Greed rising {fng_trend} points in 7 days while "
                         f"BTC +{btc_7d:.1f}% ETH +{eth_7d:.1f}%. Classic reflexive bull loop: "
                         f"Price rises → narrative improves → more buyers → price rises. "
                         f"RIDE THE NARRATIVE. Top trade: {top_trade}.")
            risk = "Reflexive loops break suddenly. Watch for narrative exhaustion (FNG > 80)."
        elif fng_trend < -15 and btc_7d < -5:
            direction = "WAIT"
            conviction = 40
            top_trade = "USDT"
            reasoning = (f"SOROS: Reflexive bear loop detected. FNG falling {abs(fng_trend)} pts + "
                         f"BTC {btc_7d:.1f}%. Narrative feeding sell pressure feeding more selling. "
                         f"Soros says: 'Do not stand in front of a train.' STAY CASH.")
            risk = "Bear reflexive loops overshoot. Wait for FNG < 20 for contrarian entry."
        else:
            direction = "NEUTRAL"
            conviction = 45
            top_trade = "BTC/USDT"
            btc_p = data.get("bitcoin", {}).get("usd", 0)
            reasoning = (f"SOROS: No strong reflexive loop. BTC at ${btc_p:,.0f}. "
                         f"FNG trend: {fng_trend:+d} pts. Market is in transitional phase. "
                         f"Watch for narrative catalyst to establish direction.")
            risk = "Position sizing minimal until reflexive loop confirms."

        return SupertraderResult(self.NAME, conviction, top_trade, direction, reasoning, risk)


# ─────────────────────────────────────────────────────────────
# Agent 3: Simons Quant Agent
# ─────────────────────────────────────────────────────────────
class SimonsQuantAgent:
    """
    Jim Simons style: pure pattern, no bias, no opinion.
    Medallion Fund approach: exploit statistical regularities in price data.
    In crypto: mean reversion on short timeframes + momentum on medium timeframes.
    """
    NAME = "Simons_Quant"

    def run(self) -> SupertraderResult:
        # Get 14-day price history for BTC to compute patterns
        prices = _market_chart("bitcoin", days=14)
        
        if len(prices) < 7:
            return SupertraderResult(self.NAME, 30, "NONE", "WAIT",
                                     "SIMONS QUANT: Insufficient price history for pattern analysis.",
                                     "No trade until data available.")

        # Pattern 1: Mean reversion — RSI-like divergence
        returns = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(1, len(prices))]
        recent_7d_avg = sum(returns[-7:]) / 7
        recent_3d_avg = sum(returns[-3:]) / 3

        # Pattern 2: Momentum — if 7d trend continues
        momentum_score = recent_7d_avg * 10
        reversion_signal = recent_3d_avg - recent_7d_avg  # negative = pullback, possible reversion

        # Simons pure signal
        if recent_7d_avg > 1.5 and reversion_signal < -1:
            direction = "LONG"
            conviction = 72
            top_trade = "BTC/USDT"
            reasoning = (f"SIMONS QUANT: 7d avg daily return +{recent_7d_avg:.2f}% (bullish trend). "
                         f"3d pullback: {recent_3d_avg:.2f}%. Statistical REVERSION signal — "
                         f"short-term dip within bullish trend. Pattern says: BUY THE DIP. "
                         f"No opinion. Just pattern.")
            risk = "Stop if 3-day drawdown exceeds 7-day average volatility."
        elif recent_7d_avg > 1.5 and reversion_signal >= 0:
            direction = "LONG"
            conviction = 65
            top_trade = "BTC/USDT"
            reasoning = (f"SIMONS QUANT: 7d avg daily return +{recent_7d_avg:.2f}%. Momentum intact. "
                         f"No reversion signal. Pattern says: RIDE MOMENTUM. Trend following mode.")
            risk = "Trail stop at 1.5% below recent peak."
        elif recent_7d_avg < -1.5:
            direction = "WAIT"
            conviction = 35
            top_trade = "NONE"
            reasoning = (f"SIMONS QUANT: 7d avg daily return {recent_7d_avg:.2f}% (bearish). "
                         f"Pattern: downtrend. Quant rule: never buy into a confirmed downtrend. "
                         f"Wait for reversal pattern (2+ consecutive positive returns above average).")
            risk = "Pattern confirmation requires 2 consecutive positive days."
        else:
            direction = "WAIT"
            conviction = 40
            top_trade = "NONE"
            reasoning = (f"SIMONS QUANT: 7d avg daily return {recent_7d_avg:+.2f}%. "
                         f"No statistically significant pattern. Simons: if no edge, NO TRADE.")
            risk = "Wait for pattern to form."

        return SupertraderResult(self.NAME, conviction, top_trade, direction, reasoning, risk)


# ─────────────────────────────────────────────────────────────
# Agent 4: Ackman Conviction Agent
# ─────────────────────────────────────────────────────────────
class AckmanConvictionAgent:
    """
    Bill Ackman style: concentrated conviction, maximum sizing on ONE best idea.
    Looks for: strong fundamentals + near-term catalyst + undervalued vs potential.
    Crypto translation: find the coin with best risk/reward and HOLD WITH CONVICTION.
    """
    NAME = "Ackman_Conviction"

    def run(self) -> SupertraderResult:
        data = _get_prices("bitcoin,ethereum,solana,chainlink,near")
        
        universe = {
            "BTC/USDT":  {"24h": data.get("bitcoin",   {}).get("usd_24h_change", 0),
                          "7d":  data.get("bitcoin",   {}).get("usd_7d_change", 0),
                          "mcap":data.get("bitcoin",   {}).get("usd_market_cap", 0)},
            "ETH/USDT":  {"24h": data.get("ethereum",  {}).get("usd_24h_change", 0),
                          "7d":  data.get("ethereum",  {}).get("usd_7d_change", 0),
                          "mcap":data.get("ethereum",  {}).get("usd_market_cap", 0)},
            "SOL/USDT":  {"24h": data.get("solana",    {}).get("usd_24h_change", 0),
                          "7d":  data.get("solana",    {}).get("usd_7d_change", 0),
                          "mcap":data.get("solana",    {}).get("usd_market_cap", 0)},
            "LINK/USDT": {"24h": data.get("chainlink", {}).get("usd_24h_change", 0),
                          "7d":  data.get("chainlink", {}).get("usd_7d_change", 0),
                          "mcap":data.get("chainlink", {}).get("usd_market_cap", 0)},
            "NEAR/USDT": {"24h": data.get("near",      {}).get("usd_24h_change", 0),
                          "7d":  data.get("near",      {}).get("usd_7d_change", 0),
                          "mcap":data.get("near",      {}).get("usd_market_cap", 0)},
        }

        # Ackman score: positive 7d momentum + small pullback 24h = best entry
        scores = {}
        for sym, d in universe.items():
            # Prefer: good 7d trend, today's dip (opportunity), reasonable mcap
            score = d["7d"] * 1.5 + max(0, -d["24h"]) * 2
            scores[sym] = score

        best_sym = max(scores, key=scores.get)
        best_data = universe[best_sym]
        best_score = scores[best_sym]

        if best_data["7d"] > 5 and best_score > 5:
            direction = "LONG"
            conviction = min(88, 55 + best_score)
            reasoning = (f"ACKMAN CONVICTION: {best_sym} is THE trade. "
                         f"7d momentum: {best_data['7d']:+.1f}%, 24h: {best_data['24h']:+.1f}%. "
                         f"Strong fundamentals + current dip = perfect entry. "
                         f"Market cap ${best_data['mcap']/1e9:.1f}B — liquid enough for conviction sizing. "
                         f"This is not diversification. THIS IS THE POSITION.")
            risk = f"Stop at -3% from entry. If thesis breaks (BTC macro turns), EXIT COMPLETELY."
        else:
            direction = "WAIT"
            conviction = 35
            best_sym = "NONE"
            reasoning = ("ACKMAN: No high-conviction setup right now. "
                         "Ackman's rule: better to do nothing than force a mediocre trade. "
                         "Waiting for a market dislocation or strong catalyst.")
            risk = "Holding cash IS a position. Wait for asymmetric risk/reward."

        return SupertraderResult(self.NAME, conviction, best_sym, direction, reasoning, risk)


# ─────────────────────────────────────────────────────────────
# Supertrader Layer Synthesizer
# ─────────────────────────────────────────────────────────────
ALL_SUPERTRADER_AGENTS = [
    DruckenmillerCryptoAgent,
    SorosReflexivityAgent,
    SimonsQuantAgent,
    AckmanConvictionAgent,
]


def run_supertrader_layer(agent_weights: dict = None) -> dict:
    weights = agent_weights or {}
    results = []
    errors = []

    for AgentClass in ALL_SUPERTRADER_AGENTS:
        try:
            result = AgentClass().run()
            w = weights.get(result.agent, 1.0)
            results.append({"result": result, "weight": w})
            time.sleep(0.5)
        except Exception as e:
            log.warning("Supertrader agent %s failed: %s", AgentClass.NAME, e)
            errors.append(AgentClass.NAME)

    # Weighted conviction vote
    long_score  = sum(r["result"].conviction * r["weight"] for r in results if r["result"].direction == "LONG")
    short_score = sum(r["result"].conviction * r["weight"] for r in results if r["result"].direction == "SHORT")
    wait_score  = sum(r["result"].conviction * r["weight"] for r in results if r["result"].direction in ("WAIT", "NEUTRAL"))

    if long_score > short_score and long_score > wait_score:
        consensus = "LONG"
    elif short_score > long_score and short_score > wait_score:
        consensus = "SHORT"
    else:
        consensus = "WAIT"

    # Find highest conviction trade
    long_results = [r for r in results if r["result"].direction == "LONG"]
    top_pick = max(long_results, key=lambda r: r["result"].conviction * r["weight"]) if long_results else None

    return {
        "supertrader_consensus": consensus,
        "top_conviction_trade": top_pick["result"].top_trade if top_pick else "NONE",
        "top_conviction_agent": top_pick["result"].agent if top_pick else "NONE",
        "agents": [r["result"].to_dict() for r in results],
        "errors": errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(run_supertrader_layer(), indent=2))
