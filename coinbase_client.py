"""
Coinbase Advanced Trade (CDP API) Client
Uses CDP Ed25519 authentication with JWT (ES256 / EdDSA)
"""
import time
import secrets
import logging
import base64
import requests
import jwt
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger("CoinbaseClient")

class CoinbaseClient:
    def __init__(self, key_name: str, private_key_raw: str):
        self.key_name = key_name.strip()
        self.base_url = "https://api.coinbase.com"
        self.host = "api.coinbase.com"
        
        # Parse raw key (could be 64-byte base64 or PEM)
        raw_clean = private_key_raw.strip()
        if "-----BEGIN" in raw_clean:
            self.pem = raw_clean
        else:
            raw_bytes = base64.b64decode(raw_clean)
            if len(raw_bytes) >= 32:
                seed = raw_bytes[:32]
                priv = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
                self.pem = priv.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ).decode('utf-8')
            else:
                raise ValueError("Coinbase Ed25519 private key seed must be at least 32 bytes")

    def _build_jwt(self, method: str, path: str) -> str:
        uri = f"{method.upper()} {self.host}{path}"
        payload = {
            "iss": "cdp",
            "nbf": int(time.time()),
            "exp": int(time.time()) + 120,
            "sub": self.key_name,
            "uri": uri
        }
        headers = {
            "kid": self.key_name,
            "nonce": secrets.token_hex(16)
        }
        return jwt.encode(payload, self.pem, algorithm="EdDSA", headers=headers)

    def _request(self, method: str, path: str, params=None, json_data=None):
        token = self._build_jwt(method, path)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        url = f"{self.base_url}{path}"
        resp = requests.request(method, url, headers=headers, params=params, json=json_data, timeout=15)
        return resp

    def get_accounts(self):
        try:
            r = self._request("GET", "/api/v3/brokerage/accounts")
            if r.status_code == 200:
                return r.json().get("accounts", [])
            logger.error(f"Coinbase get_accounts error: {r.status_code} {r.text}")
            return []
        except Exception as e:
            logger.error(f"Coinbase get_accounts exception: {e}")
            return []

    def get_balances(self):
        accounts = self.get_accounts()
        balances = {}
        for acc in accounts:
            avail = float(acc.get("available_balance", {}).get("value", 0) or 0)
            hold = float(acc.get("hold", {}).get("value", 0) or 0)
            total = avail + hold
            if total > 0:
                balances[acc.get("currency")] = total
        return balances

    def preview_order(self, product_id: str, side: str, quote_size: str = None, base_size: str = None):
        path = "/api/v3/brokerage/orders/preview"
        order_config = {}
        if quote_size:
            order_config["market_market_ioc"] = {"quote_size": str(quote_size)}
        elif base_size:
            order_config["market_market_ioc"] = {"base_size": str(base_size)}
            
        payload = {
            "product_id": product_id,
            "side": side.upper(),
            "order_configuration": order_config
        }
        r = self._request("POST", path, json_data=payload)
        return r.json()

    def create_market_order(self, product_id: str, side: str, quote_size: str = None, base_size: str = None):
        path = "/api/v3/brokerage/orders"
        client_oid = secrets.token_hex(16)
        order_config = {}
        if quote_size:
            order_config["market_market_ioc"] = {"quote_size": str(quote_size)}
        elif base_size:
            order_config["market_market_ioc"] = {"base_size": str(base_size)}

        payload = {
            "client_order_id": client_oid,
            "product_id": product_id,
            "side": side.upper(),
            "order_configuration": order_config
        }
        r = self._request("POST", path, json_data=payload)
        return r.json()

    def get_product(self, product_id: str):
        path = f"/api/v3/brokerage/products/{product_id}"
        r = self._request("GET", path)
        if r.status_code == 200:
            return r.json()
        return None
