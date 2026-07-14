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
        body_str = json.dumps(body, separators=(",", ":")) if body else ""
        headers = self._sign(method, endpoint, body_str) if auth else {
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
            log.error("HTTP %s on %s %s: %s", resp.status_code, method, endpoint, resp.text[:300])
            raise
        except Exception as exc:
            log.error("Request error on %s %s: %s", method, endpoint, exc)
            raise

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
        Delta product_id.  Tries both 'BTCUSDT' and 'BTCUSD' forms.
        """
        self._build_product_cache()
        # Normalise CoinSwitch "BTC/USDT" → "BTCUSDT"
        delta_sym = symbol.replace("/", "").upper()
        # Try direct match first
        product = self._product_cache.get(delta_sym)
        # Fallback: strip T from USDT → BTCUSD
        if product is None:
            alt = delta_sym.replace("USDT", "USD")
            product = self._product_cache.get(alt)
        if product is None:
            log.debug("No Delta product found for %s", symbol)
            return None
        return int(product["id"])

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
        Delta symbol format: 'BTCUSDT' (no slash).
        """
        delta_sym = symbol.replace("/", "").upper()
        data = self._request(
            "GET", f"/v2/tickers/{delta_sym}", auth=False, use_cdn=True
        )
        return data.get("result", {})

    def get_ticker_price(self, symbol: str) -> float:
        ticker = self.get_ticker(symbol)
        price = ticker.get("close") or ticker.get("mark_price") or 0
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
        Fetch OHLCV candles.
        Returns list of dicts with keys: o, h, l, c, v, t (timestamp).
        """
        delta_sym = symbol.replace("/", "").upper()
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
        data = self._request("GET", "/v2/wallet/balances")
        return data.get("result", [])

    def get_usdt_balance(self) -> float:
        """Return available USDT balance."""
        for item in self.get_balances():
            asset = item.get("asset", {})
            if (
                asset.get("symbol", "").upper() == "USDT"
                or str(item.get("asset_id", "")) == str(USDT_ASSET_ID)
            ):
                available = item.get("available_balance", item.get("balance", 0))
                return float(available or 0)
        return 0.0

    # ── Orders ───────────────────────────────────────────────────────────────

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
    ) -> dict:
        """
        Place a buy or sell order on Delta Exchange India.

        quantity is in base-asset units (same as CoinSwitch).
        Returns the order dict from Delta API.
        """
        product_id = self.symbol_to_product_id(symbol)
        if product_id is None:
            raise ValueError(f"Symbol {symbol} not found on Delta Exchange India")

        # Delta uses integer size (contracts). For spot/perp, 1 contract = 1 unit.
        # We round to avoid fractional contract errors.
        size = max(1, int(round(quantity)))

        body: dict = {
            "product_id": product_id,
            "size": size,
            "side": side.lower(),
            "order_type": "limit_order" if order_type.lower() == "limit" else "market_order",
        }
        if price is not None and order_type.lower() == "limit":
            body["limit_price"] = str(round(price, 8))

        log.info(
            "Delta ORDER %s %s %s qty=%s price=%s product_id=%s",
            side.upper(), order_type.upper(), symbol, size, price, product_id,
        )
        data = self._request("POST", "/v2/orders", body=body)
        return data.get("result", {})

    def get_order(self, order_id: str | int, product_id: int | None = None) -> dict:
        data = self._request(
            "GET", "/v2/orders",
            params={"id": str(order_id)},
        )
        result = data.get("result", {})
        if isinstance(result, list):
            return result[0] if result else {}
        return result

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
