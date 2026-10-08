"""
Universal Multi-Exchange Engine (CCXT Integration)
===================================================
Provides unified API access to 100+ cryptocurrency exchanges:
- Binance, Bybit, OKX, Bitget, KuCoin, Gate.io, Coinbase, MEXC, Kraken, etc.
- Unified methods for balances, tickers, orders, position management, and TP/SL.
- Multi-tenant credential isolation per user.
"""

import logging
try:
    import ccxt
except ImportError:
    ccxt = None
from database import get_ccxt_exchange_keys

log = logging.getLogger(__name__)

SUPPORTED_EXCHANGES = [
    {"id": "binance", "name": "Binance Global", "type": "spot_derivatives"},
    {"id": "bybit", "name": "Bybit", "type": "derivatives"},
    {"id": "okx", "name": "OKX", "type": "spot_derivatives"},
    {"id": "bitget", "name": "Bitget", "type": "derivatives"},
    {"id": "kucoin", "name": "KuCoin", "type": "spot_derivatives"},
    {"id": "gateio", "name": "Gate.io", "type": "spot_derivatives"},
    {"id": "coinbase", "name": "Coinbase Advanced", "type": "spot"},
    {"id": "mexc", "name": "MEXC Global", "type": "spot_derivatives"},
    {"id": "kraken", "name": "Kraken", "type": "spot_derivatives"},
    {"id": "htx", "name": "HTX (Huobi)", "type": "spot_derivatives"},
]

# Exchanges that support native TP/SL order params via CCXT
_TP_SL_SUPPORTED = {"bybit", "okx", "bitget", "binance", "mexc", "gateio", "htx"}


class UniversalExchangeEngine:
    """Manages connections to CCXT supported exchanges per user."""

    @staticmethod
    def get_supported_exchanges():
        return SUPPORTED_EXCHANGES

    @staticmethod
    def _norm_symbol(symbol: str) -> str:
        """
        Normalise symbol across all asset classes:
        - Crypto: BTC/USDT, ETH/USDT, SOL/USDT
        - Commodities: XAU/USD (Gold), XAG/USD (Silver), BRENT/USD (Oil)
        - US Indices: US30/USD (Dow 30), US100/USD (Nasdaq 100), SPX500/USD (S&P 500)
        - Forex: EUR/USD, GBP/USD, USD/JPY
        """
        norm = symbol.replace("-", "/").strip().upper()
        # Aliases for US Indices
        index_map = {
            "US30": "US30/USD",
            "DJI": "US30/USD",
            "WS30": "US30/USD",
            "US100": "US100/USD",
            "NAS100": "US100/USD",
            "USTECH": "US100/USD",
            "NDX": "US100/USD",
            "SPX": "SPX500/USD",
            "SP500": "SPX500/USD",
            "US500": "SPX500/USD",
            "GOLD": "XAU/USD",
            "XAUUSD": "XAU/USD",
            "SILVER": "XAG/USD",
            "XAGUSD": "XAG/USD",
            "OIL": "WTI/USD",
            "CRUDE": "WTI/USD",
        }
        if norm in index_map:
            return index_map[norm]

        if "/" not in norm:
            if norm.endswith("USDT"):
                norm = norm[:-4] + "/USDT"
            elif norm.endswith("USD"):
                norm = norm[:-3] + "/USD"
            elif norm.endswith("INR"):
                norm = norm[:-3] + "/INR"

        return norm

    @staticmethod
    def get_exchange_instance(user_id: int, exchange_id: str):
        """Return (exchange_instance, error_str) for a user's CCXT exchange."""
        if ccxt is None:
            return None, "CCXT library not installed. Run: pip install ccxt"

        keys = get_ccxt_exchange_keys(user_id, exchange_id)
        if not keys or not keys[0].get("api_key"):
            return None, f"API credentials not configured for {exchange_id}"

        k = keys[0]
        if not hasattr(ccxt, exchange_id):
            return None, f"Exchange '{exchange_id}' not supported in CCXT"

        exchange_class = getattr(ccxt, exchange_id)
        config = {
            "apiKey": k["api_key"],
            "secret": k["api_secret"],
            "enableRateLimit": True,
            "timeout": 15000,
        }
        if k.get("password"):
            config["password"] = k["password"]
        if k.get("is_sandbox"):
            config["sandbox"] = True

        try:
            exchange = exchange_class(config)
            return exchange, None
        except Exception as e:
            log.error("Failed to initialize CCXT %s for user %s: %s", exchange_id, user_id, e)
            return None, str(e)

    @classmethod
    def fetch_balance(cls, user_id: int, exchange_id: str) -> dict:
        exchange, err = cls.get_exchange_instance(user_id, exchange_id)
        if err:
            return {"status": "error", "error": err, "exchange": exchange_id}

        try:
            balance = exchange.fetch_balance()
            total_usdt = balance.get("total", {}).get("USDT", 0.0)
            free_usdt = balance.get("free", {}).get("USDT", 0.0)
            return {
                "status": "ok",
                "exchange": exchange_id,
                "total_usdt": float(total_usdt or 0.0),
                "free_usdt": float(free_usdt or 0.0),
                "currencies": {
                    k: v for k, v in balance.get("total", {}).items() if float(v or 0) > 0.0001
                },
            }
        except Exception as e:
            log.error("CCXT fetch_balance error for %s (user %s): %s", exchange_id, user_id, e)
            return {"status": "error", "error": str(e), "exchange": exchange_id}

    @classmethod
    def create_order(
        cls,
        user_id: int,
        exchange_id: str,
        symbol: str,
        side: str,
        order_type: str,
        amount: float,
        price: float = None,
        stop_loss_price: float = None,
        take_profit_price: float = None,
        leverage: int = None,
    ) -> dict:
        """
        Place a buy/sell order on a CCXT exchange with optional TP/SL and leverage.
        TP/SL is attached natively where supported (Bybit, OKX, Bitget, Binance Futures,
        MEXC, Gate.io, HTX). For other exchanges, TP/SL are stored as metadata only.
        """
        exchange, err = cls.get_exchange_instance(user_id, exchange_id)
        if err:
            return {"status": "error", "error": err}

        try:
            norm_symbol = cls._norm_symbol(symbol)

            # Set leverage if requested and supported
            if leverage and leverage > 1:
                try:
                    exchange.set_leverage(leverage, norm_symbol)
                except Exception as lev_err:
                    log.debug("Set leverage notice on %s: %s", exchange_id, lev_err)

            # Build exchange-specific TP/SL params
            params = {}
            if exchange_id in _TP_SL_SUPPORTED:
                if stop_loss_price and stop_loss_price > 0:
                    if exchange_id == "bybit":
                        params["stopLoss"] = {"triggerPrice": str(stop_loss_price), "type": "market"}
                    elif exchange_id == "okx":
                        params["slTriggerPx"] = str(stop_loss_price)
                        params["slOrdPx"] = "-1"  # market SL
                    elif exchange_id == "bitget":
                        params["presetStopLossPrice"] = str(stop_loss_price)
                    elif exchange_id in ("binance", "mexc", "gateio", "htx"):
                        params["stopLossPrice"] = str(stop_loss_price)

                if take_profit_price and take_profit_price > 0:
                    if exchange_id == "bybit":
                        params["takeProfit"] = {"triggerPrice": str(take_profit_price), "type": "limit", "price": str(take_profit_price)}
                    elif exchange_id == "okx":
                        params["tpTriggerPx"] = str(take_profit_price)
                        params["tpOrdPx"] = str(take_profit_price)
                    elif exchange_id == "bitget":
                        params["presetTakeProfitPrice"] = str(take_profit_price)
                    elif exchange_id in ("binance", "mexc", "gateio", "htx"):
                        params["takeProfitPrice"] = str(take_profit_price)

            res = exchange.create_order(norm_symbol, order_type.lower(), side.lower(), amount, price, params)
            return {
                "status": "filled" if res.get("status") in ["closed", "filled"] else "open",
                "order_id": str(res.get("id", "")),
                "symbol": norm_symbol,
                "side": side,
                "price": float(res.get("price") or price or 0.0),
                "amount": float(res.get("amount") or amount),
                "exchange": exchange_id,
                "sl_price": stop_loss_price,
                "tp_price": take_profit_price,
                "leverage": leverage,
            }
        except Exception as e:
            log.error("CCXT create_order error on %s: %s", exchange_id, e)
            return {"status": "error", "error": str(e), "exchange": exchange_id}

    @classmethod
    def close_position(
        cls,
        user_id: int,
        exchange_id: str,
        symbol: str,
        side: str,
        amount: float,
    ) -> dict:
        """
        Close an open position by placing the opposite market order.
        side should be the ORIGINAL position side ("buy" -> places sell to close).
        """
        close_side = "sell" if str(side).lower() in ("buy", "long") else "buy"
        return cls.create_order(
            user_id=user_id,
            exchange_id=exchange_id,
            symbol=symbol,
            side=close_side,
            order_type="market",
            amount=amount,
        )

    @classmethod
    def fetch_open_positions(cls, user_id: int, exchange_id: str) -> dict:
        """Fetch all open positions from a CCXT futures/derivatives exchange."""
        exchange, err = cls.get_exchange_instance(user_id, exchange_id)
        if err:
            return {"status": "error", "error": err, "positions": []}

        try:
            positions = exchange.fetch_positions()
            open_pos = [
                {
                    "symbol": p.get("symbol", ""),
                    "side": p.get("side", ""),
                    "size": float(p.get("contracts") or p.get("size") or 0),
                    "entry_price": float(p.get("entryPrice") or 0),
                    "mark_price": float(p.get("markPrice") or 0),
                    "unrealized_pnl": float(p.get("unrealizedPnl") or 0),
                    "leverage": float(p.get("leverage") or 1),
                    "exchange": exchange_id,
                }
                for p in (positions or [])
                if float(p.get("contracts") or p.get("size") or 0) != 0
            ]
            return {"status": "ok", "exchange": exchange_id, "positions": open_pos}
        except Exception as e:
            log.error("CCXT fetch_positions error for %s: %s", exchange_id, e)
            return {"status": "error", "error": str(e), "positions": []}

    @classmethod
    def fetch_open_orders(cls, user_id: int, exchange_id: str, symbol: str = None) -> dict:
        """Fetch all open orders from a CCXT exchange, optionally filtered by symbol."""
        exchange, err = cls.get_exchange_instance(user_id, exchange_id)
        if err:
            return {"status": "error", "error": err, "orders": []}

        try:
            norm_symbol = cls._norm_symbol(symbol) if symbol else None
            orders = exchange.fetch_open_orders(norm_symbol)
            return {
                "status": "ok",
                "exchange": exchange_id,
                "orders": [
                    {
                        "order_id": str(o.get("id", "")),
                        "symbol": o.get("symbol", ""),
                        "side": o.get("side", ""),
                        "type": o.get("type", ""),
                        "amount": float(o.get("amount") or 0),
                        "price": float(o.get("price") or 0),
                        "status": o.get("status", ""),
                    }
                    for o in (orders or [])
                ],
            }
        except Exception as e:
            log.error("CCXT fetch_open_orders error for %s: %s", exchange_id, e)
            return {"status": "error", "error": str(e), "orders": []}

    @classmethod
    def fetch_ticker(cls, exchange_id: str, symbol: str) -> dict:
        """Fetch ticker for a symbol (public, no auth required)."""
        try:
            if ccxt is None:
                return {"status": "error", "error": "CCXT not installed"}
            if not hasattr(ccxt, exchange_id):
                return {"status": "error", "error": f"Unknown exchange '{exchange_id}'"}
            exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})
            norm_symbol = cls._norm_symbol(symbol)
            ticker = exchange.fetch_ticker(norm_symbol)
            return {
                "status": "ok",
                "symbol": norm_symbol,
                "last": float(ticker.get("last") or 0.0),
                "bid": float(ticker.get("bid") or 0.0),
                "ask": float(ticker.get("ask") or 0.0),
                "high24h": float(ticker.get("high") or 0.0),
                "low24h": float(ticker.get("low") or 0.0),
                "volume24h": float(ticker.get("baseVolume") or 0.0),
                "exchange": exchange_id,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
