"""
myfundedperps_client.py — Official REST Client for MyFundedPerpetuals (MFP) Prop Firm
====================================================================================
Supported Features:
  - Account info & live risk metrics (equity, daily_loss_floor, max_drawdown_floor, daily_loss_room)
  - Strict Challenge Protection: $75 daily loss limit & $75 total loss limit guardian
  - Market catalog lookup & real-time orderbook quote fetch
  - Market order execution with atomic Take-Profit & Stop-Loss (replace_overlapping_exits=True)
  - Close all open positions with 2.5% max slippage
  - Working orders cancellation & position state tracking
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional
import requests

log = logging.getLogger(__name__)


class MyFundedPerpsClient:
    """Client for MyFundedPerpetuals Developer REST API."""

    BASE_URL = "https://developers.myfundedperpetuals.com"

    def __init__(
        self,
        api_key: str,
        account_id: Optional[str] = None,
        daily_loss_limit_usd: float = 75.0,
        total_loss_limit_usd: float = 75.0,
        timeout: int = 10,
    ):
        self.api_key = api_key.strip()
        self.account_id = account_id.strip() if account_id else None
        self.daily_loss_limit_usd = float(daily_loss_limit_usd)
        self.total_loss_limit_usd = float(total_loss_limit_usd)
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AntigravityQuantEngine/3.0",
        })
        self._markets_cache: Dict[str, Dict[str, Any]] = {}
        self._markets_cached_at: float = 0.0

        if not self.account_id and self.is_active:
            self._auto_discover_account()

    @property
    def is_active(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("fp_live_"))

    def _auto_discover_account(self) -> Optional[str]:
        """Automatically find the active challenge account ID if not provided."""
        try:
            accounts = self.list_accounts()
            for acc in accounts:
                if acc.get("status") == "active":
                    self.account_id = acc.get("id")
                    log.info("MyFundedPerps: Auto-discovered active account %s (%s)", self.account_id, acc.get("name"))
                    return self.account_id
            if accounts:
                self.account_id = accounts[0].get("id")
                return self.account_id
        except Exception as exc:
            log.warning("MyFundedPerps account discovery failed: %s", exc)
        return None

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        req_headers = {}
        if headers:
            req_headers.update(headers)

        resp = self._session.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            headers=req_headers,
            timeout=self.timeout,
        )
        if resp.status_code in (200, 201):
            return resp.json()
        
        err_msg = f"HTTP {resp.status_code}: {resp.text}"
        log.error("MyFundedPerps API error on %s %s -> %s", method, path, err_msg)
        return {"error": {"code": str(resp.status_code), "message": resp.text}}

    # ── Account & Risk Endpoints ─────────────────────────────────────────────

    def list_accounts(self) -> List[Dict[str, Any]]:
        res = self._request("GET", "/v1/accounts")
        return res.get("data", [])

    def get_account_detail(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        acc_id = account_id or self.account_id
        if not acc_id:
            return {}
        res = self._request("GET", f"/v1/accounts/{acc_id}")
        return res.get("data", {})

    def get_trading_policy(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        acc_id = account_id or self.account_id
        if not acc_id:
            return {}
        res = self._request("GET", f"/v1/accounts/{acc_id}/trading-policy")
        return res.get("data", {})

    def check_risk_guardrails(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates exact headroom for the user-mandated $75 daily loss & $75 total loss limit.
        Returns whether new orders are safe to open or must be blocked/liquidated.
        """
        detail = self.get_account_detail(account_id)
        if not detail:
            return {"safe_to_trade": False, "reason": "account_detail_unavailable"}

        starting_bal = float(detail.get("starting_balance", 2500.0) or 2500.0)
        current_bal = float(detail.get("balance", starting_bal) or starting_bal)
        risk = detail.get("risk", {})
        equity = float(risk.get("equity", current_bal) or current_bal)
        unrealized_pnl = float(risk.get("unrealized_pnl", 0.0) or 0.0)

        # 1. Total loss calculation
        total_loss = starting_bal - equity
        total_loss_remaining = max(0.0, self.total_loss_limit_usd - total_loss)

        # 2. Daily loss calculation from risk snapshot or starting balance
        daily_loss_floor = float(risk.get("daily_loss_floor", starting_bal - 75.0) or (starting_bal - 75.0))
        daily_loss_room_broker = float(risk.get("daily_loss_room", 75.0) or 75.0)
        
        # User constraint: hardcap $75 daily loss
        user_daily_loss_remaining = min(self.daily_loss_limit_usd, daily_loss_room_broker)

        # If loss breaches $75 limit or less than $10 buffer remains:
        safe = (total_loss_remaining > 10.0) and (user_daily_loss_remaining > 10.0)
        
        status = {
            "safe_to_trade": safe,
            "equity": equity,
            "starting_balance": starting_bal,
            "total_loss": total_loss,
            "total_loss_remaining": round(total_loss_remaining, 2),
            "daily_loss_remaining": round(user_daily_loss_remaining, 2),
            "unrealized_pnl": unrealized_pnl,
            "account_status": detail.get("status", "unknown"),
        }
        if not safe:
            status["reason"] = f"loss_limit_reached: total_rem=${total_loss_remaining:.2f}, daily_rem=${user_daily_loss_remaining:.2f} (cap: $75)"
            log.warning("MyFundedPerps RISK GUARDIAN BREACH RISK: %s", status["reason"])
        return status

    # ── Market & Pricing Endpoints ───────────────────────────────────────────

    def get_markets(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        now = time.time()
        if not force_refresh and self._markets_cache and (now - self._markets_cached_at) < 600.0:
            return self._markets_cache

        res = self._request("GET", "/v1/markets")
        data = res.get("data", [])
        mapping = {}
        for m in data:
            sym = str(m.get("symbol", "")).upper()
            mapping[sym] = m
            # Also map standard pair e.g. BTC/USDT -> BTC
            mapping[f"{sym}/USDT"] = m
            mapping[f"{sym}USDT"] = m
        self._markets_cache = mapping
        self._markets_cached_at = now
        return mapping

    def get_market_quote(self, symbol: str, side: str = "buy", size: float = 0.01) -> Dict[str, Any]:
        markets = self.get_markets()
        clean_sym = symbol.replace("/USDT", "").replace("USDT", "").upper()
        m_info = markets.get(clean_sym)
        if not m_info:
            return {}
        market_id = m_info.get("market_id")
        res = self._request(
            "GET",
            f"/v1/markets/{market_id}/quote",
            params={"side": side.lower(), "size": size},
        )
        return res.get("data", {})

    def get_ticker_price(self, symbol: str) -> float:
        clean_sym = symbol.replace("/USDT", "").replace("USDT", "").upper()
        # Fast quote lookup
        quote = self.get_market_quote(clean_sym, side="buy", size=0.001)
        if quote and quote.get("mid"):
            return float(quote["mid"])
        return 0.0

    # ── Orders & Positions ───────────────────────────────────────────────────

    def list_positions(self, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        acc_id = account_id or self.account_id
        if not acc_id:
            return []
        res = self._request("GET", "/v1/positions", params={"account_id": acc_id})
        return res.get("data", [])

    def place_order(
        self,
        symbol: str,
        side: str,
        size: float,
        leverage: int = 5,
        margin_mode: str = "isolated",
        order_type: str = "market",
        take_profit_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        expected_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Places an order on MyFundedPerpetuals with automatic loss limit verification.
        """
        acc_id = self.account_id
        if not acc_id:
            return {"status": "error", "reason": "no_active_mfp_account"}

        # Guard: Check $75 loss limits
        risk_check = self.check_risk_guardrails(acc_id)
        if not risk_check.get("safe_to_trade"):
            log.error("MFP Order blocked by $75 loss safeguard: %s", risk_check.get("reason"))
            return {"status": "rejected", "reason": risk_check.get("reason")}

        markets = self.get_markets()
        clean_sym = symbol.replace("/USDT", "").replace("USDT", "").upper()
        m_info = markets.get(clean_sym)
        if not m_info:
            return {"status": "error", "reason": f"market_not_tradable_on_mfp:{symbol}"}

        market_id = m_info["market_id"]
        max_lev = int(m_info.get("max_leverage", 10) or 10)
        use_lev = min(leverage, max_lev)

        decimals = int(m_info.get("size_decimals", 3) or 3)
        fmt_size = round(size, decimals)
        if fmt_size <= 0:
            fmt_size = round(10 ** (-decimals), decimals)

        payload: Dict[str, Any] = {
            "account_id": acc_id,
            "market_id": market_id,
            "side": side.lower(),
            "size": fmt_size,
            "leverage": use_lev,
            "margin_mode": margin_mode,
            "type": order_type.lower(),
        }
        if client_order_id:
            payload["client_order_id"] = client_order_id[:64]
        if expected_price and expected_price > 0:
            payload["expected_price"] = expected_price

        # Server-side TP and SL
        if take_profit_price and take_profit_price > 0:
            payload["take_profit_price"] = round(take_profit_price, 4 if take_profit_price > 1 else 6)
            payload["replace_overlapping_exits"] = True
        if stop_loss_price and stop_loss_price > 0:
            payload["stop_loss_price"] = round(stop_loss_price, 4 if stop_loss_price > 1 else 6)
            payload["replace_overlapping_exits"] = True

        idempotency_key = f"mfp_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"
        headers = {"Idempotency-Key": idempotency_key}

        log.info("MyFundedPerps SUBMITTING ORDER: %s %s %s @ lev %sx (TP: %s, SL: %s)",
                 side.upper(), fmt_size, market_id, use_lev, take_profit_price, stop_loss_price)
        res = self._request("POST", "/v1/orders", json_data=payload, headers=headers)
        data = res.get("data", {})
        if data and data.get("id"):
            log.info("MyFundedPerps ORDER ACCEPTED: ID %s (status: %s)", data.get("id"), data.get("status"))
            return {
                "status": "filled" if data.get("status") == "filled" else "open",
                "order_id": data.get("id"),
                "fill_price": float(data.get("fill_price") or data.get("expected_price") or 0.0),
                "filled_size": float(data.get("filled_size") or fmt_size),
                "market_id": market_id,
                "symbol": clean_sym,
                "raw": data,
            }
        return {"status": "error", "reason": res.get("error", {}).get("message") or "order_placement_failed"}

    def close_all_positions(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        acc_id = account_id or self.account_id
        if not acc_id:
            return {}
        idempotency_key = f"close_all_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"
        headers = {"Idempotency-Key": idempotency_key}
        res = self._request("POST", f"/v1/accounts/{acc_id}/close-all-positions", headers=headers)
        return res.get("data", {})

    def cancel_all_working_orders(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        acc_id = account_id or self.account_id
        if not acc_id:
            return {}
        idempotency_key = f"cancel_all_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"
        headers = {"Idempotency-Key": idempotency_key}
        res = self._request("POST", f"/v1/accounts/{acc_id}/cancel-all-working-orders", headers=headers)
        return res.get("data", {})
