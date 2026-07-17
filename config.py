"""
Bot Configuration — CoinSwitch Pro (v2 — Momentum + Trailing Stop)
Strategy: Multi-indicator momentum scalping optimised for small capital (₹1000).

Capital philosophy:
  - Max 2 concurrent positions to limit exposure
  - Each trade uses ~40% of free balance (size enough to matter)
  - Hard SL at 1.5% to keep single-trade loss small
  - Trail activates at +1.5% and trails 1.0% below peak
  - TP at 4% — realistic target for momentum moves on 5m candles
  - Daily drawdown cap at 4% to protect capital
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

    # ── Delta Exchange India credentials ─────────────────────────────────────
    "delta_api_key":    os.getenv("DELTA_API_KEY",    ""),
    "delta_api_secret": os.getenv("DELTA_API_SECRET", ""),

    # ── Telegram ─────────────────────────────────────────────────────────────
    "telegram_token":   os.getenv("TELEGRAM_TOKEN",   ""),
    "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),

    # ── Scanner ──────────────────────────────────────────────────────────────
    "quote_currency":        "USDT",
    "exchange":              "c2c2",    # CoinSwitch c2c2 = USDT pairs with candle data
    "request_delay_seconds": 1.0,
    "top_n_by_volume":       80,
    "timeframe":             "5m",
    "candle_limit":          120,      # more candles = better indicator accuracy
    "min_volume_usdt":       50_000,
    "blacklist": ["USDC/USDT", "BUSD/USDT", "TUSD/USDT", "FDUSD/USDT"],

    # ── Legacy scanner thresholds (used by scanner.py SignalEngine) ───────────
    "pump_score_min": 62,
    "dump_score_min": 65,
    "max_signals":     3,

    # ── Capital management ────────────────────────────────────────────────────
    # max_open_trades=2 means max 2 concurrent live positions
    # max_capital_pct=40 means each trade uses 40% of free USDT balance
    "max_capital_pct":  40,
    "max_open_trades":  2,

    # ── Exit strategy: Trailing Stop ──────────────────────────────────────────
    #
    #  For ₹1000 capital, tight stops matter:
    #
    #  hard_sl_pct=1.5   → worst case loss per trade ≈ ₹6 on a ₹400 position
    #  trail_activation  → trail kicks in only after +1.5% profit (avoids noise)
    #  trail_pct=1.0     → trails 1% below peak — gives room to breathe
    #  take_profit=4.0   → captures the move, doesn't chase indefinitely
    #
    #  Example on ₹400 position:
    #    Entry ₹400 → +1.5% profit → trail activates @ ₹406 × (1-1.0%) = ₹401.94
    #    Rises to ₹420 (+5%) → stop at ₹420 × (1-1.0%) = ₹415.80
    #    Drops to ₹416 → EXIT — locked +3.95% = +₹15.80 profit ✅
    #
    "hard_sl_pct":          1.5,   # fixed crash protection
    "trail_activation_pct": 1.5,   # profit % to activate trailing
    "trail_pct":            1.0,   # trail distance below peak

    # ── Signal indicator weights (sum = 100) ──────────────────────────────────
    # Volume spike and momentum weighted highest — best predictors for 5m pumps
    "weights": {
        "ema_cross":    15,
        "rsi":          15,
        "vwap":         15,
        "volume_spike": 25,   # strongest short-term pump predictor
        "momentum":     20,   # 5-candle ROC catches real moves
        "bb_squeeze":   10,
    },

    # ── Multi-agent pipeline settings ─────────────────────────────────────────
    "watchlist":           _watchlist_env(),
    "poll_interval_sec":   _int_env("POLL_INTERVAL_SEC", 900),
    "paper_trading_mode":  _bool_env("PAPER_TRADING_MODE", False),
    "paper_portfolio_usdt": _float_env("PAPER_PORTFOLIO_USDT", 1000.0),

    # ── Signal detector thresholds ────────────────────────────────────────────
    # 5m move ≥ 0.5% = genuine momentum candle (altcoins move 0.5-2% easily)
    # 1h threshold of 1.5% means coin is in a real uptrend
    "pump_change_5m_pct":          _float_env("PUMP_CHANGE_5M_PCT",        0.5),
    "pump_change_1h_pct":          _float_env("PUMP_CHANGE_1H_PCT",        1.5),
    "dump_change_5m_pct":          _float_env("DUMP_CHANGE_5M_PCT",        0.5),
    "dump_change_1h_pct":          _float_env("DUMP_CHANGE_1H_PCT",        1.5),
    # volume_zscore_min=1.0: z-score ≥ 1 is top ~16% of volume — meaningful spike
    "volume_zscore_min":           _float_env("VOLUME_ZSCORE_MIN",         1.0),
    # Synthetic imbalance from OHLCV typically 0.48-0.58 — threshold at 0.52
    "buy_imbalance_min":           _float_env("BUY_IMBALANCE_MIN",         0.52),
    "sell_imbalance_min":          _float_env("SELL_IMBALANCE_MIN",        0.52),
    # trade_frequency_spike_ratio=1.5: volume ratio ≥ 1.5x rolling average
    "trade_frequency_spike_ratio": _float_env("TRADE_FREQ_SPIKE_RATIO",    1.5),
    # watch_condition_count=2: flag for monitoring when 2/4 conditions met
    "watch_condition_count":       _int_env("WATCH_CONDITION_COUNT",       2),

    # ── Risk manager limits ───────────────────────────────────────────────────
    # max_position_pct=40: each trade up to 40% of portfolio → ~$40 per trade
    # max_total_exposure=70: both trades together = up to 70% → ~$70 deployed
    "max_position_pct":         _float_env("MAX_POSITION_PCT",          40.0),
    "max_total_exposure_pct":   _float_env("MAX_TOTAL_EXPOSURE_PCT",    70.0),
    "max_trades_per_hour":      _int_env("MAX_TRADES_PER_HOUR",          3),
    # min_confidence=0.30: allows moderate-confidence signals through
    "min_confidence":           _float_env("MIN_CONFIDENCE",             0.30),
    "stop_loss_pct":            _float_env("STOP_LOSS_PCT",              1.5),
    "take_profit_pct":          _float_env("TAKE_PROFIT_PCT",            4.0),
    # daily_max_drawdown=4%: on $100 that's $4 max daily loss before halt
    "daily_max_drawdown_pct":   _float_env("DAILY_MAX_DRAWDOWN_PCT",     4.0),
    "min_liquidity_usd":        _float_env("MIN_LIQUIDITY_USD",     100_000.0),
    "min_order_usdt":           _float_env("MIN_ORDER_USDT",             10.0),
    "risk_order_type":          os.getenv("RISK_ORDER_TYPE",           "limit"),

    # ── Execution settings ────────────────────────────────────────────────────
    # slippage_tolerance=2.0%: allow up to 2% price movement between signal
    # and execution — 15min GitHub Actions cycle means price can move
    "slippage_tolerance_pct":       _float_env("SLIPPAGE_TOLERANCE_PCT",    2.0),
    "limit_slippage_offset_pct":    _float_env("LIMIT_SLIPPAGE_OFFSET_PCT", 0.3),
    "max_retries":                  _int_env("MAX_RETRIES",                   3),
    "circuit_breaker_error_limit":  _int_env("CIRCUIT_BREAKER_ERROR_LIMIT",   5),
}
