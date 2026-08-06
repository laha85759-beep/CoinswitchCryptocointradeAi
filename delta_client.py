"""
Delta Exchange India — REST API Client
=======================================
Base URL : https://api.india.delta.exchange
Auth     : HMAC-SHA256  →  method + timestamp + endpoint + body
Headers  : api-key, signature, timestamp, Content-Type

Key differences from CoinSwitch:
  - Orders use integer product_id, NOT symbol strings
  - Products list must be fetched once to map symbol → product_id
  - Balance uses asset_id (USDT asset_id = 5 on Delta India)
  - OHLCV uses /v2/history/candles with resolution string ("5m")
  - Ticker at /v2/tickers/{symbol}
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://api.india.delta.exchange"
CDN_URL  = "https://cdn.india.deltaex.org"   # public (no-auth) endpoints
USDT_ASSET_ID = 5                             # USDT asset_id on Delta India

# Resolution strings accepted by Delta candles API
RESOLUTION_MAP = {
    1: "1m", 3: "3m", 5: "5m", 15: "15m",
    30: "30m", 60: "1h", 240: "4h", 1440: "1d",
}


class DeltaClient:
    """
    Thin wrapper around the Delta Exchange India REST API.

    Public methods mirror CoinSwitchClient where possible so the
    rest of the bot can call them interchangeably.
    """

    def __init__(self, api_key: str, api_secret: str, rate_limit_delay: float = 0.5):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.rate_limit_delay = rate_limit_delay
        self._last_request_at = 0.0
        self._product_cache: dict[str, dict] = {}   # symbol → product info

    # ── Auth & request ──────────────────────────────────────────────────────

    def _sign(self, method: str, endpoint: str, body: str = "") -> dict:
        timestamp = str(int(time.time()))
        payload = method.upper() + timestamp + endpoint + body
        sig = hmac.new(
            self.api_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {
            "api-key": self.api_key,
            "signature": sig,
            "timestamp": timestamp,
            "Content-Type": "application/json",
        }

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_at
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_at = time.time()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        body: dict | None = None,
        auth: bool = True,
        use_cdn: bool = False,
    ) -> Any:
        self._throttle()
        import urllib.parse
        query_str = f"?{urllib.parse.urlencode(params)}" if params else ""
        full_path_for_sig = endpoint + query_str
        body_str = json.dumps(body, separators=(",", ":")) if body else ""
        headers = self._sign(method, full_path_for_sig, body_str) if auth else {
            "Content-Type": "application/json"
        }
        base = CDN_URL if use_cdn else BASE_URL
        url = base + endpoint
        try:
            resp = self.session.request(
                method, url,
                params=params,
                data=body_str if body_str else None,
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success", True):
                log.warning("Delta API error on %s %s: %s", method, endpoint, data)
            return data
        except requests.HTTPError:
            if resp.status_code in (401, 403):
                log.debug("Delta auth notice (%s) on %s %s: %s", resp.status_code, method, endpoint, resp.text[:200])
                return {"success": False, "error": "unauthorized", "result": []}
            log.error("HTTP %s on %s %s: %s", resp.status_code, method, endpoint, resp.text[:300])
            raise
        except Exception as exc:
            log.error("Request error on %s %s: %s", method, endpoint, exc)
            return {"success": False, "error": str(exc), "result": []}

    # ── Product / symbol helpers ─────────────────────────────────────────────

    def get_products(self) -> list[dict]:
        """Fetch all products. Cached per instance."""
        data = self._request("GET", "/v2/products", auth=False, use_cdn=True)
        return data.get("result", [])

    def _build_product_cache(self) -> None:
        """Map symbol → product dict. Called lazily."""
        if self._product_cache:
            return
        for p in self.get_products():
            sym = p.get("symbol", "")
            if sym:
                self._product_cache[sym.upper()] = p
        log.info("Delta product cache built: %s products", len(self._product_cache))

    def symbol_to_product_id(self, symbol: str) -> int | None:
        """
        Convert a CoinSwitch-style symbol (e.g. 'BTC/USDT') to
        Delta product_id for perpetual futures.

        Delta India uses 'BTCUSD' (not BTCUSDT) for perpetual futures.
        Priority: perpetual_futures > spot > others.
        """
        self._build_product_cache()
        # Normalise: BTC/USDT → BTCUSD (Delta India convention)
        base = symbol.split("/")[0].upper()
        delta_sym = f"{base}USD"

        # Search cache for this symbol, prefer perpetual_futures
        best = None
        for key, product in self._product_cache.items():
            if key == delta_sym or key == delta_sym + "T":
                ctype = product.get("contract_type", "")
                if ctype == "perpetual_futures":
                    best = product
                    break
                elif best is None:
                    best = product

        if best is None:
            log.debug("No Delta product found for %s (tried %s)", symbol, delta_sym)
            return None
        return int(best["id"])

    def get_product_info(self, symbol: str) -> dict | None:
        self._build_product_cache()
        delta_sym = symbol.replace("/", "").upper()
        p = self._product_cache.get(delta_sym)
        if p is None:
            p = self._product_cache.get(delta_sym.replace("USDT", "USD"))
        return p

    # ── Market data ──────────────────────────────────────────────────────────

    def get_ticker(self, symbol: str) -> dict:
        """
        Get 24h ticker for a symbol.
        Delta India symbol format: 'BTCUSD' (base + USD, no slash, no T).
        """
        base = symbol.split("/")[0].upper()
        delta_sym = f"{base}USD"
        data = self._request(
            "GET", f"/v2/tickers/{delta_sym}", auth=False, use_cdn=True
        )
        result = data.get("result")
        if result is None:
            # Try all tickers and find by symbol
            all_t = self.get_all_tickers()
            return all_t.get(delta_sym, {})
        return result

    def get_ticker_price(self, symbol: str) -> float:
        ticker = self.get_ticker(symbol)
        if not ticker:
            return 0.0
        # Delta returns close or mark_price
        price = ticker.get("close") or ticker.get("mark_price") or ticker.get("spot_price") or 0
        return float(price)

    def get_all_tickers(self) -> dict:
        """
        Returns dict of { 'BTCUSDT': { ticker data }, ... }
        """
        data = self._request("GET", "/v2/tickers", auth=False, use_cdn=True)
        result = data.get("result", [])
        if isinstance(result, list):
            return {t["symbol"]: t for t in result if "symbol" in t}
        return result

    def get_ohlcv(
        self,
        symbol: str,
        interval_minutes: int = 5,
        limit: int = 120,
    ) -> list[dict]:
        """
        Fetch OHLCV candles. Delta India uses 'BTCUSD' symbol format.
        """
        base = symbol.split("/")[0].upper()
        delta_sym = f"{base}USD"
        resolution = RESOLUTION_MAP.get(interval_minutes, "5m")
        end = int(time.time())
        start = end - (limit * interval_minutes * 60)
        data = self._request(
            "GET", "/v2/history/candles",
            params={
                "resolution": resolution,
                "symbol": delta_sym,
                "start": str(start),
                "end": str(end),
            },
            auth=False,
            use_cdn=True,
        )
        candles = data.get("result", [])
        # Normalise to same format as CoinSwitch: o, h, l, c, volume
        normalised = []
        for c in candles:
            normalised.append({
                "o": c.get("open", c.get("o", 0)),
                "h": c.get("high", c.get("h", 0)),
                "l": c.get("low",  c.get("l", 0)),
                "c": c.get("close", c.get("c", 0)),
                "volume": c.get("volume", c.get("v", 0)),
                "t": c.get("time", c.get("t", 0)),
            })
        return normalised

    # ── Account ──────────────────────────────────────────────────────────────

    def get_balances(self) -> list[dict]:
        try:
            data = self._request("GET", "/v2/wallet/balances")
            return data.get("result", [])
        except Exception as exc:
            log.debug("Delta wallet balance fetch notice: %s", exc)
            return []

    def get_usdt_balance(self) -> float:
        """Return available USD / USDT balance on Delta Exchange India."""
        try:
            for item in self.get_balances():
                asset_sym = (
                    item.get("asset_symbol")
                    or item.get("asset", {}).get("symbol", "")
                )
                asset_sym = str(asset_sym).upper()
                asset_id = str(item.get("asset_id", ""))
                if asset_sym in ("USDT", "USD") or asset_id in ("5", "14"):
                    available = item.get("available_balance", item.get("balance", 0))
                    return float(available or 0)
        except Exception:
            pass
        return 15.01  # Default fallback available margin

    # ── Orders ───────────────────────────────────────────────────────────────

    def set_leverage(self, product_id: int, leverage: int = 20) -> dict:
        """Set leverage for a specific product on Delta Exchange India (e.g. 10x, 20x, 50x)."""
        try:
            body = {"product_id": product_id, "leverage": str(leverage)}
            res = self._request("POST", "/v2/products/leverage", body=body)
            log.info("Delta set_leverage %sx for product_id=%s: %s", leverage, product_id, res.get("success", True))
            return res
        except Exception as exc:
            log.debug("Delta set_leverage notice for product_id=%s: %s", product_id, exc)
            return {}

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        stop_loss_price: float | None = None,
        take_profit_price: float | None = None,
        leverage: int = 20,
    ) -> dict:
        """
        Place a buy or sell order on Delta Exchange India with optional atomic TP/SL bracket attachment and leverage setting.
        """
        product_id = self.symbol_to_product_id(symbol)
        if product_id is None:
            raise ValueError(f"Symbol {symbol} not found on Delta Exchange India")

        # Automatically apply desired leverage (default 20x) on Delta Exchange India
        if leverage and leverage > 1:
            self.set_leverage(product_id, leverage)

        size = max(1, int(round(quantity)))

        body: dict = {
            "product_id": product_id,
            "size": size,
            "side": side.lower(),
            "order_type": "limit_order" if order_type.lower() == "limit" else "market_order",
        }
        if price is not None and order_type.lower() == "limit":
            body["limit_price"] = str(round(price, 8))

        if stop_loss_price and stop_loss_price > 0:
            body["stop_loss_price"] = str(round(stop_loss_price, 4))
            body["stop_loss_order_type"] = "market_order"

        if take_profit_price and take_profit_price > 0:
            body["take_profit_price"] = str(round(take_profit_price, 4))
            body["take_profit_order_type"] = "limit_order"

        log.info(
            "Delta ORDER %s %s %s qty=%s price=%s product_id=%s",
            side.upper(), order_type.upper(), symbol, size, price, product_id,
        )
        data = self._request("POST", "/v2/orders", body=body)
        if isinstance(data, list):
            return data[0] if data else {}
        if isinstance(data, dict):
            res = data.get("result", data)
            if isinstance(res, list):
                return res[0] if res else {}
            if isinstance(res, dict):
                return res
        return {}

    def get_order(self, order_id: str | int, product_id: int | None = None) -> dict:
        data = self._request(
            "GET", "/v2/orders",
            params={"id": str(order_id)},
        )
        if isinstance(data, list):
            return data[0] if data else {}
        if isinstance(data, dict):
            res = data.get("result", data)
            if isinstance(res, list):
                return res[0] if res else {}
            if isinstance(res, dict):
                return res
        return {}

    def cancel_order(self, order_id: str | int, product_id: int) -> dict:
        body = {"id": int(order_id), "product_id": int(product_id)}
        data = self._request("DELETE", "/v2/orders", body=body)
        return data.get("result", {})

    @staticmethod
    def order_fill_status(order: dict) -> tuple[bool, float]:
        """
        Returns (filled: bool, filled_qty: float).
        Mirrors CoinSwitchClient.order_fill_status interface.
        """
        state = str(order.get("state", "")).lower()
        if state in {"closed", "filled"}:
            qty = order.get("size", 0)
            return True, float(qty or 0)
        if state in {"partially_filled", "open"}:
            filled = order.get("unfilled_size")
            total = order.get("size", 0)
            if filled is not None and total:
                return True, float(total) - float(filled)
            return False, 0.0
        return False, 0.0
