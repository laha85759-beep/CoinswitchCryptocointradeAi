"""
JournalIt Institutional Trading Journal Service
===============================================
Inspired by Cursivez/journalit institutional trading journal:
- Setup tags (Breakout, Pullback, Mean Reversion, Liquidity Gap, Ghost SuperTrend, Options Straddle, Trend Follow)
- Psychological emotion tracking (Disciplined, FOMO, Confident, Hesitant, Revenge)
- R-Multiple (Risk:Reward) metric calculations
- Calendar heatmaps and trade analytics
- Multi-user isolation
"""

import logging
import time
from database import (
    get_user_journal_entries,
    add_or_update_journal_entry,
    get_journal_calendar_stats,
    get_db,
)

log = logging.getLogger(__name__)

SETUP_TAGS = [
    "Breakout",
    "Pullback",
    "Mean Reversion",
    "Liquidity Gap",
    "Ghost SuperTrend",
    "Options Straddle",
    "Trend Follow",
    "Scalping",
    "AI Consensus"
]

EMOTION_TAGS = [
    "Disciplined",
    "Confident",
    "Hesitant",
    "FOMO",
    "Revenge",
    "Impatient",
    "Calm"
]


class JournalService:
    """Manages trading journal entries, psychology tags, and performance analytics."""

    @staticmethod
    def get_setup_tags():
        return SETUP_TAGS

    @staticmethod
    def get_emotion_tags():
        return EMOTION_TAGS

    @classmethod
    def get_journal_overview(cls, user_id: int) -> dict:
        entries = get_user_journal_entries(user_id, limit=100)
        calendar = get_journal_calendar_stats(user_id)

        total_trades = len(entries)
        wins = [e for e in entries if float(e.get("pnl") or 0.0) > 0]
        losses = [e for e in entries if float(e.get("pnl") or 0.0) < 0]

        total_pnl = sum(float(e.get("pnl") or 0.0) for e in entries)
        win_rate = round((len(wins) / total_trades * 100), 1) if total_trades > 0 else 0.0

        avg_win = sum(float(e.get("pnl") or 0.0) for e in wins) / max(1, len(wins))
        avg_loss = abs(sum(float(e.get("pnl") or 0.0) for e in losses) / max(1, len(losses)))
        profit_factor = round(avg_win / max(0.01, avg_loss), 2) if losses else round(avg_win, 2)

        r_multiples = [float(e.get("r_multiple") or 0.0) for e in entries if e.get("r_multiple")]
        avg_r = round(sum(r_multiples) / max(1, len(r_multiples)), 2) if r_multiples else 0.0

        # Setup Tag Breakdown
        tag_counts = {}
        for e in entries:
            tag = e.get("setup_tag") or "Other"
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Emotion Breakdown
        emotion_counts = {}
        for e in entries:
            emo = e.get("emotion") or "Calm"
            emotion_counts[emo] = emotion_counts.get(emo, 0) + 1

        return {
            "status": "ok",
            "summary": {
                "total_trades": total_trades,
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": win_rate,
                "total_pnl": round(total_pnl, 2),
                "profit_factor": profit_factor,
                "avg_r_multiple": avg_r,
            },
            "tag_counts": tag_counts,
            "emotion_counts": emotion_counts,
            "calendar": calendar,
            "recent_entries": entries[:30]
        }

    @classmethod
    def save_entry(cls, user_id: int, entry_data: dict) -> dict:
        try:
            entry_id = add_or_update_journal_entry(user_id, entry_data)
            return {"status": "ok", "entry_id": entry_id, "message": "Journal entry saved successfully"}
        except Exception as e:
            log.error("Failed to save journal entry for user %s: %s", user_id, e)
            return {"status": "error", "error": str(e)}

    @classmethod
    def auto_journal_closed_trade(cls, user_id: int, trade_row: dict):
        """Automatically creates a journal entry when a trade is closed."""
        try:
            entry_p = float(trade_row.get("entry_price") or 0.0)
            exit_p = float(trade_row.get("exit_price") or entry_p)
            pnl = float(trade_row.get("realized_pnl") or 0.0)
            sl_p = float(trade_row.get("sl_price") or (entry_p * 0.98))
            risk_unit = abs(entry_p - sl_p) if abs(entry_p - sl_p) > 0 else (entry_p * 0.02)
            r_mult = round(pnl / max(1.0, risk_unit), 2)

            data = {
                "trade_id": trade_row.get("id"),
                "symbol": trade_row.get("symbol", "BTC/USDT"),
                "direction": trade_row.get("direction", "LONG"),
                "entry_price": entry_p,
                "exit_price": exit_p,
                "pnl": pnl,
                "r_multiple": r_mult,
                "setup_tag": trade_row.get("strategy") or "AI Consensus",
                "emotion": "Disciplined",
                "notes": f"Auto-closed by Quant Engine at {exit_p}. Realized P&L: ${pnl:.2f}",
                "trade_date": time.strftime("%Y-%m-%d")
            }
            add_or_update_journal_entry(user_id, data)
        except Exception as e:
            log.warning("Auto journal trade failed: %s", e)
