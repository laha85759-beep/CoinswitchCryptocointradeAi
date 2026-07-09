"""
Bot Configuration — CoinSwitch Pro (v2 — Trailing Stop)
Secrets loaded from .env file or environment variables.
"""
import os

# ── Load .env file if present (for local development) ─────────────────────
_dotenv = os.path.join(os.path.dirname(__file__), ".env")
if os.path.isfile(_dotenv):
    with open(_dotenv) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

CONFIG = {
    # ── CoinSwitch Pro credentials ───────────────────────────────────────────
    "api_key":    os.getenv("CS_API_KEY",    ""),
    "api_secret": os.getenv("CS_API_SECRET", ""),

    # ── Telegram ─────────────────────────────────────────────────────────────
    "telegram_token":   os.getenv("TELEGRAM_TOKEN",   ""),
    "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),

    # ── Scanner ──────────────────────────────────────────────────────────────
    "quote_currency":   "USDT",
    "request_delay_seconds": 1.0,
    "top_n_by_volume":  80,
    "timeframe":        "5m",
    "candle_limit":     100,
    "min_volume_usdt":  1_000_000,
    "blacklist": ["USDC/USDT", "BUSD/USDT", "TUSD/USDT", "FDUSD/USDT"],

    # ── Signal thresholds ────────────────────────────────────────────────────
    "pump_score_min":  65,
    "dump_score_min":  70,
    "max_signals":     2,

    # ── Capital ──────────────────────────────────────────────────────────────
    "max_capital_pct":  50,
    "max_open_trades":  2,

    # ── Exit Strategy: Trailing Stop ─────────────────────────────────────────
    #
    #   HARD SL   : Fixed % below entry. Protects against sudden crash.
    #               Exits immediately if price drops this much from entry.
    #
    #   TRAIL ACTIVATION : Trailing stop only activates once you are
    #               this much IN PROFIT. Before that, hard SL protects.
    #
    #   TRAIL PCT  : Once activated, the stop trails this % below the
    #               highest price seen. Rides the trend, locks profit.
    #
    # Example (trail_activation=1.0%, trail_pct=0.8%):
    #   Entry  = ₹100
    #   +1.0%  → ₹101  → trailing stop ACTIVATES at ₹101 × (1-0.8%) = ₹100.19
    #   +3.0%  → ₹103  → trailing stop moves up to ₹103 × (1-0.8%) = ₹102.18
    #   +6.0%  → ₹106  → trailing stop = ₹106 × (1-0.8%) = ₹105.15
    #   Drops to ₹105  → EXIT — locked +5% profit instead of fixed 1.5% ✅
    #
    "hard_sl_pct":          0.8,    # % below entry — hard stop (crash protection)
    "trail_activation_pct": 1.0,    # % profit needed to activate trailing stop
    "trail_pct":            0.8,    # % the stop trails below the peak price

    # ── Signal weights ────────────────────────────────────────────────────────
    "weights": {
        "ema_cross":    20,
        "rsi":          20,
        "vwap":         15,
        "volume_spike": 20,
        "momentum":     15,
        "bb_squeeze":   10,
    },
}
