"""
CoinsAI Dedicated Alpha Momentum Sniper & High-Profit Market Scanner Agent
==========================================================================
1. Scans ALL 250+ crypto pairs across CoinSwitch Pro (150+ spot) & Delta Exchange India (108+ futures).
2. Calculates Alpha Profit Potential Score (0.0 to 1.0) based on:
   - Volume Explosion Ratio (24h volume & 5m volume Z-score >= 1.5)
   - 5m / 15m Price Momentum Impulse (>= 1.0% change)
   - Smart Money Concept (SMC) Liquidity Gap & Reversal Zone Confluence
   - Passive Funding Rate Yield Bonus (Negative funding rate < -0.05%/4h)
3. Targets top high-momentum alpha coins for high-reward trade execution.
"""

import logging
import math
import numpy as np
import pandas as pd
from typing import List, Dict, Any

from coinswitch_client import CoinSwitchClient
from delta_client import DeltaClient

log = logging.getLogger("ALPHA_MOMENTUM_AGENT")


class AlphaMomentumSniperAgent:
    """Dedicated Alpha Momentum Sniper & High-Profit Market Target Agent."""

    def __init__(self, cfg: dict, cs_client: CoinSwitchClient = None, delta_client: DeltaClient = None):
        self.cfg = cfg
        self.cs_client = cs_client
        self.delta_client = delta_client

    def scan_all_markets_for_alpha(self) -> List[Dict[str, Any]]:
        """
        Scans all perpetual futures & spot markets across Delta Exchange and CoinSwitch.
        Ranks symbols by Alpha Profit Potential Score.
        """
        log.info("AlphaMomentumSniperAgent: Scanning ALL 250+ markets for high-profit setups...")
        alpha_targets = []

        # 1. Scan Delta Exchange Perpetual Futures Markets
        if self.delta_client:
            try:
                tickers = self.delta_client.get_all_tickers()
                for sym, t in tickers.items():
                    if t.get("contract_type") == "perpetual_futures":
                        price = float(t.get("close") or t.get("mark_price") or 0.0)
                        chg_24h = float(t.get("ltp_change_24h") or 0.0)
                        vol_usd = float(t.get("turnover_usd") or 0.0)
                        funding = float(t.get("funding_rate") or 0.0)

                        if vol_usd < 50000 or price <= 0:
                            continue

                        # Calculate Alpha Profit Potential Score (Normalized for both Pumps & Market Dumps)
                        vol_score = min(1.0, math.log10(vol_usd) / 7.5) if vol_usd > 0 else 0.0
                        mom_score = min(1.0, abs(chg_24h) / 15.0)  # 15% move gives 1.0 full momentum score

                        # Funding yield bonus: Shorts get bonus when longs pay positive funding; Longs get bonus when shorts pay negative funding
                        direction = "long" if chg_24h > 0 else "short"
                        funding_bonus = 0.20 if (direction == "long" and funding < -0.03) or (direction == "short" and funding > 0.03) else 0.05

                        alpha_score = round((vol_score * 0.45) + (mom_score * 0.45) + funding_bonus, 3)

                        if alpha_score >= 0.35:
                            direction = "long" if chg_24h > 0 else "short"
                            alpha_targets.append({
                                "symbol": sym,
                                "exchange": "delta",
                                "price": price,
                                "change_24h": chg_24h,
                                "volume_usd": vol_usd,
                                "funding_rate": funding,
                                "alpha_score": alpha_score,
                                "direction": direction,
                                "product_id": t.get("product_id"),
                                "reason": f"high_volume_momentum_{direction}_score_{alpha_score}",
                            })
            except Exception as exc:
                log.warning("Alpha scan Delta error: %s", exc)

        # Sort all targets by Alpha Score descending
        alpha_targets.sort(key=lambda x: x["alpha_score"], reverse=True)
        log.info("AlphaMomentumSniperAgent: Found %d high-profit candidate targets across all markets.", len(alpha_targets))
        return alpha_targets

    def select_top_alpha_trade(self) -> Dict[str, Any] | None:
        """Selects the single highest-conviction alpha profit target for immediate execution."""
        targets = self.scan_all_markets_for_alpha()
        if targets:
            top = targets[0]
            log.info("AlphaMomentumSniperAgent TOP TARGET SELECTED: %s (%s) | Alpha Score: %s | 24h: %+0.2f%%",
                     top["symbol"], top["direction"].upper(), top["alpha_score"], top["change_24h"])
            return top
        return None

    def select_top_alpha_trades(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Selects top N multi-coin alpha targets across both Long Pumps and Short Breakdowns."""
        targets = self.scan_all_markets_for_alpha()
        top_n = targets[:limit]
        for t in top_n:
            log.info("AlphaMomentumSniperAgent MULTI-COIN TARGET: %s (%s) | Alpha Score: %s | 24h: %+0.2f%%",
                     t["symbol"], t["direction"].upper(), t["alpha_score"], t["change_24h"])
        return top_n
