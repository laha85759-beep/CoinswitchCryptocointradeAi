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
    "api_key":    os.getenv("CS_API_KEY",    "d75f998ed6d14f67459f9d52c312d1f91bc7da4e5a246e8ae58f8c33e6e6850a"),
    "api_secret": os.getenv("CS_API_SECRET", "57e0867584c4835cc24ca8c12f281d7c588c51fb27ef8fd68faa74a5c8b72140"),

    # ── Delta Exchange India credentials ─────────────────────────────────────
    "delta_api_key":    os.getenv("DELTA_API_KEY",    "vjEEk2mwin1lwPM862AJeRPbTVSZGC"),
    "delta_api_secret": os.getenv("DELTA_API_SECRET", "4mv1fEWHjwuLz1pcpoqP5pxKC5XpylzsMuOqDTU74kBl309h1yuQKasGNEeV"),

    # ── Telegram ─────────────────────────────────────────────────────────────
    "telegram_token":   os.getenv("TELEGRAM_TOKEN",   "8802671362:AAGJQdrqAnI4aVuuH3sxqwetBv9F35m_2V8"),
    "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", "6207722743"),

    # ── 1min.AI Multi-Model AI API ───────────────────────────────────────────
    "onemin_ai_api_key": os.getenv("ONEMIN_AI_API_KEY", "5bbdd65d81492ca76dba5f864a7f0125e1bc0a2f6801c3a8134696d28327ffcd"),

    # ── Scanner ──────────────────────────────────────────────────────────────
    "quote_currency":        "USDT",
    "exchange":              "c2c2",    # CoinSwitch c2c2 = USDT pairs with candle data
    "request_delay_seconds": 0.5,
    "top_n_by_volume":       150,     # scans all top active & newly listed coins
    "timeframe":             "5m",
    "candle_limit":          50,       # 50 candles for 5m indicators
    "min_volume_usdt":       100.0,    # Lower volume filter to catch explosive low-cap memecoins & new listings
    "priority_memecoins": [
        "PEPE/USDT", "DOGE/USDT", "SHIB/USDT", "WIF/USDT", "BONK/USDT", "FLOKI/USDT",
        "MOODENG/USDT", "PUMP/USDT", "FARTCOIN/USDT", "ZRO/USDT", "SPX/USDT", "POPCAT/USDT",
        "GOAT/USDT", "GRIFFAIN/USDT", "TRUMP/USDT", "VIRTUAL/USDT", "AIXBT/USDT", "HYPE/USDT",
        "ONDO/USDT", "OM/USDT", "PENDLE/USDT", "LINK/USDT", "AVAX/USDT", "MKR/USDT", "CTC/USDT",
        "SOL/USDT", "NEAR/USDT", "SUI/USDT", "APT/USDT", "TIA/USDT"
    ],
    "blacklist": ["BTC/USDT", "BTC/INR", "ETH/USDT", "ETH/INR", "USDC/USDT", "BUSD/USDT", "TUSD/USDT", "FDUSD/USDT"],

    # ── Legacy scanner thresholds (used by scanner.py SignalEngine) ───────────
    "pump_score_min": 62,
    "dump_score_min": 65,
    "max_signals":     3,

    # ── Capital management ────────────────────────────────────────────────────
    # max_open_trades=2 means max 2 concurrent live positions
    # max_capital_pct=40 means each trade uses 40% of free USDT balance
    "max_capital_pct":  40,
    "max_open_trades":  10,    # allow up to 10 concurrent live positions across exchanges

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
    "hard_sl_pct":          2.0,   # fixed crash protection (backtested optimal)
    "trail_activation_pct": 1.5,   # profit % to activate trailing
    "trail_pct":            1.0,   # trail distance below peak

    # ── Signal indicator weights (sum = 100) ──────────────────────────────────
    # Volume spike and momentum weighted highest — best predictors for 5m pumps
    "weights": {
        "pp_supertrend_ghost": 25,   # Pivot Point SuperTrend + Ghost Protocol V3
        "liquidity_gap_run":   25,   # SMC Liquidity Gap & Liquidity Run Strategy
        "ema_cross":           10,
        "rsi":                 10,
        "vwap":                15,
        "volume_spike":        15,   # strongest short-term pump predictor
    },

    # ── Consolidation + Breakout Strategy ──────────────────────────────────────
    # Looks for coins consolidating 1-2 days, trades the breakout.
    # Uses 1h candles for consolidation detection + 5m for entry timing.
    "consolidation_lookback_hours":    48,   # 2-day lookback window
    "consolidation_range_max_pct":    4.0,   # max price range % during consolidation
    "bb_squeeze_percentile":          20,    # BB width must be ≤ 20th pctl → squeeze
    "breakout_volume_multiplier":     1.8,   # volume must be ≥ 1.8× avg for confirmation
    "trendline_breakout_enabled":    True,   # also detect trendline breakouts
    "consolidation_breakout_score_min": 0.55, # min confidence to approve breakout trade

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
    # Backtested optimal: max_position_pct=20 reduces risk per trade
    "max_position_pct":         _float_env("MAX_POSITION_PCT",          75.0),  # ~$10.50 / ₹924 INR position size (clears CoinSwitch $10 min quote filter)
    "max_total_exposure_pct":   _float_env("MAX_TOTAL_EXPOSURE_PCT",    98.0),
    "max_trades_per_hour":      _int_env("MAX_TRADES_PER_HOUR",         10),
    # min_confidence=0.50: ensures high-probability momentum breakout signals only
    "min_confidence":           _float_env("MIN_CONFIDENCE",             0.50),
    "stop_loss_pct":            _float_env("STOP_LOSS_PCT",              1.5),  # Optimal -1.5% SL for momentum breakouts
    "take_profit_pct":          _float_env("TAKE_PROFIT_PCT",            4.8),  # High +4.8% TP (1:3+ Risk-Reward ratio)
    "scalp_lot_multiplier":     _float_env("SCALP_LOT_MULTIPLIER",       2.5),  # QuickScalpAgent uses 2.5x larger lot size
    # daily_max_drawdown=4%: on $100 that's $4 max daily loss before halt
    "daily_max_drawdown_pct":   _float_env("DAILY_MAX_DRAWDOWN_PCT",     4.0),
    "min_liquidity_usd":        _float_env("MIN_LIQUIDITY_USD",      10_000.0),
    "min_order_usdt":           _float_env("MIN_ORDER_USDT",             0.05),
    "risk_order_type":          os.getenv("RISK_ORDER_TYPE",           "market"),

    # ── Execution settings ────────────────────────────────────────────────────
    # slippage_tolerance=3.5%: allow up to 3.5% price movement between signal
    # and execution — 15min GitHub Actions cycle means price can move
    "slippage_tolerance_pct":       _float_env("SLIPPAGE_TOLERANCE_PCT",    3.5),
    "limit_slippage_offset_pct":    _float_env("LIMIT_SLIPPAGE_OFFSET_PCT", 0.3),
    "max_retries":                  _int_env("MAX_RETRIES",                   3),
    "circuit_breaker_error_limit":  _int_env("CIRCUIT_BREAKER_ERROR_LIMIT",   5),

    # ── Short Selling ─────────────────────────────────────────────────────────
    "short_selling_enabled": _bool_env("SHORT_SELLING_ENABLED", True),
    "short_exchanges": ["delta"],

    # ── Options Hedge Agent ───────────────────────────────────────────────────
    "options_enabled":         _bool_env("OPTIONS_ENABLED", True),
    "options_assets":          ["ETH", "BTC", "XAUT", "SOL", "XRP", "DOGE", "MNT"],
    "options_stop_loss_pct":   _float_env("OPTIONS_STOP_LOSS_PCT", 50.0),   # -50% SL on options premium
    "options_take_profit_pct": _float_env("OPTIONS_TAKE_PROFIT_PCT", 100.0), # +100% TP on options premium
}

# ── Isolate proxy configuration to prevent affecting other clients (CoinSwitch / Telegram) ──
CONFIG["http_proxy"] = os.environ.pop("HTTP_PROXY", os.environ.pop("http_proxy", None))
CONFIG["https_proxy"] = os.environ.pop("HTTPS_PROXY", os.environ.pop("https_proxy", None))

# ── Load config override if exists ──
_override_path = os.path.join(os.path.dirname(__file__), "config_override.json")
if os.path.isfile(_override_path):
    try:
        with open(_override_path) as _f:
            import json
            _overrides = json.load(_f)
            CONFIG.update(_overrides)
    except Exception:
        pass




