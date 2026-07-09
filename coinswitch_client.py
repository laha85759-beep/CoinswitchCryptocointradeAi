"""
CoinSwitch Pro — Authenticated REST API Client (Ed25519)
========================================================
Implements the 2026 CoinSwitch Spot API with Ed25519 signing.
Docs: https://api-trading.coinswitch.co
"""

import json
import logging
import time
import urllib.parse

import requests
from cryptography.hazmat.primitives.asymmetric import ed25519

log = logging.getLogger(__name__)

BASE_URL = "https://coinswitch.co"
EXCHANGE_USDT = "c2c1"


class CoinSwitchClient:
    def __init__(self, api_key: str, api_secret: str, rate_limit_delay: float = 1.0):
        self.api_key = api_key
        self.secret = ed25519.Ed25519PrivateKey.from_private_bytes(
            bytes.fromhex(api_secret)
        )
        self.session = requests.Session()
        self.rate_limit_delay = rate_limit_delay
        self._last_request_at = 0.0

    def _sign(self, method: str, path: str, params: dict = None) -> tuple:
        method = method.upper()
        if params:
            qs = urllib.parse.urlencode(sorted(params.items()))
            sep = "&" if "?" in path else "?"
            path = path + sep + qs
        decoded = urllib.parse.unquote_plus(path)
        epoch = str(int(time.time() * 1000))
        message = method + decoded + epoch
        signature = self.secret.sign(message.encode("utf-8")).hex()
        headers = {
            "Content-Type": "application/json",
            "X-AUTH-APIKEY": self.api_key,
            "X-AUTH-SIGNATURE": signature,
            "X-AUTH-EPOCH": epoch,
        }
        return headers, decoded

    def _throttle_request(self) -> None:
        if self.rate_limit_delay <= 0:
            return
        elapsed = time.time() - self._last_request_at
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_at = time.time()

    def _request(
        self, method: str, path: str, params: dict = None, body: dict = None
    ) -> dict:
        self._throttle_request()
        headers, decoded_path = self._sign(method, path, params)
        url = BASE_URL + decoded_path
        try:
            resp = self.session.request(
                method, url, json=body, headers=headers, timeout=15
            )
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            log.error(f"HTTP {resp.status_code} on {method} {path}: {resp.text}")
            raise
        except Exception as e:
            log.error(f"Request error on {method} {path}: {e}")
            raise

    def get_coins(self, exchange: str = EXCHANGE_USDT) -> list:
        """List trading symbols on an exchange."""
        data = self._request("GET", "/trade/api/v2/coins", params={"exchange": exchange})
        return data.get("data", {}).get(exchange, [])

    def get_all_tickers(self, exchange: str = EXCHANGE_USDT) -> dict:
        """24h stats for all symbols on an exchange.
        Returns dict keyed by symbol, e.g. {"BTC/USDT": {...}}.
        """
        data = self._request(
            "GET", "/trade/api/v2/24hr/all-pairs/ticker", params={"exchange": exchange}
        )
        return data.get("data", {})

    def get_all_tickers_multi(self, exchanges: list[str] = None) -> dict:
        """Merge tickers from multiple exchanges."""
        if exchanges is None:
            exchanges = ["c2c1", "c2c2"]
        merged = {}
        for ex in exchanges:
            try:
                tickers = self.get_all_tickers(ex)
                for sym, data in tickers.items():
                    if sym not in merged:
                        merged[sym] = data
                    else:
                        v1 = float(merged[sym].get("quoteVolume", 0) or 0)
                        v2 = float(data.get("quoteVolume", 0) or 0)
                        if v2 > v1:
                            merged[sym] = data
            except Exception as e:
                log.warning(f"Ticker fetch failed for {ex}: {e}")
        return merged

    def get_ticker(self, symbol: str, exchange: str = EXCHANGE_USDT) -> dict:
        """24h stats for a specific symbol."""
        data = self._request(
            "GET", "/trade/api/v2/24hr/ticker",
            params={"exchange": exchange, "symbol": symbol},
        )
        return data.get("data", {}).get(symbol, {})

    def get_ticker_price(self, symbol: str) -> float:
        ticker = self.get_ticker(symbol)
        return float(ticker.get("lastPrice", 0))

    def get_ohlcv(
        self,
        symbol: str,
        interval_minutes: int = 5,
        limit: int = 100,
        exchange: str = EXCHANGE_USDT,
    ) -> list:
        """Historical OHLCV candles.
        interval_minutes: 1, 5, 15, 60, 1440
        """
        end = int(time.time() * 1000)
        start = end - (limit * interval_minutes * 60 * 1000)
        data = self._request(
            "GET", "/trade/api/v2/candles",
            params={
                "exchange": exchange,
                "symbol": symbol,
                "interval": str(interval_minutes),
                "start_time": str(start),
                "end_time": str(end),
            },
        )
        return data.get("data", [])

    @staticmethod
    def _portfolio_balance(item: dict) -> tuple[float, float, float]:
        def _coerce(value) -> float:
            try:
                return float(value) if value is not None else 0.0
            except (TypeError, ValueError):
                return 0.0

        main = item.get("main_balance")
        if main is None:
            main = item.get("available_balance")
        if main is None:
            main = item.get("available")
        if main is None:
            main = item.get("balance")
        if main is None:
            main = item.get("free")

        locked = item.get("locked_balance")
        if locked is None:
            locked = item.get("locked")
        if locked is None:
            locked = item.get("freeze")
        if locked is None:
            locked = item.get("lock")

        available = _coerce(main)
        locked_val = _coerce(locked)
        if item.get("main_balance") is not None and locked is not None and available >= locked_val:
            available = available - locked_val
        return available, locked_val, available + locked_val

    @staticmethod
    def order_fill_status(order: dict) -> tuple[bool, float]:
        status = str(order.get("status", "")).lower()
        if status in {"filled", "completed", "closed", "fully_filled"}:
            return True, 0.0
        if status in {"partially_filled", "partial", "partially filled"}:
            for key in ("filled_quantity", "executed_qty", "filledQty", "quantity_filled"):
                if key in order and order.get(key) is not None:
                    try:
                        return True, float(order.get(key))
                    except (TypeError, ValueError):
                        continue
            return True, 0.0
        return False, 0.0

    def get_portfolio(self) -> list:
        data = self._request("GET", "/trade/api/v2/user/portfolio")
        return data.get("data", [])

    def get_usdt_balance(self) -> float:
        for item in self.get_portfolio():
            if item.get("currency", "").upper() == "USDT":
                available, _, _ = self._portfolio_balance(item)
                return available
        return 0.0

    def get_coin_balance(self, coin: str) -> float:
        for item in self.get_portfolio():
            if item.get("currency", "").upper() == coin.upper():
                available, _, _ = self._portfolio_balance(item)
                return available
        return 0.0

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float = None,
        exchange: str = EXCHANGE_USDT,
    ) -> dict:
        body = {
            "side": side.lower(),
            "symbol": symbol,
            "type": order_type.upper(),
            "quantity": quantity,
            "exchange": exchange,
        }
        if price is not None:
            body["price"] = price
        log.info(f"  Placing {side.upper()} {order_type.upper()} {quantity} {symbol} @ {price or 'LIMIT'}")
        data = self._request("POST", "/trade/api/v2/order", body=body)
        return data.get("data", {})

    def cancel_order(self, order_id: str) -> dict:
        data = self._request("DELETE", "/trade/api/v2/order", body={"order_id": order_id})
        return data.get("data", {})

    def get_order(self, order_id: str) -> dict:
        data = self._request("GET", "/trade/api/v2/order", params={"order_id": order_id})
        return data.get("data", {})

    def get_open_orders(
        self,
        exchange: str = EXCHANGE_USDT,
    ) -> list:
        data = self._request(
            "GET", "/trade/api/v2/orders",
            params={"open": "true", "exchanges": exchange},
        )
        return data.get("data", {}).get("orders", [])
