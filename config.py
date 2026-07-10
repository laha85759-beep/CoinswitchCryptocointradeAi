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


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _watchlist_env() -> list[str]:
    raw = os.getenv("WATCHLIST", "").strip()
    return [x.strip().upper() for x in raw.split(",") if x.strip()]

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

    # Multi-agent app settings from the prompt spec. Paper trading defaults to
    # true; set PAPER_TRADING_MODE=false only after deliberate live validation.
    "watchlist": _watchlist_env(),
    "poll_interval_sec": _int_env("POLL_INTERVAL_SEC", 900),
    "paper_trading_mode": _bool_env("PAPER_TRADING_MODE", True),
    "paper_portfolio_usdt": _float_env("PAPER_PORTFOLIO_USDT", 1000.0),

    # Data Collector / Signal Detector thresholds.
    "pump_change_5m_pct": _float_env("PUMP_CHANGE_5M_PCT", 5.0),
    "pump_change_1h_pct": _float_env("PUMP_CHANGE_1H_PCT", 10.0),
    "dump_change_5m_pct": _float_env("DUMP_CHANGE_5M_PCT", 5.0),
    "dump_change_1h_pct": _float_env("DUMP_CHANGE_1H_PCT", 10.0),
    "volume_zscore_min": _float_env("VOLUME_ZSCORE_MIN", 3.0),
    "buy_imbalance_min": _float_env("BUY_IMBALANCE_MIN", 0.65),
    "sell_imbalance_min": _float_env("SELL_IMBALANCE_MIN", 0.65),
    "trade_frequency_spike_ratio": _float_env("TRADE_FREQ_SPIKE_RATIO", 2.0),
    "watch_condition_count": _int_env("WATCH_CONDITION_COUNT", 2),

    # Risk Manager hard limits.
    "max_position_pct": _float_env("MAX_POSITION_PCT", 2.0),
    "max_total_exposure_pct": _float_env("MAX_TOTAL_EXPOSURE_PCT", 15.0),
    "max_trades_per_hour": _int_env("MAX_TRADES_PER_HOUR", 2),
    "min_confidence": _float_env("MIN_CONFIDENCE", 0.7),
    "stop_loss_pct": _float_env("STOP_LOSS_PCT", 3.0),
    "take_profit_pct": _float_env("TAKE_PROFIT_PCT", 6.0),
    "daily_max_drawdown_pct": _float_env("DAILY_MAX_DRAWDOWN_PCT", 5.0),
    "min_liquidity_usd": _float_env("MIN_LIQUIDITY_USD", 1_000_000.0),
    "min_order_usdt": _float_env("MIN_ORDER_USDT", 10.0),
    "risk_order_type": os.getenv("RISK_ORDER_TYPE", "limit"),

    # Execution Agent / orchestration controls.
    "slippage_tolerance_pct": _float_env("SLIPPAGE_TOLERANCE_PCT", 1.0),
    "limit_slippage_offset_pct": _float_env("LIMIT_SLIPPAGE_OFFSET_PCT", 0.5),
    "max_retries": _int_env("MAX_RETRIES", 2),
    "circuit_breaker_error_limit": _int_env("CIRCUIT_BREAKER_ERROR_LIMIT", 3),
}
