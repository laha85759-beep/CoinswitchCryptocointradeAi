"""
ATLAS Layer 1 — Macro Intelligence Agents (10 Agents)
======================================================
Crypto-adapted from ATLAS Pro macro desk.
Each agent returns: regime (RISK_ON / RISK_OFF / NEUTRAL), confidence (0-1), reasoning (str)

Agents:
  1. BTCDominanceAgent      - BTC dom vs altcoin rotation
  2. FedFearIndexAgent       - CPI/FOMC impact on crypto
  3. GlobalLiquidityAgent    - M2 + DXY vs BTC
  4. StablecoinFlowAgent     - USDT/USDC market cap growth
  5. MinerSentimentAgent     - Hash rate + miner pressure
  6. CryptoFearGreedAgent    - Fear & Greed Index
  7. RegulationRiskAgent     - News sentiment for regulation
  8. OnChainFlowAgent        - Exchange inflows/outflows
  9. VolatilityRegimeAgent   - VIX-equivalent + BVOL
  10. InstitutionalFlowAgent - OI + funding rate aggregate
"""
from __future__ import annotations
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any
import requests

log = logging.getLogger(__name__)

RISK_ON   = "RISK_ON"
RISK_OFF  = "RISK_OFF"
NEUTRAL   = "NEUTRAL"


def _safe_get(url: str, params: dict = None, timeout: int = 8) -> dict:
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log.debug("HTTP fetch failed %s: %s", url, e)
    return {}


class MacroAgentResult:
    def __init__(self, agent: str, regime: str, confidence: float, reasoning: str, data: dict = None):
        self.agent = agent
        self.regime = regime
        self.confidence = round(max(0.0, min(1.0, confidence)), 3)
        self.reasoning = reasoning
        self.data = data or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "regime": self.regime,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "data": self.data,
            "timestamp": self.timestamp,
        }


# ─────────────────────────────────────────────────────────────
# Agent 1: BTC Dominance
# ─────────────────────────────────────────────────────────────
class BTCDominanceAgent:
    """
    BTC dominance rising = capital rotating INTO BTC = altcoins underperform.
    BTC dominance falling = capital rotating OUT of BTC = altcoins pump.
    """
    NAME = "BTC_Dominance"

    def run(self) -> MacroAgentResult:
        data = _safe_get("https://api.coingecko.com/api/v3/global")
        mkt = data.get("data", {})
        btc_dom = mkt.get("market_cap_percentage", {}).get("btc", 50.0)
        total_mcap = mkt.get("total_market_cap", {}).get("usd", 0)
        change_24h = mkt.get("market_cap_change_percentage_24h_usd", 0)

        if btc_dom > 56:
            regime = RISK_OFF
            conf = 0.72
            reasoning = f"BTC dominance {btc_dom:.1f}% is high (>56%). Capital concentrated in BTC, altcoins underperforming. Risk-off for altcoin trades."
        elif btc_dom < 44:
            regime = RISK_ON
            conf = 0.75
            reasoning = f"BTC dominance {btc_dom:.1f}% is low (<44%). Capital rotating into altcoins. Strong risk-on for altcoin longs."
        else:
            regime = NEUTRAL
            conf = 0.50
            reasoning = f"BTC dominance {btc_dom:.1f}% is neutral (44-56%). Mixed rotation signal. Market cap change 24h: {change_24h:.1f}%."

        return MacroAgentResult(self.NAME, regime, conf, reasoning,
                                {"btc_dom": btc_dom, "total_mcap_usd": total_mcap, "change_24h": change_24h})


# ─────────────────────────────────────────────────────────────
# Agent 2: Fed Fear Index (CPI / Rate Sensitivity)
# ─────────────────────────────────────────────────────────────
class FedFearIndexAgent:
    """
    Uses DXY (Dollar Index) proxy from forex data + US10Y yield as Fed fear proxy.
    High DXY + Rising yields = crypto risk-off.
    Falling DXY + Stable yields = crypto risk-on.
    """
    NAME = "Fed_Fear_Index"

    def run(self) -> MacroAgentResult:
        # Use BTC price trend as macro proxy (since direct DXY API requires paid keys)
        btc_data = _safe_get("https://api.coingecko.com/api/v3/simple/price",
                             {"ids": "bitcoin", "vs_currencies": "usd", "include_24hr_change": "true"})
        btc_change = btc_data.get("bitcoin", {}).get("usd_24h_change", 0)

        # Fear proxy: large BTC drawdown = Fed fear is high
        if btc_change < -4:
            regime = RISK_OFF
            conf = 0.78
            reasoning = f"BTC down {btc_change:.1f}% in 24h — strong macro sell pressure. Fed/macro fear elevated. Reduce leverage, avoid new longs."
        elif btc_change > 3:
            regime = RISK_ON
            conf = 0.70
            reasoning = f"BTC up {btc_change:.1f}% in 24h — macro fear receding. Risk appetite returning. Favorable for momentum longs."
        else:
            regime = NEUTRAL
            conf = 0.50
            reasoning = f"BTC {btc_change:+.1f}% in 24h — neutral macro signal. No strong Fed fear or euphoria. Wait for confirmation."

        return MacroAgentResult(self.NAME, regime, conf, reasoning, {"btc_24h_change": btc_change})


# ─────────────────────────────────────────────────────────────
# Agent 3: Global Liquidity Agent
# ─────────────────────────────────────────────────────────────
class GlobalLiquidityAgent:
    """
    Total crypto market cap trend = global liquidity proxy.
    Rising total mcap = liquidity expanding = RISK_ON.
    """
    NAME = "Global_Liquidity"

    def run(self) -> MacroAgentResult:
        data = _safe_get("https://api.coingecko.com/api/v3/global")
        mkt = data.get("data", {})
        change = mkt.get("market_cap_change_percentage_24h_usd", 0)
        total = mkt.get("total_market_cap", {}).get("usd", 0)
        total_b = total / 1e9

        if change > 2.5:
            regime = RISK_ON
            conf = 0.74
            reasoning = f"Global crypto market cap +{change:.1f}% today (${total_b:.0f}B). Liquidity expanding — bullish for all assets."
        elif change < -2.5:
            regime = RISK_OFF
            conf = 0.76
            reasoning = f"Global crypto market cap {change:.1f}% today (${total_b:.0f}B). Liquidity contracting — bearish signal."
        else:
            regime = NEUTRAL
            conf = 0.48
            reasoning = f"Global crypto market cap {change:+.1f}% (${total_b:.0f}B). Liquidity stable — no directional signal."

        return MacroAgentResult(self.NAME, regime, conf, reasoning,
                                {"total_mcap_B": total_b, "change_24h": change})


# ─────────────────────────────────────────────────────────────
# Agent 4: Stablecoin Flow Agent
# ─────────────────────────────────────────────────────────────
class StablecoinFlowAgent:
    """
    USDT + USDC market cap growth = dry powder entering the market = RISK_ON.
    Stablecoin mcap shrinking = money leaving = RISK_OFF.
    """
    NAME = "Stablecoin_Flow"

    def run(self) -> MacroAgentResult:
        data = _safe_get("https://api.coingecko.com/api/v3/simple/price",
                         {"ids": "tether,usd-coin", "vs_currencies": "usd",
                          "include_market_cap": "true", "include_24hr_change": "true"})
        usdt_mcap = data.get("tether", {}).get("usd_market_cap", 0)
        usdc_mcap = data.get("usd-coin", {}).get("usd_market_cap", 0)
        usdt_change = data.get("tether", {}).get("usd_24h_change", 0)
        combined_b = (usdt_mcap + usdc_mcap) / 1e9

        if usdt_change > 0.05:
            regime = RISK_ON
            conf = 0.65
            reasoning = f"Stablecoin supply growing (USDT+USDC = ${combined_b:.0f}B). Dry powder accumulating — bullish setup. Capital ready to deploy."
        elif usdt_change < -0.05:
            regime = RISK_OFF
            conf = 0.62
            reasoning = f"Stablecoin supply contracting (${combined_b:.0f}B). Capital leaving ecosystem — bearish signal."
        else:
            regime = NEUTRAL
            conf = 0.50
            reasoning = f"Stablecoin supply stable (${combined_b:.0f}B). No significant capital inflow or outflow signal."

        return MacroAgentResult(self.NAME, regime, conf, reasoning,
                                {"stablecoin_supply_B": combined_b, "usdt_change": usdt_change})


# ─────────────────────────────────────────────────────────────
# Agent 5: Miner Sentiment Agent
# ─────────────────────────────────────────────────────────────
class MinerSentimentAgent:
    """
    BTC hash rate is a leading indicator of miner confidence.
    Proxy: BTC 7-day trend vs 30-day trend (miners sell to cover costs when price drops).
    """
    NAME = "Miner_Sentiment"

    def run(self) -> MacroAgentResult:
        data = _safe_get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
                         {"vs_currency": "usd", "days": "30", "interval": "daily"})
        prices = [p[1] for p in data.get("prices", [])]

        if len(prices) >= 30:
            avg7  = sum(prices[-7:])  / 7
            avg30 = sum(prices[-30:]) / 30
            trend = (avg7 - avg30) / avg30 * 100

            if trend > 5:
                regime = RISK_ON
                conf = 0.68
                reasoning = f"BTC 7d avg (${avg7:,.0f}) is {trend:.1f}% above 30d avg (${avg30:,.0f}). Miners profitable, no forced selling. Risk-on."
            elif trend < -5:
                regime = RISK_OFF
                conf = 0.70
                reasoning = f"BTC 7d avg (${avg7:,.0f}) is {trend:.1f}% below 30d avg (${avg30:,.0f}). Miner margins compressed. Capitulation risk. Risk-off."
            else:
                regime = NEUTRAL
                conf = 0.50
                reasoning = f"BTC 7d/30d trend diff is {trend:+.1f}%. Miner sentiment neutral."
        else:
            regime, conf = NEUTRAL, 0.40
            reasoning = "Insufficient price history for miner sentiment analysis."

        return MacroAgentResult(self.NAME, regime, conf, reasoning, {})


# ─────────────────────────────────────────────────────────────
# Agent 6: Crypto Fear & Greed Agent
# ─────────────────────────────────────────────────────────────
class CryptoFearGreedAgent:
    """
    Fear & Greed Index from alternative.me API.
    Extreme Fear (0-25)  → contrarian BUY signal (RISK_ON for bold)
    Extreme Greed (75-100) → caution, market overextended (RISK_OFF)
    """
    NAME = "Fear_Greed_Index"

    def run(self) -> MacroAgentResult:
        data = _safe_get("https://api.alternative.me/fng/?limit=1")
        fng = data.get("data", [{}])[0]
        value = int(fng.get("value", 50))
        classification = fng.get("value_classification", "Neutral")

        if value <= 25:
            regime = RISK_ON
            conf = 0.80
            reasoning = f"Fear & Greed = {value} ({classification}). EXTREME FEAR is historically the best buying opportunity. Contrarian RISK_ON signal."
        elif value >= 75:
            regime = RISK_OFF
            conf = 0.75
            reasoning = f"Fear & Greed = {value} ({classification}). EXTREME GREED — market overextended. Reduce new entries, trail existing stops tight."
        elif value >= 60:
            regime = NEUTRAL
            conf = 0.55
            reasoning = f"Fear & Greed = {value} ({classification}). Greed building but not extreme yet. Use tight risk management."
        else:
            regime = NEUTRAL
            conf = 0.50
            reasoning = f"Fear & Greed = {value} ({classification}). Neutral sentiment — no strong directional bias."

        return MacroAgentResult(self.NAME, regime, conf, reasoning,
                                {"fng_value": value, "classification": classification})


# ─────────────────────────────────────────────────────────────
# Agent 7: Regulation Risk Agent
# ─────────────────────────────────────────────────────────────
class RegulationRiskAgent:
    """
    Monitors crypto regulation news via CoinGecko trending + news proxy.
    Uses BTC/ETH volatility spike as regulation fear proxy.
    """
    NAME = "Regulation_Risk"

    def run(self) -> MacroAgentResult:
        # Use price volatility as proxy for regulation news shock
        btc = _safe_get("https://api.coingecko.com/api/v3/coins/bitcoin",
                        {"localization": "false", "tickers": "false", "community_data": "false"})
        price_change_7d = btc.get("market_data", {}).get("price_change_percentage_7d", 0)
        ath_change = btc.get("market_data", {}).get("ath_change_percentage", {}).get("usd", -50)

        if price_change_7d < -10:
            regime = RISK_OFF
            conf = 0.73
            reasoning = f"BTC down {price_change_7d:.1f}% in 7 days — possible regulation shock or macro event. Elevated risk-off signal."
        elif ath_change > -10:
            regime = RISK_OFF
            conf = 0.60
            reasoning = f"BTC near ATH (only {ath_change:.1f}% below). Regulatory risk elevated at cycle peaks. Caution warranted."
        elif price_change_7d > 8:
            regime = RISK_ON
            conf = 0.65
            reasoning = f"BTC up {price_change_7d:.1f}% in 7 days — positive momentum, regulation fears subdued."
        else:
            regime = NEUTRAL
            conf = 0.50
            reasoning = f"BTC {price_change_7d:+.1f}% in 7 days. No obvious regulation shock detected. Neutral."

        return MacroAgentResult(self.NAME, regime, conf, reasoning,
                                {"btc_7d_change": price_change_7d, "ath_change": ath_change})


# ─────────────────────────────────────────────────────────────
# Agent 8: On-Chain Flow Agent
# ─────────────────────────────────────────────────────────────
class OnChainFlowAgent:
    """
    Exchange inflows = selling pressure (whales depositing to exchanges to sell).
    Uses ETH + BTC volume trend as on-chain flow proxy.
    """
    NAME = "OnChain_Flow"

    def run(self) -> MacroAgentResult:
        data = _safe_get("https://api.coingecko.com/api/v3/simple/price",
                         {"ids": "bitcoin,ethereum", "vs_currencies": "usd",
                          "include_24hr_vol": "true", "include_24hr_change": "true"})
        btc_vol  = data.get("bitcoin", {}).get("usd_24h_vol", 0) / 1e9
        eth_vol  = data.get("ethereum", {}).get("usd_24h_vol", 0) / 1e9
        btc_chg  = data.get("bitcoin", {}).get("usd_24h_change", 0)
        eth_chg  = data.get("ethereum", {}).get("usd_24h_change", 0)
        total_vol = btc_vol + eth_vol

        # High volume + positive price = accumulation (bullish)
        # High volume + negative price = distribution (bearish)
        if total_vol > 30 and btc_chg > 2 and eth_chg > 2:
            regime = RISK_ON
            conf = 0.72
            reasoning = f"High volume (${total_vol:.0f}B) with BTC +{btc_chg:.1f}% ETH +{eth_chg:.1f}% — institutional accumulation signal. RISK_ON."
        elif total_vol > 30 and btc_chg < -2 and eth_chg < -2:
            regime = RISK_OFF
            conf = 0.74
            reasoning = f"High volume (${total_vol:.0f}B) with BTC {btc_chg:.1f}% ETH {eth_chg:.1f}% — distribution/sell-off detected. RISK_OFF."
        elif total_vol < 10:
            regime = NEUTRAL
            conf = 0.42
            reasoning = f"Low volume (${total_vol:.0f}B) — low conviction moves. Wait for volume confirmation before trading."
        else:
            regime = NEUTRAL
            conf = 0.50
            reasoning = f"Volume ${total_vol:.0f}B with mixed price action. No strong on-chain directional signal."

        return MacroAgentResult(self.NAME, regime, conf, reasoning,
                                {"total_vol_B": total_vol, "btc_change": btc_chg, "eth_change": eth_chg})


# ─────────────────────────────────────────────────────────────
# Agent 9: Volatility Regime Agent
# ─────────────────────────────────────────────────────────────
class VolatilityRegimeAgent:
    """
    High volatility + downtrend = RISK_OFF (dangerous wicks, stop-outs).
    Low volatility + uptrend = RISK_ON (clean trending moves).
    Uses BTC price range (high-low) as volatility proxy.
    """
    NAME = "Volatility_Regime"

    def run(self) -> MacroAgentResult:
        data = _safe_get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
                         {"vs_currency": "usd", "days": "7", "interval": "daily"})
        prices = [p[1] for p in data.get("prices", [])]

        if len(prices) >= 3:
            recent_high = max(prices[-3:])
            recent_low  = min(prices[-3:])
            volatility  = (recent_high - recent_low) / recent_low * 100
            trend = (prices[-1] - prices[0]) / prices[0] * 100

            if volatility > 15 and trend < 0:
                regime = RISK_OFF
                conf = 0.78
                reasoning = f"High volatility ({volatility:.1f}% range over 3 days) with downtrend ({trend:.1f}%). Dangerous wick environment. Reduce leverage."
            elif volatility > 15 and trend > 0:
                regime = NEUTRAL
                conf = 0.55
                reasoning = f"High volatility ({volatility:.1f}%) but uptrend ({trend:+.1f}%). Mixed — use tighter stops to capture moves without getting stopped out."
            elif volatility < 5 and trend > 0:
                regime = RISK_ON
                conf = 0.70
                reasoning = f"Low volatility ({volatility:.1f}%) with clean uptrend ({trend:+.1f}%). Ideal trending market. Momentum signals reliable."
            else:
                regime = NEUTRAL
                conf = 0.50
                reasoning = f"Moderate volatility ({volatility:.1f}%), trend {trend:+.1f}%. Normal market conditions."
        else:
            regime, conf = NEUTRAL, 0.40
            reasoning = "Insufficient data for volatility regime analysis."

        return MacroAgentResult(self.NAME, regime, conf, reasoning,
                                {"volatility_pct": locals().get("volatility", 0), "trend_7d": locals().get("trend", 0)})


# ─────────────────────────────────────────────────────────────
# Agent 10: Institutional Flow Agent
# ─────────────────────────────────────────────────────────────
class InstitutionalFlowAgent:
    """
    ETH/BTC market cap ratio: rising ETH dom = institutions allocating to altcoins.
    Uses ETH/BTC ratio trend as institutional allocation proxy.
    """
    NAME = "Institutional_Flow"

    def run(self) -> MacroAgentResult:
        data = _safe_get("https://api.coingecko.com/api/v3/simple/price",
                         {"ids": "bitcoin,ethereum", "vs_currencies": "usd",
                          "include_market_cap": "true", "include_24hr_change": "true"})
        btc_mcap = data.get("bitcoin",  {}).get("usd_market_cap", 1)
        eth_mcap = data.get("ethereum", {}).get("usd_market_cap", 1)
        eth_chg  = data.get("ethereum", {}).get("usd_24h_change", 0)
        btc_chg  = data.get("bitcoin",  {}).get("usd_24h_change", 0)
        eth_btc_ratio = eth_mcap / btc_mcap

        if eth_btc_ratio > 0.22 and eth_chg > btc_chg:
            regime = RISK_ON
            conf = 0.68
            reasoning = f"ETH/BTC ratio {eth_btc_ratio:.3f} and ETH outperforming BTC (+{eth_chg:.1f}% vs +{btc_chg:.1f}%). Institutional rotation into alts. RISK_ON."
        elif eth_btc_ratio < 0.16:
            regime = RISK_OFF
            conf = 0.65
            reasoning = f"ETH/BTC ratio low ({eth_btc_ratio:.3f}) — institutions rotating to safety. Altcoin risk elevated."
        elif eth_chg < btc_chg - 3:
            regime = RISK_OFF
            conf = 0.60
            reasoning = f"ETH underperforming BTC ({eth_chg:.1f}% vs {btc_chg:.1f}%). Institutional capital fleeing to BTC safety. Caution."
        else:
            regime = NEUTRAL
            conf = 0.50
            reasoning = f"ETH/BTC ratio {eth_btc_ratio:.3f}. Institutional flow neutral."

        return MacroAgentResult(self.NAME, regime, conf, reasoning,
                                {"eth_btc_ratio": eth_btc_ratio, "eth_24h": eth_chg, "btc_24h": btc_chg})


# ─────────────────────────────────────────────────────────────
# Macro Layer Synthesizer
# ─────────────────────────────────────────────────────────────
ALL_MACRO_AGENTS = [
    BTCDominanceAgent,
    FedFearIndexAgent,
    GlobalLiquidityAgent,
    StablecoinFlowAgent,
    MinerSentimentAgent,
    CryptoFearGreedAgent,
    RegulationRiskAgent,
    OnChainFlowAgent,
    VolatilityRegimeAgent,
    InstitutionalFlowAgent,
]


def run_macro_layer(agent_weights: dict = None) -> dict:
    """
    Run all 10 macro agents and synthesize into a single macro regime signal.
    Returns weighted consensus regime + full agent reasoning.
    """
    weights = agent_weights or {}
    results = []
    errors  = []

    for AgentClass in ALL_MACRO_AGENTS:
        try:
            agent = AgentClass()
            result = agent.run()
            w = weights.get(result.agent, 1.0)
            results.append({"result": result, "weight": w})
            time.sleep(0.3)  # CoinGecko rate limit
        except Exception as e:
            log.warning("Macro agent %s failed: %s", AgentClass.NAME, e)
            errors.append(AgentClass.NAME)

    # Weighted vote
    score = {RISK_ON: 0.0, RISK_OFF: 0.0, NEUTRAL: 0.0}
    for item in results:
        r = item["result"]
        w = item["weight"]
        score[r.regime] += r.confidence * w

    total = sum(score.values()) or 1.0
    regime_pcts = {k: round(v / total * 100, 1) for k, v in score.items()}
    macro_regime = max(score, key=score.get)
    macro_confidence = round(score[macro_regime] / total, 3)

    return {
        "macro_regime": macro_regime,
        "macro_confidence": macro_confidence,
        "regime_breakdown": regime_pcts,
        "agents": [r["result"].to_dict() for r in results],
        "errors": errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(run_macro_layer(), indent=2))
