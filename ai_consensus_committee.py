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
        self.min_consensus_score = float(cfg.get("ai_consensus_min_score", 0.88))
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

        # D. Order Flow Delta & Cumulative Volume Delta (CVD) Analysis
        order_flow_delta = 0.0
        cvd_bias = "neutral"
        absorption_detected = False
        if len(df) >= 5:
            # Estimate aggressive buyer vs seller pressure across last 5 candles
            # Buy volume proxy = volume * (close - low) / (high - low)
            # Sell volume proxy = volume * (high - close) / (high - low)
            deltas = []
            for k in range(-5, 0):
                rng = max(high[k] - low[k], 1e-6)
                buy_vol = volume[k] * ((close[k] - low[k]) / rng)
                sell_vol = volume[k] * ((high[k] - close[k]) / rng)
                deltas.append(buy_vol - sell_vol)

            net_delta = float(np.sum(deltas))
            total_vol = float(np.sum(volume[-5:])) or 1.0
            order_flow_delta = round(net_delta / total_vol, 3)

            # CVD Divergence / Delta Absorption detection:
            # Price pushed lower but net delta is positive -> Bullish Absorption
            # Price pushed higher but net delta is negative -> Bearish Absorption
            price_change_5 = close[-1] - close[-5]
            if price_change_5 < 0 and order_flow_delta > 0.15:
                absorption_detected = True
                cvd_bias = "bullish"
                smc_score += 0.25
                if bias == "neutral":
                    bias = "bullish"
            elif price_change_5 > 0 and order_flow_delta < -0.15:
                absorption_detected = True
                cvd_bias = "bearish"
                smc_score += 0.25
                if bias == "neutral":
                    bias = "bearish"
            elif order_flow_delta > 0.20:
                cvd_bias = "bullish"
                smc_score += 0.15
            elif order_flow_delta < -0.20:
                cvd_bias = "bearish"
                smc_score += 0.15

        orderflow_info = {
            "net_delta_ratio": order_flow_delta,
            "cvd_bias": cvd_bias,
            "absorption_detected": absorption_detected,
        }

        # E. Liquidity Map (BSL / SSL Pools, Equal Highs EQH, Equal Lows EQL)
        liquidity_map = {
            "buy_side_liquidity_pools": [],   # Resting buy-stops above key highs
            "sell_side_liquidity_pools": [],  # Resting sell-stops below key lows
            "equal_highs": [],
            "equal_lows": [],
            "nearest_bsl": None,
            "nearest_ssl": None,
            "liquidity_draw": "neutral",
            "bsl_distance_pct": 0.0,
            "ssl_distance_pct": 0.0,
        }

        if len(df) >= 10:
            # Map swing pivot highs and lows across lookback
            eval_window = min(len(df) - 2, 40)
            highs_win = high[-eval_window:]
            lows_win = low[-eval_window:]
            
            # Detect significant swing highs (local maxima) as Buy-Side Liquidity (BSL)
            for j in range(2, len(highs_win) - 2):
                if highs_win[j] >= highs_win[j-1] and highs_win[j] >= highs_win[j-2] and \
                   highs_win[j] >= highs_win[j+1] and highs_win[j] >= highs_win[j+2]:
                    pool_price = float(highs_win[j])
                    if pool_price > curr_close:
                        liquidity_map["buy_side_liquidity_pools"].append(round(pool_price, 4))
            
            # Detect significant swing lows (local minima) as Sell-Side Liquidity (SSL)
            for j in range(2, len(lows_win) - 2):
                if lows_win[j] <= lows_win[j-1] and lows_win[j] <= lows_win[j-2] and \
                   lows_win[j] <= lows_win[j+1] and lows_win[j] <= lows_win[j+2]:
                    pool_price = float(lows_win[j])
                    if pool_price < curr_close:
                        liquidity_map["sell_side_liquidity_pools"].append(round(pool_price, 4))

            # Detect Equal Highs (EQH) - Double/Triple tops where retail stops cluster heavily
            bsl_pools = sorted(liquidity_map["buy_side_liquidity_pools"])
            for idx in range(len(bsl_pools) - 1):
                if abs(bsl_pools[idx] - bsl_pools[idx+1]) / max(bsl_pools[idx], 1e-6) <= 0.002: # within 0.2%
                    liquidity_map["equal_highs"].append(round((bsl_pools[idx] + bsl_pools[idx+1]) / 2.0, 4))

            # Detect Equal Lows (EQL) - Double/Triple bottoms where stop-losses cluster
            ssl_pools = sorted(liquidity_map["sell_side_liquidity_pools"])
            for idx in range(len(ssl_pools) - 1):
                if abs(ssl_pools[idx] - ssl_pools[idx+1]) / max(ssl_pools[idx], 1e-6) <= 0.002: # within 0.2%
                    liquidity_map["equal_lows"].append(round((ssl_pools[idx] + ssl_pools[idx+1]) / 2.0, 4))

            # Nearest magnet levels (draw on liquidity)
            if bsl_pools:
                nearest_bsl = min(bsl_pools)
                liquidity_map["nearest_bsl"] = nearest_bsl
                liquidity_map["bsl_distance_pct"] = round((nearest_bsl - curr_close) / curr_close * 100.0, 2)

            if ssl_pools:
                nearest_ssl = max(ssl_pools)
                liquidity_map["nearest_ssl"] = nearest_ssl
                liquidity_map["ssl_distance_pct"] = round((curr_close - nearest_ssl) / curr_close * 100.0, 2)

            # Determine algorithmic draw on liquidity
            if liquidity_map["equal_highs"] and (not liquidity_map["equal_lows"] or bias == "bullish"):
                liquidity_map["liquidity_draw"] = "draw_to_buy_side_liquidity"
                smc_score += 0.20
            elif liquidity_map["equal_lows"] and (not liquidity_map["equal_highs"] or bias == "bearish"):
                liquidity_map["liquidity_draw"] = "draw_to_sell_side_liquidity"
                smc_score += 0.20
            elif liquidity_map["nearest_bsl"] and (not liquidity_map["nearest_ssl"] or liquidity_map["bsl_distance_pct"] < liquidity_map["ssl_distance_pct"]):
                liquidity_map["liquidity_draw"] = "bullish_bsl_target"
                smc_score += 0.10
            elif liquidity_map["nearest_ssl"]:
                liquidity_map["liquidity_draw"] = "bearish_ssl_target"
                smc_score += 0.10

        return {
            "fvg": fvg_info,
            "order_block": ob_info,
            "liquidity_sweep": sweep_info,
            "order_flow": orderflow_info,
            "liquidity_map": liquidity_map,
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

        # 3.2. Order Flow Delta & Institutional CVD Confluence
        of_info = smc_data.get("order_flow", {})
        cvd_bias = of_info.get("cvd_bias", "neutral")
        of_delta = float(of_info.get("net_delta_ratio", 0.0))
        of_aligned = (direction == "BUY" and cvd_bias == "bullish") or (direction == "SELL" and cvd_bias == "bearish")
        orderflow_score = 0.15 if of_aligned else (0.20 if of_info.get("absorption_detected") else 0.05)

        # 3.5. Smart Gatekeeper Pre-Check: Do not waste NVIDIA API tokens on mathematically non-viable setups
        tech_score = (base_confidence * 0.30) + (smc_score * 0.18 if smc_aligned else 0.08) + vol_score + trend_score + orderflow_score
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
            "order_flow": of_info,
            "net_volume_delta": of_delta,
            "orderflow_absorption": of_info.get("absorption_detected", False),
            "liquidity_map": smc_data.get("liquidity_map"),
        }
        nvidia_verdict = self.nvidia_engine.evaluate_super_brain_consensus(symbol, signal, nvidia_market_context, df=df)
        nvidia_score = float(nvidia_verdict.get("consensus_score", 0.85))

        # 5. Master Composite Consensus Score (0.0 to 1.0)
        consensus_score = tech_score + (nvidia_score * 0.40)
        consensus_score = min(round(consensus_score, 3), 1.0)

        # 6. Precision Invalidation SL & Target TP under Capital Survival Mode
        default_sl_pct = float(self.cfg.get("stop_loss_pct", 1.5))
        default_tp_pct = float(self.cfg.get("take_profit_pct", 6.0))

        if smc_data.get("order_block"):
            inval_px = float(smc_data["order_block"]["invalidation_price"])
            sl_pct = abs(price - inval_px) / price * 100.0
            hard_sl_pct = max(0.5, min(round(sl_pct * 1.05, 2), 1.5))  # Hard cap 1.5% SL
        elif smc_data.get("fvg"):
            gap_boundary = float(smc_data["fvg"]["gap_bottom"] if direction == "BUY" else smc_data["fvg"]["gap_top"])
            sl_pct = abs(price - gap_boundary) / price * 100.0
            hard_sl_pct = max(0.5, min(round(sl_pct * 1.05, 2), 1.5))  # Hard cap 1.5% SL
        else:
            hard_sl_pct = min(default_sl_pct, 1.5)

        # Capital Survival: Ensure minimum 1:3 Reward-to-Risk ratio (prefer 1:4+)
        take_profit_pct = max(default_tp_pct, round(hard_sl_pct * 3.5, 2))

        # Dynamic Anchor to Liquidity Map target (BSL for BUY, SSL for SELL)
        liq_m = smc_data.get("liquidity_map", {})
        if direction == "BUY" and liq_m.get("nearest_bsl"):
            bsl_target_dist = float(liq_m.get("bsl_distance_pct", 0.0))
            if bsl_target_dist >= hard_sl_pct * 3.0:
                take_profit_pct = round(bsl_target_dist, 2)
        elif direction == "SELL" and liq_m.get("nearest_ssl"):
            ssl_target_dist = float(liq_m.get("ssl_distance_pct", 0.0))
            if ssl_target_dist >= hard_sl_pct * 3.0:
                take_profit_pct = round(ssl_target_dist, 2)

        rr_ratio = round(take_profit_pct / hard_sl_pct, 2)

        hard_sl = price * (1 - hard_sl_pct / 100.0) if direction == "BUY" else price * (1 + hard_sl_pct / 100.0)
        take_profit = price * (1 + take_profit_pct / 100.0) if direction == "BUY" else price * (1 - take_profit_pct / 100.0)

        # Strict Multi-Model Committee Approval
        nvidia_approved = bool(nvidia_verdict.get("approved", False))
        min_rr_met = (rr_ratio >= float(self.cfg.get("min_rr_ratio", 3.0)))
        approved = (consensus_score >= self.min_consensus_score) and nvidia_approved and min_rr_met

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
            "risk_reward_ratio": rr_ratio,
            "reason": f"NVIDIA GLM-5.3 & SMC Score: {consensus_score:.3f} | R:R 1:{rr_ratio} | NV_Appr={nvidia_approved}",
        }

        if approved:
            log.info(
                "⚡ [AI CONSENSUS APPROVED • CAPITAL SURVIVAL] %s %s | Score: %.3f (Req: %.2f) | Entry: %.4f | SL: %.4f (-%.1f%%) | TP: %.4f (+%.1f%%) | RR: 1:%.1f",
                symbol, direction, consensus_score, self.min_consensus_score, price, hard_sl, hard_sl_pct, take_profit, take_profit_pct, rr_ratio
            )
        else:
            log.info(
                "🛡️ [CAPITAL SURVIVAL FILTERED] %s %s rejected | Score: %.3f (Req: %.2f) | RR: 1:%.1f (Req: >=3.0) | NV_Appr: %s",
                symbol, direction, consensus_score, self.min_consensus_score, rr_ratio, nvidia_approved
            )

        return verdict
