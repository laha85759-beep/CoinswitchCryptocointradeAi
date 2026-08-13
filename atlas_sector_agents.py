"""
ATLAS Layer 2 — Sector Desk Agents (7 Agents)
==============================================
Crypto sector rotation detection.
Each agent scores a sector 0-100 and identifies top picks within that sector.

Agents:
  1. L1BlueChipsAgent    - BTC, ETH, SOL momentum
  2. DeFiDeskAgent       - LINK, UNI, AAVE sector
  3. AITokenDeskAgent    - WIF, PEPE, DOGE meme/AI tokens
  4. RWADeskAgent        - ONDO, TON real-world assets
  5. InfraDeskAgent      - MATIC, AVAX, DOT infra chains
  6. GamingDeskAgent     - Gaming/metaverse tokens
  7. RelationshipMapper  - Cross-pair correlation & sector rotation
"""
from __future__ import annotations
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Any
import requests

log = logging.getLogger(__name__)


def _price_data(coin_ids: str) -> dict:
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coin_ids, "vs_currencies": "usd",
                    "include_24hr_change": "true", "include_7d_change": "true"},
            timeout=10
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log.debug("Price fetch failed: %s", e)
    return {}


class SectorResult:
    def __init__(self, agent: str, sector_score: float, top_picks: List[str],
                 bias: str, reasoning: str, data: dict = None):
        self.agent = agent
        self.sector_score = round(max(0, min(100, sector_score)), 1)
        self.top_picks = top_picks
        self.bias = bias  # BULLISH / BEARISH / NEUTRAL
        self.reasoning = reasoning
        self.data = data or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "sector_score": self.sector_score,
            "top_picks": self.top_picks,
            "bias": self.bias,
            "reasoning": self.reasoning,
            "data": self.data,
            "timestamp": self.timestamp,
        }


# ─────────────────────────────────────────────────────────────
# Agent 1: L1 Blue Chips
# ─────────────────────────────────────────────────────────────
class L1BlueChipsAgent:
    NAME = "L1_BlueChips"
    COINS = "bitcoin,ethereum,solana"

    def run(self) -> SectorResult:
        data = _price_data(self.COINS)
        btc_c = data.get("bitcoin",  {}).get("usd_24h_change", 0)
        eth_c = data.get("ethereum", {}).get("usd_24h_change", 0)
        sol_c = data.get("solana",   {}).get("usd_24h_change", 0)
        avg = (btc_c + eth_c + sol_c) / 3
        picks = []
        if sol_c > btc_c and sol_c > eth_c: picks.append("SOL/USDT")
        if eth_c > btc_c: picks.append("ETH/USDT")
        picks.append("BTC/USDT")

        score = 50 + avg * 4
        bias = "BULLISH" if avg > 1 else "BEARISH" if avg < -1 else "NEUTRAL"
        reasoning = (f"BTC {btc_c:+.1f}% | ETH {eth_c:+.1f}% | SOL {sol_c:+.1f}%. "
                     f"Avg {avg:+.1f}%. L1 sector is {bias}. "
                     f"Best performer: {picks[0] if picks else 'None'}.")
        return SectorResult(self.NAME, score, picks[:2], bias, reasoning,
                            {"btc": btc_c, "eth": eth_c, "sol": sol_c})


# ─────────────────────────────────────────────────────────────
# Agent 2: DeFi Desk
# ─────────────────────────────────────────────────────────────
class DeFiDeskAgent:
    NAME = "DeFi_Desk"
    COINS = "chainlink,uniswap,aave,curve-dao-token,maker"

    def run(self) -> SectorResult:
        data = _price_data(self.COINS)
        changes = {
            "LINK/USDT": data.get("chainlink",       {}).get("usd_24h_change", 0),
            "UNI/USDT":  data.get("uniswap",         {}).get("usd_24h_change", 0),
            "AAVE/USDT": data.get("aave",             {}).get("usd_24h_change", 0),
            "CRV/USDT":  data.get("curve-dao-token",  {}).get("usd_24h_change", 0),
            "MKR/USDT":  data.get("maker",            {}).get("usd_24h_change", 0),
        }
        avg = sum(changes.values()) / len(changes) if changes else 0
        picks = sorted(changes, key=changes.get, reverse=True)[:2]
        bias = "BULLISH" if avg > 1.5 else "BEARISH" if avg < -1.5 else "NEUTRAL"
        score = 50 + avg * 3
        top_str = " | ".join(f"{k} {v:+.1f}%" for k, v in list(changes.items())[:3])
        reasoning = f"DeFi sector avg {avg:+.1f}%. {top_str}. Sector is {bias}."
        return SectorResult(self.NAME, score, picks, bias, reasoning, {"changes": changes})


# ─────────────────────────────────────────────────────────────
# Agent 3: AI / Meme Token Desk
# ─────────────────────────────────────────────────────────────
class AITokenDeskAgent:
    NAME = "AI_Meme_Desk"
    COINS = "dogwifcoin,pepe,dogecoin,shiba-inu,floki"

    def run(self) -> SectorResult:
        data = _price_data(self.COINS)
        changes = {
            "WIF/USDT":  data.get("dogwifcoin",  {}).get("usd_24h_change", 0),
            "PEPE/USDT": data.get("pepe",         {}).get("usd_24h_change", 0),
            "DOGE/USDT": data.get("dogecoin",     {}).get("usd_24h_change", 0),
            "SHIB/USDT": data.get("shiba-inu",    {}).get("usd_24h_change", 0),
            "FLOKI/USDT":data.get("floki",        {}).get("usd_24h_change", 0),
        }
        avg = sum(changes.values()) / len(changes) if changes else 0
        picks = sorted(changes, key=changes.get, reverse=True)[:2]
        bias = "BULLISH" if avg > 3 else "BEARISH" if avg < -3 else "NEUTRAL"
        score = 50 + avg * 2.5

        # Meme tokens need stronger signal threshold
        if avg > 5:
            reasoning = f"MEME SECTOR HOT: avg +{avg:.1f}%. Momentum trade opportunity. Best: {picks[0]}."
        elif avg < -5:
            reasoning = f"MEME SECTOR DUMPING: avg {avg:.1f}%. Avoid or short. Weakest: {picks[-1] if picks else '?'}."
        else:
            reasoning = f"Meme/AI token sector avg {avg:+.1f}%. No extreme signal. Top pick: {picks[0] if picks else 'None'}."

        return SectorResult(self.NAME, score, picks, bias, reasoning, {"changes": changes})


# ─────────────────────────────────────────────────────────────
# Agent 4: Real World Assets (RWA) Desk
# ─────────────────────────────────────────────────────────────
class RWADeskAgent:
    NAME = "RWA_Desk"
    COINS = "ondo-finance,the-open-network,centrifuge,maple"

    def run(self) -> SectorResult:
        data = _price_data(self.COINS)
        changes = {
            "ONDO/USDT": data.get("ondo-finance",      {}).get("usd_24h_change", 0),
            "TON/USDT":  data.get("the-open-network",  {}).get("usd_24h_change", 0),
            "CFG/USDT":  data.get("centrifuge",        {}).get("usd_24h_change", 0),
        }
        avg = sum(changes.values()) / len(changes) if changes else 0
        picks = sorted(changes, key=changes.get, reverse=True)[:2]
        bias = "BULLISH" if avg > 1 else "BEARISH" if avg < -1 else "NEUTRAL"
        score = 50 + avg * 4
        reasoning = (f"RWA sector avg {avg:+.1f}%. ONDO {changes.get('ONDO/USDT', 0):+.1f}%, "
                     f"TON {changes.get('TON/USDT', 0):+.1f}%. "
                     f"RWA sector is {bias} — institutional tokenisation trend.")
        return SectorResult(self.NAME, score, picks, bias, reasoning, {"changes": changes})


# ─────────────────────────────────────────────────────────────
# Agent 5: Infrastructure Chains Desk
# ─────────────────────────────────────────────────────────────
class InfraDeskAgent:
    NAME = "Infra_Chains_Desk"
    COINS = "matic-network,avalanche-2,polkadot,cosmos,near"

    def run(self) -> SectorResult:
        data = _price_data(self.COINS)
        changes = {
            "MATIC/USDT": data.get("matic-network",  {}).get("usd_24h_change", 0),
            "AVAX/USDT":  data.get("avalanche-2",    {}).get("usd_24h_change", 0),
            "DOT/USDT":   data.get("polkadot",       {}).get("usd_24h_change", 0),
            "ATOM/USDT":  data.get("cosmos",         {}).get("usd_24h_change", 0),
            "NEAR/USDT":  data.get("near",           {}).get("usd_24h_change", 0),
        }
        avg = sum(changes.values()) / len(changes) if changes else 0
        picks = sorted(changes, key=changes.get, reverse=True)[:2]
        bias = "BULLISH" if avg > 1.5 else "BEARISH" if avg < -1.5 else "NEUTRAL"
        score = 50 + avg * 3
        reasoning = f"Infra chains avg {avg:+.1f}%. Top: {picks[0] if picks else 'None'}. Sector {bias}."
        return SectorResult(self.NAME, score, picks, bias, reasoning, {"changes": changes})


# ─────────────────────────────────────────────────────────────
# Agent 6: Gaming Desk
# ─────────────────────────────────────────────────────────────
class GamingDeskAgent:
    NAME = "Gaming_Desk"
    COINS = "axie-infinity,immutable-x,gala,the-sandbox,decentraland"

    def run(self) -> SectorResult:
        data = _price_data(self.COINS)
        changes = {
            "AXS/USDT":  data.get("axie-infinity",  {}).get("usd_24h_change", 0),
            "IMX/USDT":  data.get("immutable-x",    {}).get("usd_24h_change", 0),
            "GALA/USDT": data.get("gala",           {}).get("usd_24h_change", 0),
            "SAND/USDT": data.get("the-sandbox",    {}).get("usd_24h_change", 0),
        }
        avg = sum(changes.values()) / len(changes) if changes else 0
        picks = sorted(changes, key=changes.get, reverse=True)[:2]
        bias = "BULLISH" if avg > 2 else "BEARISH" if avg < -2 else "NEUTRAL"
        score = 50 + avg * 2.5
        reasoning = f"Gaming/Metaverse sector avg {avg:+.1f}%. Best: {picks[0] if picks else 'None'}. Sector {bias}."
        return SectorResult(self.NAME, score, picks, bias, reasoning, {"changes": changes})


# ─────────────────────────────────────────────────────────────
# Agent 7: Relationship Mapper (cross-pair correlation)
# ─────────────────────────────────────────────────────────────
class RelationshipMapperAgent:
    NAME = "Relationship_Mapper"

    def run(self) -> SectorResult:
        """
        Detects which sector is leading vs lagging.
        Identifies cross-pair correlation patterns.
        """
        data = _price_data("bitcoin,ethereum,solana,chainlink,dogecoin,ondo-finance,matic-network")
        changes = {
            "BTC": data.get("bitcoin",         {}).get("usd_24h_change", 0),
            "ETH": data.get("ethereum",        {}).get("usd_24h_change", 0),
            "SOL": data.get("solana",          {}).get("usd_24h_change", 0),
            "LINK": data.get("chainlink",      {}).get("usd_24h_change", 0),
            "DOGE": data.get("dogecoin",       {}).get("usd_24h_change", 0),
            "ONDO": data.get("ondo-finance",   {}).get("usd_24h_change", 0),
            "MATIC": data.get("matic-network", {}).get("usd_24h_change", 0),
        }
        # Find biggest outperformers vs BTC
        btc_chg = changes.get("BTC", 0)
        outperformers = {k: v - btc_chg for k, v in changes.items() if k != "BTC" and v - btc_chg > 2}
        underperformers = {k: v - btc_chg for k, v in changes.items() if k != "BTC" and v - btc_chg < -2}

        picks = [f"{k}/USDT" for k in sorted(outperformers, key=outperformers.get, reverse=True)[:2]]
        bias = "BULLISH" if len(outperformers) > len(underperformers) else "BEARISH" if underperformers else "NEUTRAL"
        score = 50 + (len(outperformers) - len(underperformers)) * 8

        out_str = ", ".join(f"{k} +{v:.1f}% vs BTC" for k, v in list(outperformers.items())[:3])
        reasoning = (f"Outperformers vs BTC: {out_str or 'none'}. "
                     f"Underperformers: {len(underperformers)}. Rotation signal: {bias}. "
                     f"When altcoins outperform BTC = strong alt season confirmation.")

        return SectorResult(self.NAME, score, picks or ["BTC/USDT"], bias, reasoning, {"changes": changes})


# ─────────────────────────────────────────────────────────────
# Sector Layer Synthesizer
# ─────────────────────────────────────────────────────────────
ALL_SECTOR_AGENTS = [
    L1BlueChipsAgent,
    DeFiDeskAgent,
    AITokenDeskAgent,
    RWADeskAgent,
    InfraDeskAgent,
    GamingDeskAgent,
    RelationshipMapperAgent,
]


def run_sector_layer(agent_weights: dict = None) -> dict:
    weights = agent_weights or {}
    results = []
    errors = []

    for AgentClass in ALL_SECTOR_AGENTS:
        try:
            result = AgentClass().run()
            w = weights.get(result.agent, 1.0)
            results.append({"result": result, "weight": w})
            time.sleep(0.4)
        except Exception as e:
            log.warning("Sector agent %s failed: %s", AgentClass.NAME, e)
            errors.append(AgentClass.NAME)

    # Collect all top picks weighted by sector score
    pick_scores: dict = {}
    for item in results:
        r = item["result"]
        w = item["weight"]
        if r.bias == "BULLISH":
            for pick in r.top_picks:
                pick_scores[pick] = pick_scores.get(pick, 0) + r.sector_score * w

    top_picks = sorted(pick_scores, key=pick_scores.get, reverse=True)[:5]
    avg_score = sum(r["result"].sector_score for r in results) / len(results) if results else 50

    return {
        "sector_consensus": "BULLISH" if avg_score > 60 else "BEARISH" if avg_score < 40 else "NEUTRAL",
        "avg_sector_score": round(avg_score, 1),
        "top_picks": top_picks,
        "agents": [r["result"].to_dict() for r in results],
        "errors": errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(run_sector_layer(), indent=2))
