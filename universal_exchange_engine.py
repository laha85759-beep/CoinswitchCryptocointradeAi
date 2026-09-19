"""
Universal Multi-Exchange Engine (CCXT Integration)
===================================================
Provides unified API access to 100+ cryptocurrency exchanges:
- Binance, Bybit, OKX, Bitget, KuCoin, Gate.io, Coinbase, MEXC, Kraken, etc.
- Unified methods for balances, tickers, orders, and position management.
- Multi-tenant credential isolation per user.
"""

import logging
import ccxt
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


class UniversalExchangeEngine:
    """Manages connections to CCXT supported exchanges per user."""

    @staticmethod
    def get_supported_exchanges():
        return SUPPORTED_EXCHANGES

    @staticmethod
    def get_exchange_instance(user_id: int, exchange_id: str):
        keys = get_ccxt_exchange_keys(user_id, exchange_id)
        if not keys or not keys[0].get("api_key"):
            return None, "API credentials not configured for exchange"

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
                }
            }
        except Exception as e:
            log.error("CCXT fetch_balance error for %s (user %s): %s", exchange_id, user_id, e)
            return {"status": "error", "error": str(e), "exchange": exchange_id}

    @classmethod
    def create_order(cls, user_id: int, exchange_id: str, symbol: str, side: str, order_type: str, amount: float, price: float = None) -> dict:
        exchange, err = cls.get_exchange_instance(user_id, exchange_id)
        if err:
            return {"status": "error", "error": err}

        try:
            norm_symbol = symbol.replace("-", "/").upper()
            if "/" not in norm_symbol and "USDT" in norm_symbol:
                norm_symbol = norm_symbol.replace("USDT", "/USDT")

            params = {}
            res = exchange.create_order(norm_symbol, order_type.lower(), side.lower(), amount, price, params)
            return {
                "status": "filled" if res.get("status") in ["closed", "filled"] else "open",
                "order_id": str(res.get("id")),
                "symbol": norm_symbol,
                "side": side,
                "price": float(res.get("price") or price or 0.0),
                "amount": float(res.get("amount") or amount),
                "exchange": exchange_id
            }
        except Exception as e:
            log.error("CCXT create_order error on %s: %s", exchange_id, e)
            return {"status": "error", "error": str(e), "exchange": exchange_id}

    @classmethod
    def fetch_ticker(cls, exchange_id: str, symbol: str) -> dict:
        try:
            if not hasattr(ccxt, exchange_id):
                return {"status": "error", "error": "Unknown exchange"}
            exchange = getattr(ccxt, exchange_id)({"enableRateLimit": True})
            norm_symbol = symbol.replace("-", "/").upper()
            if "/" not in norm_symbol and "USDT" in norm_symbol:
                norm_symbol = norm_symbol.replace("USDT", "/USDT")
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
                "exchange": exchange_id
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
