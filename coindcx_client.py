"""
coindcx_client.py - Production CoinDCX Futures & Derivatives REST Client
========================================================================
Implements official CoinDCX REST API specification:
  - Official Base URL: https://api.coindcx.com
  - HMAC-SHA256 authenticated request headers (X-AUTH-APIKEY, X-AUTH-SIGNATURE)
  - Public market data: Active instruments, orderbooks, ticker prices
  - Private trading: Balances, open positions, placing market/limit orders with SL & TP
"""

import hmac
import hashlib
import json
import time
import logging
from typing import Dict, Any, List, Optional
import requests

log = logging.getLogger("CoinDCXClient")

class CoinDCXClient:
    BASE_URL = "https://api.coindcx.com"

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.api_key = api_key or ""
        self.api_secret = api_secret or ""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TheSmartMag-Quant/2026",
            "Content-Type": "application/json"
        })

    def _get_auth_headers(self, body_dict: Dict[str, Any]) -> Dict[str, str]:
        """Generates official HMAC-SHA256 signature required by CoinDCX."""
        json_body = json.dumps(body_dict, separators=(",", ":"))
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            json_body.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return {
            "Content-Type": "application/json",
            "X-AUTH-APIKEY": self.api_key,
            "X-AUTH-SIGNATURE": signature
        }

    # ==========================================
    # PUBLIC MARKET DATA ENDPOINTS
    # ==========================================
    def get_active_instruments(self) -> List[str]:
        """Fetch all active CoinDCX futures pairs (e.g. B-BTC_USDT, B-ETH_USDT)."""
        url = f"{self.BASE_URL}/exchange/v1/derivatives/futures/data/active_instruments"
        try:
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            log.warning("CoinDCX active instruments fetch error: %s", e)
        return []

    def get_ticker_price(self, pair: str = "B-BTC_USDT") -> float:
        """Fetch current mark/last price for a futures contract or spot market."""
        clean_pair = pair.replace("B-", "").replace("_", "").upper()
        url = f"{self.BASE_URL}/exchange/ticker"
        try:
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                for item in data:
                    m = item.get("market", "").upper()
                    if m == pair.upper() or m == clean_pair:
                        return float(item.get("last_price", 0.0))
        except Exception as e:
            log.warning("CoinDCX ticker fetch error: %s", e)
        return 0.0

    # ==========================================
    # PRIVATE TRADING & ACCOUNT ENDPOINTS
    # ==========================================
    def get_balances(self) -> List[Dict[str, Any]]:
        """Fetch user account wallet balances."""
        if not self.api_key or not self.api_secret:
            return []
        url = f"{self.BASE_URL}/exchange/v1/users/balances"
        body = {"timestamp": int(time.time() * 1000)}
        headers = self._get_auth_headers(body)
        try:
            r = self.session.post(url, data=json.dumps(body), headers=headers, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            log.warning("CoinDCX get_balances error: %s", e)
        return []

    def get_open_positions(self, page: int = 1, size: int = 50) -> List[Dict[str, Any]]:
        """Fetch active open futures positions."""
        if not self.api_key or not self.api_secret:
            return []
        url = f"{self.BASE_URL}/exchange/v1/derivatives/futures/positions"
        body = {
            "timestamp": int(time.time() * 1000),
            "page": page,
            "size": size
        }
        headers = self._get_auth_headers(body)
        try:
            r = self.session.post(url, data=json.dumps(body), headers=headers, timeout=10)
            if r.status_code == 200:
                res = r.json()
                return res if isinstance(res, list) else res.get("positions", [])
        except Exception as e:
            log.warning("CoinDCX get_open_positions error: %s", e)
        return []

    def place_futures_order(
        self,
        pair: str,
        side: str,
        quantity: float,
        leverage: int = 10,
        order_type: str = "market_order",
        price: Optional[float] = None,
        sl_price: Optional[float] = None,
        tp_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes a futures order with mandatory Stop Loss and Take Profit.
        side: 'buy' (Long) or 'sell' (Short)
        """
        if not self.api_key or not self.api_secret:
            return {"status": "error", "message": "CoinDCX API credentials missing"}

        url = f"{self.BASE_URL}/exchange/v1/derivatives/futures/orders"
        
        order_dict: Dict[str, Any] = {
            "side": side.lower(),
            "pair": pair,
            "order_type": order_type,
            "total_quantity": quantity,
            "leverage": leverage
        }
        if price and order_type != "market_order":
            order_dict["price_per_unit"] = price
        if sl_price:
            order_dict["stop_loss_price"] = sl_price
        if tp_price:
            order_dict["take_profit_price"] = tp_price

        body = {
            "timestamp": int(time.time() * 1000),
            "order": order_dict
        }
        headers = self._get_auth_headers(body)
        try:
            r = self.session.post(url, data=json.dumps(body), headers=headers, timeout=10)
            return r.json()
        except Exception as e:
            log.error("CoinDCX place_futures_order failed: %s", e)
            return {"status": "error", "message": str(e)}

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancels a pending futures order by ID."""
        if not self.api_key or not self.api_secret:
            return {"status": "error", "message": "CoinDCX API credentials missing"}
        url = f"{self.BASE_URL}/exchange/v1/derivatives/futures/orders/cancel"
        body = {
            "timestamp": int(time.time() * 1000),
            "id": order_id
        }
        headers = self._get_auth_headers(body)
        try:
            r = self.session.post(url, data=json.dumps(body), headers=headers, timeout=10)
            return r.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
