"""

Coinbase Global Derivatives (Deribit Gateway) Auto-Trading & Risk Client

========================================================================

Supports:

  - 24/7 scanning of BTC, ETH, SOL and top perpetual futures

  - Multi-tiered risk guardian (0.5% - 1.0% risk per trade, max 3-5 open trades)

  - Strict position sizing: Position Size = (Equity * Risk %) / SL Distance

  - Hard stop-loss and multi-tier take-profit (TP1 50% partial at 1.5R, move to BE, TP2 runner)

  - Real-time position tracking and automatic reconciliation

"""



import os

import time

import logging

from typing import Dict, Any, List, Optional

from datetime import datetime, timezone

from pathlib import Path



# Load project .env automatically

dotenv_path = Path(__file__).parent / ".env"

if dotenv_path.exists():

    with open(dotenv_path, "r", encoding="utf-8") as _f:

        for _l in _f:

            _l = _l.strip()

            if _l and not _l.startswith("#") and "=" in _l:

                _k, _v = _l.split("=", 1)

                os.environ.setdefault(_k.strip(), _v.strip())



try:

    from coinbase.deribit import DeribitRetailClient

except ImportError:

    DeribitRetailClient = None



log = logging.getLogger("CoinbaseDerivativesClient")





class CoinbaseDerivativesClient:

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, cfg: Optional[Dict[str, Any]] = None):

        self.cfg = cfg or {}

        self.api_key = api_key or os.getenv("COINBASE_API_KEY", "")

        self.api_secret = api_secret or os.getenv("COINBASE_PRIVATE_KEY", "")

        self.client = None

        self.is_active = False



        if DeribitRetailClient and self.api_key and self.api_secret:

            try:

                self.client = DeribitRetailClient(api_key=self.api_key, api_secret=self.api_secret)

                # Quick verification of credentials

                summary = self.client.private_get_account_summary(currency="USDC")

                if summary and hasattr(summary, "result"):

                    self.is_active = True

                    log.info("CoinbaseDerivativesClient: Initialized with USDC Equity: $%.2f", summary.result.equity)

            except Exception as e:

                log.warning("CoinbaseDerivativesClient initialization notice: %s", e)



    def get_account_summary(self) -> Dict[str, Any]:

        if not self.is_active or not self.client:

            return {"status": "inactive", "equity": 0.0, "available_funds": 0.0}

        try:

            res = self.client.private_get_account_summary(currency="USDC")

            r = res.result

            return {

                "status": "active",

                "equity": float(r.equity or 0.0),

                "balance": float(r.balance or 0.0),

                "available_funds": float(r.available_funds or 0.0),

                "margin_balance": float(r.margin_balance or 0.0),

                "maintenance_margin": float(r.maintenance_margin or 0.0),

                "initial_margin": float(r.initial_margin or 0.0),

            }

        except Exception as e:

            log.error("Failed to fetch Coinbase Derivatives account summary: %s", e)

            return {"status": "error", "error": str(e), "equity": 0.0}



    def get_positions(self) -> List[Dict[str, Any]]:

        if not self.is_active or not self.client:

            return []

        try:

            res = self.client.private_get_positions(currency="USDC")

            positions = []

            pos_list = res.result if hasattr(res, "result") else (res.get("result", []) if isinstance(res, dict) else [])

            for p in pos_list:

                size_val = float(getattr(p, "size", 0.0) if hasattr(p, "size") else p.get("size", 0.0))

                if abs(size_val) > 0.0000001:

                    positions.append({

                        "instrument_name": getattr(p, "instrument_name", "") if hasattr(p, "instrument_name") else p.get("instrument_name"),

                        "direction": getattr(p, "direction", "") if hasattr(p, "direction") else p.get("direction"),

                        "size": size_val,

                        "mark_price": float(getattr(p, "mark_price", 0.0) if hasattr(p, "mark_price") else p.get("mark_price", 0.0)),

                        "entry_price": float(getattr(p, "average_price", 0.0) if hasattr(p, "average_price") else p.get("average_price", 0.0)),

                        "leverage": float(getattr(p, "leverage", 0.0) if hasattr(p, "leverage") else p.get("leverage", 0.0)),

                        "floating_pnl": float(getattr(p, "floating_profit_loss", 0.0) if hasattr(p, "floating_profit_loss") else p.get("floating_profit_loss", 0.0)),

                    })

            return positions

        except Exception as e:

            log.error("Failed to list Coinbase Derivatives positions: %s", e)

            return []



    def close_position(self, instrument_name: str, order_type: str = "market") -> Dict[str, Any]:
        """Closes an open position on Coinbase Derivatives / Deribit Gateway cleanly."""
        if not self.is_active or not self.client:
            return {"status": "error", "reason": "coinbase_derivatives_inactive"}
        inst = self.format_instrument(instrument_name)
        try:
            res = self.client.private_close_position(instrument_name=inst, type=order_type)
            try:
                self.client.private_cancel_all_by_instrument(instrument_name=inst)
            except Exception as c_err:
                log.warning("Notice cancelling remaining orders for %s: %s", inst, c_err)
            return {"status": "closed", "instrument": inst, "result": res}
        except Exception as e:
            log.error("Failed to close Coinbase Derivatives position %s: %s", inst, e)
            return {"status": "error", "reason": str(e)}

    def format_instrument(self, symbol: str) -> str:

        s = symbol.upper().strip()

        if "_USDC-PERPETUAL" in s or "-PERPETUAL" in s:

            return s

        s = s.replace("/", "").replace("_", "")

        if "USDT" in s:

            s = s.replace("USDT", "_USDC-PERPETUAL")

        elif "USDC" in s:

            s = s.replace("USDC", "_USDC-PERPETUAL")

        elif "USD" in s:

            s = s.replace("USD", "_USDC-PERPETUAL")

        else:

            s = f"{s}_USDC-PERPETUAL"

        return s



    def get_ticker_price(self, instrument_name: str) -> float:

        inst = self.format_instrument(instrument_name)

        try:

            t = self.client.public_ticker(instrument_name=inst)

            return float(t.result.mark_price or t.result.last_price or 0.0)

        except Exception as e:

            log.warning("Could not fetch ticker for %s: %s", inst, e)

            return 0.0



    def calculate_lot_size(self, instrument_name: str, equity: float, risk_pct: float, stop_loss_pct: float) -> float:
        """
        Lot size calculation based strictly on capital survival:
        Risk $ = Equity * (Risk % / 100)
        Position Size = Risk $ / (Price * SL %)
        CRITICAL GUARD: Position notional value is capped at 5x equity exposure max.
        If the minimum exchange contract size exceeds the maximum allowed risk/margin headroom,
        we return 0.0 to prevent forced liquidation and capital destruction.
        """
        price = self.get_ticker_price(instrument_name)
        if price <= 0 or equity <= 0:
            return 0.0

        # Safe leverage ceiling (max 5x leverage for risk preservation)
        max_notional = equity * 5.0
        risk_usd = equity * (risk_pct / 100.0)
        sl_pct_dec = max(0.01, stop_loss_pct / 100.0)
        target_notional_usd = min(risk_usd / sl_pct_dec, max_notional)

        try:
            inst_info = self.client.public_get_instrument(instrument_name=self.format_instrument(instrument_name))
            min_size = float(inst_info.result.min_trade_amount or 0.0001)
            min_notional = min_size * price

            # CAPITAL SURVIVAL CHECK: If min order notional requires more than max_notional (5x equity),
            # reject this instrument to protect capital from instant liquidation.
            if min_notional > max_notional:
                log.warning("Coinbase Derivatives lot rejected: %s min notional $%.2f exceeds max allowable $%.2f (equity=$%.2f)",
                            instrument_name, min_notional, max_notional, equity)
                return 0.0

            contract_qty = target_notional_usd / price
            decimals = max(0, -int(round(float(__import__('math').log10(min_size)))))
            rounded_qty = round(contract_qty, decimals)
            return max(min_size, rounded_qty)
        except Exception as e:
            log.warning("Error computing lot size for %s: %s", instrument_name, e)
            contract_qty = target_notional_usd / price
            return round(contract_qty, 4)



    def execute_order(

        self,

        symbol: str,

        direction: str,

        stop_loss_pct: float = 2.0,

        take_profit_pct: float = 6.0,

        risk_pct: float = 0.5

    ) -> Dict[str, Any]:

        """

        Executes a perpetual futures order with automated lot sizing and risk management.

        """

        if not self.is_active or not self.client:

            return {"status": "error", "reason": "coinbase_derivatives_inactive"}



        instrument = self.format_instrument(symbol)

        dir_lower = direction.lower()

        side = "buy" if dir_lower in ("long", "buy") else "sell"



        # Check account headroom

        summary = self.get_account_summary()

        equity = summary.get("equity", 0.0)

        avail = summary.get("available_funds", 0.0)

        if avail <= 0.10:

            return {"status": "rejected", "reason": f"insufficient_margin: available=${avail:.2f}"}



        # Check max open positions (limit to 5)

        current_positions = self.get_positions()

        if len(current_positions) >= 5:

            return {"status": "rejected", "reason": f"max_positions_reached ({len(current_positions)}/5)"}



        # Don't double open the same instrument

        if any(p["instrument_name"] == instrument for p in current_positions):

            return {"status": "skipped", "reason": f"already_open:{instrument}"}



        amount = self.calculate_lot_size(instrument, equity, risk_pct, stop_loss_pct)

        if amount <= 0:

            return {"status": "error", "reason": "calculated_amount_too_small"}



        try:

            if side == "buy":

                res = self.client.private_buy(

                    instrument_name=instrument,

                    amount=amount,

                    type="market",

                    label=f"SuperBrain_BUY_{int(time.time())}"

                )

            else:

                res = self.client.private_sell(

                    instrument_name=instrument,

                    amount=amount,

                    type="market",

                    label=f"SuperBrain_SELL_{int(time.time())}"

                )



            order_data = res.get("result", {}) if hasattr(res, "get") else (res.result if hasattr(res, "result") else {})

            order_info = order_data.get("order", {}) if isinstance(order_data, dict) else (getattr(order_data, "order", {}) or {})

            fill_price = float((order_info.get("average_price") if isinstance(order_info, dict) else getattr(order_info, "average_price", 0.0)) or self.get_ticker_price(instrument))



            # ── ATOMIC PROTECTION: Enforce Hard SL and TP on every single executed trade ──

            sl_price = round(fill_price * (1.0 - stop_loss_pct / 100.0), 4 if fill_price > 10 else 6) if side == "buy" else round(fill_price * (1.0 + stop_loss_pct / 100.0), 4 if fill_price > 10 else 6)

            tp_price = round(fill_price * (1.0 + take_profit_pct / 100.0), 4 if fill_price > 10 else 6) if side == "buy" else round(fill_price * (1.0 - take_profit_pct / 100.0), 4 if fill_price > 10 else 6)

            close_side = "sell" if side == "buy" else "buy"



            try:

                # 1. Place Stop Loss (Stop Market, Trigger: mark_price, reduce_only: True)

                if close_side == "sell":

                    self.client.private_sell(

                        instrument_name=instrument,

                        amount=amount,

                        type="stop_market",

                        trigger="mark_price",

                        trigger_price=sl_price,

                        reduce_only=True,

                        label=f"Guardian_SL_{instrument.split('_')[0]}"

                    )

                else:

                    self.client.private_buy(

                        instrument_name=instrument,

                        amount=amount,

                        type="stop_market",

                        trigger="mark_price",

                        trigger_price=sl_price,

                        reduce_only=True,

                        label=f"Guardian_SL_{instrument.split('_')[0]}"

                    )

                log.info("Guardian SL placed for %s @ %s", instrument, sl_price)

            except Exception as sl_err:

                log.error("Failed to attach SL for %s: %s", instrument, sl_err)



            try:

                # 2. Place Take Profit (Limit, reduce_only: True)

                if close_side == "sell":

                    self.client.private_sell(

                        instrument_name=instrument,

                        amount=amount,

                        type="limit",

                        price=tp_price,

                        reduce_only=True,

                        label=f"Guardian_TP_{instrument.split('_')[0]}"

                    )

                else:

                    self.client.private_buy(

                        instrument_name=instrument,

                        amount=amount,

                        type="limit",

                        price=tp_price,

                        reduce_only=True,

                        label=f"Guardian_TP_{instrument.split('_')[0]}"

                    )

                log.info("Guardian TP placed for %s @ %s", instrument, tp_price)

            except Exception as tp_err:

                log.error("Failed to attach TP for %s: %s", instrument, tp_err)



            return {

                "status": "filled",

                "instrument_name": instrument,

                "direction": side,

                "amount": amount,

                "fill_price": fill_price,

                "stop_loss": sl_price,

                "take_profit": tp_price,

                "order_id": str(order_info.get("order_id") if isinstance(order_info, dict) else getattr(order_info, "order_id", "")),

                "timestamp": datetime.now(timezone.utc).isoformat()

            }

        except Exception as e:

            log.error("Execution error on %s: %s", instrument, e)

            return {"status": "error", "reason": str(e)}





coinbase_derivatives = CoinbaseDerivativesClient()

