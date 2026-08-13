"""
Darwin Engine — Autoresearch Self-Improvement Loop
===================================================
ATLAS-style Karpathy autoresearch adapted for CoinsAI.

The Loop:
  1. Every 7 trading days: calculate rolling Sharpe ratio for each agent
  2. Identify WORST performer (lowest Sharpe)
  3. Generate 1 targeted prompt modification via 1min.AI
  4. Run modified agent for 5 days in shadow mode (no real trades)
  5. Compare new Sharpe vs old Sharpe:
     - Improved → mark as KEPT (keep change)
     - Degraded  → mark as REVERTED

Darwinian Weights:
  Each agent has a weight 0.3 (min) to 2.5 (max).
  Top quartile agents    → weight × 1.05 daily
  Bottom quartile agents → weight × 0.95 daily

Agent Spawning:
  When same blind spot appears 3+ times in 5 days → spawn new specialist agent.
"""
from __future__ import annotations
import json
import logging
import math
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

import requests

log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
WEIGHTS_FILE       = BASE_DIR / "agent_weights.json"
DARWIN_HISTORY     = BASE_DIR / "darwin_history.json"
SPAWNED_AGENTS     = BASE_DIR / "spawned_agents.json"
AGENT_AUDIT_FILE   = BASE_DIR / "agent_audit.jsonl"
CLOSED_TRADES_FILE = BASE_DIR / "closed_trades.json"

# All 25 agent names (Layers 1-4)
ALL_AGENT_NAMES = [
    # Layer 1 - Macro
    "BTC_Dominance", "Fed_Fear_Index", "Global_Liquidity", "Stablecoin_Flow",
    "Miner_Sentiment", "Fear_Greed_Index", "Regulation_Risk", "OnChain_Flow",
    "Volatility_Regime", "Institutional_Flow",
    # Layer 2 - Sector
    "L1_BlueChips", "DeFi_Desk", "AI_Meme_Desk", "RWA_Desk",
    "Infra_Chains_Desk", "Gaming_Desk", "Relationship_Mapper",
    # Layer 3 - Supertraders
    "Druckenmiller_Crypto", "Soros_Reflexivity", "Simons_Quant", "Ackman_Conviction",
    # Layer 4 - Decision
    "CRO_Risk", "Alpha_Discovery", "Auto_Execution", "CIO_Synthesizer",
]

# Darwinian weight bounds
MIN_WEIGHT = 0.3
MAX_WEIGHT = 2.5
DAILY_TOP_QUARTILE_BOOST  = 1.05
DAILY_BOT_QUARTILE_DECAY  = 0.95


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────
# Weight Manager
# ─────────────────────────────────────────────────────────────
class DarwinWeightManager:
    """Manages the Darwinian weight for each of the 25 agents."""

    def __init__(self):
        self.weights = self._load_or_init_weights()

    def _load_or_init_weights(self) -> dict:
        data = _load_json(WEIGHTS_FILE, {})
        # Ensure all agents have a weight
        changed = False
        for name in ALL_AGENT_NAMES:
            if name not in data:
                data[name] = {
                    "weight": 1.0,
                    "sharpe_rolling": 0.0,
                    "trades_tracked": 0,
                    "wins": 0,
                    "losses": 0,
                    "total_return_pct": 0.0,
                    "last_updated": _utc_now(),
                }
                changed = True
        if changed:
            _save_json(WEIGHTS_FILE, data)
        return data

    def get(self, agent_name: str) -> float:
        return self.weights.get(agent_name, {}).get("weight", 1.0)

    def get_all_weights(self) -> Dict[str, float]:
        return {k: v["weight"] for k, v in self.weights.items()}

    def update_sharpe(self, agent_name: str, sharpe: float, wins: int, losses: int, total_return: float):
        if agent_name in self.weights:
            self.weights[agent_name]["sharpe_rolling"] = round(sharpe, 4)
            self.weights[agent_name]["wins"] = wins
            self.weights[agent_name]["losses"] = losses
            self.weights[agent_name]["total_return_pct"] = round(total_return, 4)
            self.weights[agent_name]["trades_tracked"] = wins + losses
            self.weights[agent_name]["last_updated"] = _utc_now()
        _save_json(WEIGHTS_FILE, self.weights)

    def apply_daily_darwin_update(self) -> dict:
        """
        Top quartile agents get weight * 1.05.
        Bottom quartile get weight * 0.95.
        Called once per day.
        """
        scores = {k: v.get("sharpe_rolling", 0.0) for k, v in self.weights.items()}
        sorted_names = sorted(scores, key=scores.get, reverse=True)
        n = len(sorted_names)
        top_quartile = set(sorted_names[:max(1, n // 4)])
        bot_quartile = set(sorted_names[max(1, 3 * n // 4):])

        updated = {}
        for name in ALL_AGENT_NAMES:
            if name not in self.weights:
                continue
            old_w = self.weights[name]["weight"]
            if name in top_quartile:
                new_w = min(MAX_WEIGHT, old_w * DAILY_TOP_QUARTILE_BOOST)
                status = "TOP_QUARTILE_BOOST"
            elif name in bot_quartile:
                new_w = max(MIN_WEIGHT, old_w * DAILY_BOT_QUARTILE_DECAY)
                status = "BOT_QUARTILE_DECAY"
            else:
                new_w = old_w
                status = "NEUTRAL"
            self.weights[name]["weight"] = round(new_w, 4)
            updated[name] = {"old": round(old_w, 4), "new": round(new_w, 4), "status": status}

        _save_json(WEIGHTS_FILE, self.weights)
        log.info("Darwin daily weight update complete: %d agents updated.", len(updated))
        return updated

    def get_leaderboard(self) -> list:
        """Returns agents sorted by Sharpe ratio (highest first)."""
        board = []
        for name, data in self.weights.items():
            wins = data.get("wins", 0)
            losses = data.get("losses", 0)
            total = wins + losses
            win_rate = round(wins / total * 100, 1) if total > 0 else 0.0
            board.append({
                "agent": name,
                "weight": data.get("weight", 1.0),
                "sharpe": data.get("sharpe_rolling", 0.0),
                "win_rate": win_rate,
                "wins": wins,
                "losses": losses,
                "total_return_pct": data.get("total_return_pct", 0.0),
                "last_updated": data.get("last_updated", ""),
            })
        return sorted(board, key=lambda x: x["sharpe"], reverse=True)


# ─────────────────────────────────────────────────────────────
# Sharpe Calculator
# ─────────────────────────────────────────────────────────────
class SharpeCalculator:
    """
    Computes rolling Sharpe ratio from closed trades.
    Each agent that triggered a signal gets credited/debited for trade outcome.
    """

    def __init__(self):
        self.trades = self._load_trades()

    def _load_trades(self) -> list:
        trades = []
        # Load from closed_trades.json
        data = _load_json(CLOSED_TRADES_FILE, [])
        if isinstance(data, list):
            trades.extend(data)
        # Also scan agent_audit.jsonl for additional records
        if AGENT_AUDIT_FILE.exists():
            try:
                with AGENT_AUDIT_FILE.open("r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            row = json.loads(line)
                            if row.get("payload", {}).get("pnl_pct") is not None:
                                trades.append(row["payload"])
                        except Exception:
                            pass
            except Exception:
                pass
        return trades

    def compute_for_agent(self, agent_name: str, lookback_days: int = 30) -> dict:
        """Compute win rate and Sharpe for an agent over lookback period."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        relevant = []
        for t in self.trades:
            pnl = t.get("pnl_pct") or t.get("pnl_percent") or t.get("pnl")
            ts_str = t.get("closed_at") or t.get("timestamp") or t.get("exit_time", "")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")) if ts_str else cutoff
            except Exception:
                ts = cutoff
            if pnl is not None and ts >= cutoff:
                relevant.append(float(pnl))

        if not relevant:
            return {"sharpe": 0.0, "wins": 0, "losses": 0, "total_return": 0.0}

        wins   = sum(1 for p in relevant if p > 0)
        losses = sum(1 for p in relevant if p <= 0)
        total_return = sum(relevant)
        mean_r = total_return / len(relevant)

        # Sharpe = mean_return / std_return (annualized approximation)
        if len(relevant) >= 2:
            variance = sum((r - mean_r) ** 2 for r in relevant) / len(relevant)
            std = math.sqrt(variance) if variance > 0 else 0.001
            sharpe = mean_r / std * math.sqrt(252)
        else:
            sharpe = mean_r * 10  # single trade, rough estimate

        return {
            "sharpe": round(sharpe, 4),
            "wins": wins,
            "losses": losses,
            "total_return": round(total_return, 4),
        }

    def compute_all_agents(self) -> dict:
        results = {}
        for name in ALL_AGENT_NAMES:
            results[name] = self.compute_for_agent(name)
        return results


# ─────────────────────────────────────────────────────────────
# Autoresearch Prompt Rewriter
# ─────────────────────────────────────────────────────────────
class AutoresearchRewriter:
    """
    Uses 1min.AI to generate targeted prompt modifications for the worst-performing agent.
    Inspired by Karpathy's autoresearch pattern.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate_improvement(self, agent_name: str, current_logic_summary: str,
                              performance: dict) -> str:
        """
        Calls 1min.AI to suggest ONE targeted improvement for the worst agent.
        """
        if not self.api_key:
            return self._rule_based_improvement(agent_name, performance)

        prompt = f"""You are an expert crypto trading agent optimizer.

Agent: {agent_name}
Current performance (last 30 days):
- Sharpe ratio: {performance.get('sharpe', 0):.3f}
- Win rate: {performance.get('wins', 0)}/{performance.get('wins', 0)+performance.get('losses', 0)} trades
- Total return: {performance.get('total_return', 0):.2f}%
- Current logic: {current_logic_summary[:300]}

Task: Suggest ONE specific, targeted improvement to this agent's signal logic that would improve its Sharpe ratio.
The improvement must be concrete and implementable in Python.
Focus on: threshold tuning, indicator weights, regime filters, or entry/exit timing.
Output: A single paragraph describing the improvement. Be specific. No generic advice."""

        try:
            r = requests.post(
                "https://api.1min.ai/api/features",
                headers={"API-KEY": self.api_key, "Content-Type": "application/json"},
                json={
                    "type": "CHAT_WITH_AI",
                    "model": "mistral-7b-instruct",
                    "conversationId": f"darwin-{agent_name}",
                    "message": prompt,
                },
                timeout=30,
            )
            if r.status_code == 200:
                result = r.json()
                answer = (result.get("aiRecord", {}).get("aiRecordDetail", {})
                          .get("resultObject", [""])[0])
                if answer:
                    return answer.strip()
        except Exception as e:
            log.warning("1min.AI rewrite call failed: %s", e)

        return self._rule_based_improvement(agent_name, performance)

    def _rule_based_improvement(self, agent_name: str, performance: dict) -> str:
        """Fallback: rule-based improvement suggestions."""
        sharpe = performance.get("sharpe", 0)
        win_rate_pct = (performance.get("wins", 0) /
                        max(1, performance.get("wins", 0) + performance.get("losses", 0)) * 100)

        if sharpe < 0:
            return (f"Agent {agent_name} has negative Sharpe ({sharpe:.2f}). "
                    f"Recommendation: Increase confidence threshold by 0.10 to filter low-quality signals. "
                    f"Current win rate {win_rate_pct:.0f}% — need >55% for positive Sharpe.")
        elif win_rate_pct < 50:
            return (f"Agent {agent_name} win rate is {win_rate_pct:.0f}% (<50%). "
                    f"Recommendation: Add macro regime filter — only fire signals when macro is RISK_ON. "
                    f"This will reduce trade count but increase win rate.")
        else:
            return (f"Agent {agent_name} Sharpe {sharpe:.2f} is low despite {win_rate_pct:.0f}% win rate. "
                    f"Recommendation: Increase take-profit threshold from 4% to 5% to improve reward/risk. "
                    f"The wins are too small relative to losses.")


# ─────────────────────────────────────────────────────────────
# Darwin Engine (Main Loop)
# ─────────────────────────────────────────────────────────────
class DarwinEngine:
    """
    Main autoresearch self-improvement engine.
    Runs the full Darwin loop: evaluate → identify worst → rewrite → test → commit/revert.
    """

    def __init__(self, onemin_api_key: str = ""):
        self.weight_manager = DarwinWeightManager()
        self.sharpe_calc    = SharpeCalculator()
        self.rewriter       = AutoresearchRewriter(onemin_api_key)
        self.history        = _load_json(DARWIN_HISTORY, [])
        self.spawned        = _load_json(SPAWNED_AGENTS, [])

    def run_full_cycle(self) -> dict:
        """
        Execute one full Darwin improvement cycle.
        Call this weekly (every 7 trading days).
        """
        log.info("Darwin Engine: Starting full improvement cycle...")
        cycle_result = {
            "started_at": _utc_now(),
            "steps": [],
        }

        # Step 1: Compute Sharpe for all agents
        log.info("Step 1: Computing Sharpe ratios for all 25 agents...")
        all_sharpes = self.sharpe_calc.compute_all_agents()
        for name, perf in all_sharpes.items():
            self.weight_manager.update_sharpe(
                name, perf["sharpe"], perf["wins"], perf["losses"], perf["total_return"]
            )
        cycle_result["steps"].append({"step": "sharpe_computed", "agents": len(all_sharpes)})

        # Step 2: Identify worst performer
        leaderboard = self.weight_manager.get_leaderboard()
        worst_agent = leaderboard[-1]
        best_agent  = leaderboard[0]
        log.info("Worst agent: %s (Sharpe: %.3f)", worst_agent["agent"], worst_agent["sharpe"])
        log.info("Best agent:  %s (Sharpe: %.3f)", best_agent["agent"],  best_agent["sharpe"])
        cycle_result["steps"].append({
            "step": "worst_identified",
            "worst_agent": worst_agent["agent"],
            "worst_sharpe": worst_agent["sharpe"],
            "best_agent": best_agent["agent"],
            "best_sharpe": best_agent["sharpe"],
        })

        # Step 3: Generate prompt improvement for worst agent
        log.info("Step 3: Generating improvement for %s...", worst_agent["agent"])
        perf = all_sharpes.get(worst_agent["agent"], {})
        improvement = self.rewriter.generate_improvement(
            agent_name=worst_agent["agent"],
            current_logic_summary=f"Layer agent with Sharpe={worst_agent['sharpe']:.3f}",
            performance=perf,
        )
        log.info("Improvement generated: %s", improvement[:100])
        cycle_result["steps"].append({
            "step": "improvement_generated",
            "agent": worst_agent["agent"],
            "improvement": improvement,
        })

        # Step 4: Log to Darwin history (shadow mode — 5-day test will be manual)
        history_entry = {
            "cycle_id": len(self.history) + 1,
            "started_at": _utc_now(),
            "agent": worst_agent["agent"],
            "sharpe_before": worst_agent["sharpe"],
            "improvement": improvement,
            "status": "SHADOW_TESTING",  # will be updated to KEPT or REVERTED after 5 days
            "sharpe_after": None,
            "decision": None,
        }
        self.history.append(history_entry)
        _save_json(DARWIN_HISTORY, self.history)

        # Step 5: Apply daily Darwin weight update
        weight_update = self.weight_manager.apply_daily_darwin_update()
        cycle_result["steps"].append({
            "step": "weights_updated",
            "changes": weight_update,
        })

        cycle_result["completed_at"] = _utc_now()
        cycle_result["worst_agent"]  = worst_agent["agent"]
        cycle_result["improvement"]  = improvement
        log.info("Darwin cycle complete. Worst agent: %s — in shadow mode for 5 days.", worst_agent["agent"])
        return cycle_result

    def run_daily_weight_update(self) -> dict:
        """
        Run just the daily weight update (top/bottom quartile adjustment).
        Call this once per day.
        """
        all_sharpes = self.sharpe_calc.compute_all_agents()
        for name, perf in all_sharpes.items():
            self.weight_manager.update_sharpe(
                name, perf["sharpe"], perf["wins"], perf["losses"], perf["total_return"]
            )
        return self.weight_manager.apply_daily_darwin_update()

    def evaluate_shadow_result(self, cycle_id: int, new_sharpe: float) -> str:
        """
        Called after 5-day shadow test.
        Compares new_sharpe vs before. Returns KEPT or REVERTED.
        """
        for entry in self.history:
            if entry["cycle_id"] == cycle_id:
                old_sharpe = entry.get("sharpe_before", 0)
                if new_sharpe > old_sharpe:
                    decision = "KEPT"
                    entry["sharpe_after"] = new_sharpe
                    entry["decision"] = "KEPT"
                    entry["status"] = "KEPT"
                    entry["resolved_at"] = _utc_now()
                    log.info("Darwin: Cycle %d KEPT — Sharpe %.3f → %.3f (improvement)",
                             cycle_id, old_sharpe, new_sharpe)
                else:
                    decision = "REVERTED"
                    entry["sharpe_after"] = new_sharpe
                    entry["decision"] = "REVERTED"
                    entry["status"] = "REVERTED"
                    entry["resolved_at"] = _utc_now()
                    log.info("Darwin: Cycle %d REVERTED — Sharpe %.3f → %.3f (degraded)",
                             cycle_id, old_sharpe, new_sharpe)
                _save_json(DARWIN_HISTORY, self.history)
                return decision
        return "NOT_FOUND"

    def check_agent_spawning(self, recent_debates: list) -> Optional[dict]:
        """
        Scan recent agent debate logs for recurring blind spots.
        If same gap appears 3+ times in 5 days → spawn a new specialist agent.
        """
        gap_counts = {}
        for debate in recent_debates:
            gaps = debate.get("knowledge_gaps", [])
            for gap in gaps:
                gap_counts[gap] = gap_counts.get(gap, 0) + 1

        frequent_gaps = {k: v for k, v in gap_counts.items() if v >= 3}
        if not frequent_gaps:
            return None

        top_gap = max(frequent_gaps, key=frequent_gaps.get)
        new_agent = {
            "name": f"Spawned_{top_gap.replace(' ', '_')[:30]}",
            "spawned_at": _utc_now(),
            "trigger": top_gap,
            "occurrence_count": frequent_gaps[top_gap],
            "weight": 1.0,
            "status": "ACTIVE",
            "description": f"Auto-spawned specialist: {top_gap}",
        }
        self.spawned.append(new_agent)
        _save_json(SPAWNED_AGENTS, self.spawned)
        log.info("Agent spawned: %s (gap detected %dx)", new_agent["name"], frequent_gaps[top_gap])
        return new_agent

    def get_dashboard_data(self) -> dict:
        """Returns all data needed for the Darwin UI dashboard."""
        leaderboard = self.weight_manager.get_leaderboard()
        pending_cycles = [h for h in self.history if h.get("status") == "SHADOW_TESTING"]
        kept_count = sum(1 for h in self.history if h.get("decision") == "KEPT")
        reverted_count = sum(1 for h in self.history if h.get("decision") == "REVERTED")

        return {
            "leaderboard": leaderboard,
            "darwin_history": self.history[-20:],   # last 20 cycles
            "spawned_agents": self.spawned,
            "pending_improvements": pending_cycles,
            "stats": {
                "total_cycles": len(self.history),
                "kept": kept_count,
                "reverted": reverted_count,
                "keep_rate_pct": round(kept_count / max(1, kept_count + reverted_count) * 100, 1),
                "active_spawned": sum(1 for s in self.spawned if s.get("status") == "ACTIVE"),
            },
            "timestamp": _utc_now(),
        }


# ─────────────────────────────────────────────────────────────
# Initialize default weights file if not present
# ─────────────────────────────────────────────────────────────
def initialize_weights():
    """Create initial agent_weights.json with all 25 agents at weight=1.0"""
    mgr = DarwinWeightManager()
    log.info("Initialized weights for %d agents.", len(mgr.weights))
    return mgr.get_all_weights()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys

    onemin_key = os.getenv("ONEMIN_AI_API_KEY", "")
    engine = DarwinEngine(onemin_api_key=onemin_key)

    if "--daily" in sys.argv:
        result = engine.run_daily_weight_update()
        print(json.dumps(result, indent=2, default=str))
    elif "--cycle" in sys.argv:
        result = engine.run_full_cycle()
        print(json.dumps(result, indent=2, default=str))
    elif "--dashboard" in sys.argv:
        result = engine.get_dashboard_data()
        print(json.dumps(result, indent=2, default=str))
    else:
        # Default: show leaderboard
        result = engine.get_dashboard_data()
        print(json.dumps(result["leaderboard"][:5], indent=2, default=str))
        print(f"\nStats: {result['stats']}")
