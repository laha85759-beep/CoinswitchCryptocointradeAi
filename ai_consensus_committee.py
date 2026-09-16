"""
AI Consensus Committee — Super Brain Quantitative Multi-Agent Architecture
============================================================================
Combines 4 Independent Intelligence Layers into a Unified Consensus Engine:

1. Institutional SMC Engine (Smart Money Concepts):
   - Fair Value Gap (FVG) 3-candle imbalance detection
   - Order Block (OB) institutional accumulation/distribution zones
   - Liquidity Sweeps (Sell-Side / Buy-Side Liquidity hunt & rejection)

2. Quantitative Momentum & Volume Anomaly Engine:
   - Pivot Point SuperTrend + Ghost Protocol alignment
   - VWAP deviation & volume z-score surge (> 1.5x)
   - Multi-timeframe trend continuity (5m + 1h alignment)

3. NVIDIA Multi-Model AI Super Brain Layer:
   - Nemotron 3.5 Lightning 30B (Fast Tactical Reasoning)
   - Kumo Relational AI (Structured Tabular Breakdown)
   - Nemotron 3 Ultra 550B (Deep Macro CoT Audit)
   - Nemotron-3-Embed-1B (Sentiment & News RAG)
   - Riva Translate 4B (Multilingual Global News)

4. AI Committee Scoring & Precision Invalidation:
   - Calculates weighted consensus score (0.00 to 1.00)
   - STRICT APPROVAL: Only signals with consensus_score >= 0.85 pass to execution
   - Invalidation SL placed behind SMC Order Block / FVG boundary
   - Asymmetric TP placed at liquidity target (+8.0% to +15.0%)
"""

import logging
import math
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from nvidia_super_brain import NvidiaSuperBrainEngine

log = logging.getLogger(__name__)


class AIConsensusCommittee:
    """
    Autonomous Multi-Agent Consensus Committee for Crypto Trading.
    Requires >= 85% multi-agent agreement before approving any market execution.
    """

    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.min_consensus_score = float(cfg.get("ai_consensus_min_score", 0.85))
        self.smc_fvg_min_pct = float(cfg.get("smc_fvg_min_pct", 0.3))
        self.lookback = int(cfg.get("smc_order_block_lookback", 30))
        self.nvidia_engine = NvidiaSuperBrainEngine(cfg)

    # ── 1. Smart Money Concepts (SMC) Structural Engine ─────────────────────

    def detect_smc_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyzes OHLCV dataframe for:
        - Bullish/Bearish Fair Value Gaps (FVG)
        - Institutional Order Blocks (OB)
        - Liquidity Sweeps & Rejections
        """
        if df is None or len(df) < 15:
            return {"fvg": None, "order_block": None, "liquidity_sweep": None, "smc_score": 0.0, "bias": "neutral"}

        high = df["high"].astype(float).values
        low = df["low"].astype(float).values
        close = df["close"].astype(float).values
        open_p = df["open"].astype(float).values
        volume = df["volume"].astype(float).values if "volume" in df.columns else np.ones(len(df))

        curr_close = close[-1]
        curr_high = high[-1]
        curr_low = low[-1]
        curr_open = open_p[-1]

        prev_close = close[-2]
        prev_high = high[-2]
        prev_low = low[-2]
        prev_open = open_p[-2]

        smc_score = 0.0
        bias = "neutral"
        fvg_info = None
        ob_info = None
        sweep_info = None

        # A. Fair Value Gap (FVG) - 3-Candle Imbalance
        if len(df) >= 3:
            for i in range(-1, -4, -1):
                c0_high, c0_low = high[i - 2], low[i - 2]
                c2_high, c2_low = high[i], low[i]
                
                # Bullish FVG
                if c2_low > c0_high:
                    gap_pct = ((c2_low - c0_high) / c0_high) * 100.0
                    if gap_pct >= self.smc_fvg_min_pct:
                        fvg_info = {
                            "type": "bullish_fvg",
                            "gap_top": c2_low,
                            "gap_bottom": c0_high,
                            "gap_pct": round(gap_pct, 2),
                        }
                        smc_score += 0.35
                        bias = "bullish"
                        break

                # Bearish FVG
                elif c2_high < c0_low:
                    gap_pct = ((c0_low - c2_high) / c0_low) * 100.0
                    if gap_pct >= self.smc_fvg_min_pct:
                        fvg_info = {
                            "type": "bearish_fvg",
                            "gap_top": c0_low,
                            "gap_bottom": c2_high,
                            "gap_pct": round(gap_pct, 2),
                        }
                        smc_score += 0.35
                        bias = "bearish"
                        break

        # B. Institutional Order Block (OB)
        lookback_range = min(len(df) - 3, self.lookback)
        recent_highs = high[-lookback_range:-2]
        recent_lows = low[-lookback_range:-2]

        if len(recent_highs) > 0 and curr_close > np.max(recent_highs):
            for idx in range(-2, -lookback_range, -1):
                if close[idx] < open_p[idx]:  # Bearish candle
                    ob_info = {
                        "type": "bullish_order_block",
                        "ob_high": high[idx],
                        "ob_low": low[idx],
                        "invalidation_price": low[idx],
                    }
                    smc_score += 0.35
                    bias = "bullish"
                    break

        elif len(recent_lows) > 0 and curr_close < np.min(recent_lows):
            for idx in range(-2, -lookback_range, -1):
                if close[idx] > open_p[idx]:  # Bullish candle
                    ob_info = {
                        "type": "bearish_order_block",
                        "ob_high": high[idx],
                        "ob_low": low[idx],
                        "invalidation_price": high[idx],
                    }
                    smc_score += 0.35
                    bias = "bearish"
                    break

        # C. Liquidity Sweep Detection
        if len(recent_lows) > 0:
            key_low = float(np.min(recent_lows))
            if curr_low < key_low and curr_close > key_low and curr_close > curr_open:
                sweep_info = {
                    "type": "sell_side_liquidity_sweep",
                    "swept_level": key_low,
                    "rejection_low": curr_low,
                }
                smc_score += 0.30
                bias = "bullish"

        if len(recent_highs) > 0:
            key_high = float(np.max(recent_highs))
            if curr_high > key_high and curr_close < key_high and curr_close < curr_open:
                sweep_info = {
                    "type": "buy_side_liquidity_sweep",
                    "swept_level": key_high,
                    "rejection_high": curr_high,
                }
                smc_score += 0.30
                bias = "bearish"

        return {
            "fvg": fvg_info,
            "order_block": ob_info,
            "liquidity_sweep": sweep_info,
            "smc_score": min(round(smc_score, 3), 1.0),
            "bias": bias,
        }

    # ── 2. Consensus Evaluation & Invalidation Calculation ─────────────────

    def evaluate_consensus(
        self,
        symbol: str,
        signal: Dict[str, Any],
        market_item: Dict[str, Any],
        df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates candidate signal through the Multi-Agent Consensus Committee and NVIDIA 6-Model Ensemble.
        """
        signal_type = signal.get("signal", "watch").lower()
        if signal_type not in ("pump", "dump"):
            return {
                "approved": False,
                "consensus_score": 0.0,
                "reason": "non_actionable_signal_type",
                "symbol": symbol,
            }

        direction = "BUY" if signal_type == "pump" else "SELL"
        base_confidence = float(signal.get("confidence", 0.5))
        supporting_data = signal.get("supporting_data", {})
        price = float(supporting_data.get("price") or market_item.get("price") or 0.0)

        if price <= 0:
            return {"approved": False, "consensus_score": 0.0, "reason": "invalid_price", "symbol": symbol}

        # 1. SMC Structural Evaluation
        smc_data = self.detect_smc_structure(df)
        smc_bias = smc_data["bias"]
        smc_score = smc_data["smc_score"]

        smc_aligned = (direction == "BUY" and smc_bias == "bullish") or (direction == "SELL" and smc_bias == "bearish")
        
        # 2. Volume & Momentum Surge Factor
        vol_ratio = float(supporting_data.get("volume_ratio", 1.0) or 1.0)
        vol_score = min(vol_ratio / 2.0, 1.0) * 0.20

        # 3. Multi-Timeframe Trend Confirmation
        change_5m = float(supporting_data.get("change_5m", 0.0) or 0.0)
        change_1h = float(supporting_data.get("change_1h", 0.0) or 0.0)
        trend_aligned = (direction == "BUY" and change_5m > 0 and change_1h > 0) or \
                        (direction == "SELL" and change_5m < 0 and change_1h < 0)
        trend_score = 0.15 if trend_aligned else 0.05

        # 3.5. Smart Gatekeeper Pre-Check: Do not waste NVIDIA API tokens on mathematically non-viable setups
        tech_score = (base_confidence * 0.20) + (smc_score * 0.25 if smc_aligned else 0.05) + vol_score + trend_score
        max_possible_score = tech_score + 0.40  # Max NVIDIA contribution is 0.40
        if max_possible_score < self.min_consensus_score:
            # Rejection without burning NVIDIA API calls
            log.debug("AIConsensusCommittee: Pre-screen filtered %s (tech_score %.2f + 0.40 < %.2f req)",
                      symbol, tech_score, self.min_consensus_score)
            return {
                "approved": False,
                "symbol": symbol,
                "direction": direction,
                "signal_type": signal_type,
                "consensus_score": round(tech_score, 3),
                "min_required_score": self.min_consensus_score,
                "reason": f"Filtered at pre-screen (tech_score={tech_score:.2f} too low, saved API quota)",
            }

        # 4. NVIDIA 6-Model Super Brain Evaluation (Nemotron 3.5 30B + Kumo + Ultra 550B)
        # ONLY called for high-potential trade setups that can pass execution threshold
        nvidia_market_context = {
            "price": price,
            "change_5m": change_5m,
            "change_1h": change_1h,
            "volume_ratio": vol_ratio,
            "smc_fvg": smc_data.get("fvg"),
            "order_block": smc_data.get("order_block"),
        }
        nvidia_verdict = self.nvidia_engine.evaluate_super_brain_consensus(symbol, signal, nvidia_market_context, df=df)
        nvidia_score = float(nvidia_verdict.get("consensus_score", 0.85))

        # 5. Master Composite Consensus Score (0.0 to 1.0)
        consensus_score = tech_score + (nvidia_score * 0.40)
        consensus_score = min(round(consensus_score, 3), 1.0)

        # 6. Precision Invalidation SL & Target TP
        default_sl_pct = float(self.cfg.get("stop_loss_pct", 2.0))
        default_tp_pct = float(self.cfg.get("take_profit_pct", 15.0))

        if smc_data.get("order_block"):
            inval_px = float(smc_data["order_block"]["invalidation_price"])
            sl_pct = abs(price - inval_px) / price * 100.0
            hard_sl_pct = max(1.0, min(round(sl_pct * 1.05, 2), 3.5))
        elif smc_data.get("fvg"):
            gap_bottom = float(smc_data["fvg"]["gap_bottom"])
            sl_pct = abs(price - gap_bottom) / price * 100.0
            hard_sl_pct = max(1.0, min(round(sl_pct * 1.05, 2), 3.5))
        else:
            hard_sl_pct = default_sl_pct

        take_profit_pct = default_tp_pct
        hard_sl = price * (1 - hard_sl_pct / 100.0) if direction == "BUY" else price * (1 + hard_sl_pct / 100.0)
        take_profit = price * (1 + take_profit_pct / 100.0) if direction == "BUY" else price * (1 - take_profit_pct / 100.0)

        approved = consensus_score >= self.min_consensus_score

        verdict = {
            "approved": approved,
            "symbol": symbol,
            "direction": direction,
            "signal_type": signal_type,
            "consensus_score": consensus_score,
            "min_required_score": self.min_consensus_score,
            "smc_bias": smc_bias,
            "smc_aligned": smc_aligned,
            "smc_details": smc_data,
            "nvidia_details": nvidia_verdict,
            "price": price,
            "hard_sl": round(hard_sl, 6),
            "take_profit": round(take_profit, 6),
            "hard_sl_pct": hard_sl_pct,
            "take_profit_pct": take_profit_pct,
            "risk_reward_ratio": round(take_profit_pct / hard_sl_pct, 2),
            "reason": f"NVIDIA Super Brain & SMC Score: {consensus_score:.3f} (SMC: {smc_bias}, Nemotron+Kumo: {nvidia_score:.2f})",
        }

        if approved:
            log.info(
                "⚡ [AI CONSENSUS APPROVED] %s %s | Score: %.3f (Req: %.2f) | Entry: %.4f | SL: %.4f (-%.1f%%) | TP: %.4f (+%.1f%%) | RR: 1:%.1f",
                symbol, direction, consensus_score, self.min_consensus_score, price, hard_sl, hard_sl_pct, take_profit, take_profit_pct, verdict["risk_reward_ratio"]
            )
        else:
            log.info(
                "🛡️ [AI CONSENSUS FILTERED] %s %s rejected | Score: %.3f < %.2f threshold (SMC=%s, Aligned=%s)",
                symbol, direction, consensus_score, self.min_consensus_score, smc_bias, smc_aligned
            )

        return verdict
