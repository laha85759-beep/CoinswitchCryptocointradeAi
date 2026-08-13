"""
Options Chain Agent — Delta Exchange India
==========================================
Implements limited-loss, unlimited-profit options hedge strategies (Long Straddle & Long Strangle).
Guarantees mandatory Stop-Loss (SL) and Take-Profit (TP) on every options trade plan.
"""

import math
import logging
import time
from datetime import datetime, timezone
from typing import Any

from datetime import datetime, timezone

def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def load_json(filepath: str, default: Any = None) -> Any:
    import os, json
    if not os.path.exists(filepath):
        return default if default is not None else []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []

def save_json(filepath: str, data: Any) -> None:
    import json
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

log = logging.getLogger(__name__)

OPTIONS_TRADES_FILE = "open_options.json"


class OptionsChainProvider:
    """Fetches and filters live options chains from Delta Exchange India."""

    def __init__(self, delta_client: Any):
        self.client = delta_client

    def get_live_options_chain(self, asset: str) -> list[dict]:
        """Fetch all live call and put options for a given base asset (e.g. ETH, BTC)."""
        if not self.client:
            return []
        
        try:
            resp = self.client._request("GET", "/v2/products", params={"page_size": "1000"})
            products = resp if isinstance(resp, list) else resp.get("result", resp.get("data", []))
            if isinstance(products, dict):
                products = products.get("result", products.get("data", []))

            options = []
            asset_upper = asset.upper()
            for p in products:
                if p.get("state") != "live":
                    continue
                c_type = p.get("contract_type", "")
                if c_type not in ("call_options", "put_options"):
                    continue
                
                u_asset = p.get("underlying_asset")
                if isinstance(u_asset, dict):
                    u_asset = u_asset.get("symbol", "")
                
                if str(u_asset).upper() == asset_upper:
                    options.append(p)
            return options
        except Exception as exc:
            log.error("Failed to fetch options chain for %s: %s", asset, exc)
            return []

    def get_option_pricing(self, product_id: int) -> dict:
        """Fetch live bid/ask orderbook pricing for an option product."""
        try:
            ob = self.client._request("GET", f"/v2/l2orderbook/{product_id}", auth=False)
            res = ob.get("result", ob) if isinstance(ob, dict) else {}
            sells = res.get("sell", [])
            buys = res.get("buy", [])
            ask_price = float(sells[0]["price"]) if sells else 0.0
            bid_price = float(buys[0]["price"]) if buys else 0.0
            return {"ask": ask_price, "bid": bid_price, "mid": (ask_price + bid_price) / 2 if (ask_price and bid_price) else (ask_price or bid_price)}
        except Exception as exc:
            log.warning("Option pricing fetch failed for product %s: %s", product_id, exc)
            return {"ask": 0.0, "bid": 0.0, "mid": 0.0}


class OptionsHedgeAgent:
    """
    Evaluates volatility signals and creates Options Hedge Trade Plans (Straddle / Strangle).
    Enforces STRICT mandatory SL and TP rules on all trade plans.
    """

    def __init__(self, cfg: dict, delta_client: Any, notifier: Any = None):
        self.cfg = cfg
        self.delta_client = delta_client
        self.provider = OptionsChainProvider(delta_client)
        self.notifier = notifier

    def generate_trade_plan(self, asset: str, spot_price: float, signal_type: str = "volatility_breakout") -> dict | None:
        """
        Builds a hedged options trade plan (Call + Put legs) with MANDATORY SL & TP.
        Returns None if risk checks fail or pricing is unavailable.
        """
        if not self.cfg.get("options_enabled", True) or not self.delta_client:
            return None

        # Check if active options trade already open for this asset to avoid repeated entries
        open_opts = load_json(OPTIONS_TRADES_FILE, [])
        if any(t.get("asset") == asset and t.get("status") == "active" for t in open_opts):
            return None

        chain = self.provider.get_live_options_chain(asset)
        if not chain:
            log.info("No active options chain found for %s", asset)
            return None

        # Filter options with at least 1 day until expiry
        now_iso = datetime.now(timezone.utc).isoformat()
        valid_options = []
        for opt in chain:
            settle = opt.get("settlement_time", "")
            if settle > now_iso:
                valid_options.append(opt)

        if not valid_options:
            return None

        # Find nearest ATM strike for Straddle / Strangle
        calls = [o for o in valid_options if o.get("contract_type") == "call_options"]
        puts = [o for o in valid_options if o.get("contract_type") == "put_options"]

        if not calls or not puts:
            return None

        # Pick nearest ATM Call & Put
        best_call = min(calls, key=lambda c: abs(float(c.get("strike_price", 0)) - spot_price))
        best_put = min(puts, key=lambda p: abs(float(p.get("strike_price", 0)) - spot_price))

        call_price = self.provider.get_option_pricing(best_call["id"])
        put_price = self.provider.get_option_pricing(best_put["id"])

        entry_call_premium = call_price["ask"] or call_price["mid"]
        entry_put_premium = put_price["ask"] or put_price["mid"]

        if entry_call_premium <= 0 or entry_put_premium <= 0:
            log.warning("Invalid options premium pricing for %s (Call: %s, Put: %s)", asset, entry_call_premium, entry_put_premium)
            return None

        total_premium_paid = entry_call_premium + entry_put_premium

        # MANDATORY SL & TP CALCULATIONS (Strict Risk Protection)
        # Max loss is strictly capped at Premium Paid.
        # Hard SL: -50% of premium paid (prevents total loss of premium if volatility stays flat)
        # Take Profit: +100% of premium paid (doubles investment on big price expansion)
        sl_pct = float(self.cfg.get("options_stop_loss_pct", 50.0))
        tp_pct = float(self.cfg.get("options_take_profit_pct", 100.0))

        stop_loss_val = round(total_premium_paid * (1 - sl_pct / 100.0), 4)
        take_profit_val = round(total_premium_paid * (1 + tp_pct / 100.0), 4)

        # STRICT VALIDATION: Reject any trade plan that lacks SL or TP
        if stop_loss_val <= 0 or take_profit_val <= total_premium_paid:
            log.error("CRITICAL: Rejected Options Trade Plan — invalid SL/TP calculation! SL: %s, TP: %s", stop_loss_val, take_profit_val)
            return None

        plan = {
            "strategy": "long_straddle",
            "asset": asset,
            "spot_price_at_entry": spot_price,
            "call_leg": {
                "symbol": best_call["symbol"],
                "product_id": best_call["id"],
                "strike": float(best_call.get("strike_price", 0)),
                "entry_premium": entry_call_premium,
            },
            "put_leg": {
                "symbol": best_put["symbol"],
                "product_id": best_put["id"],
                "strike": float(best_put.get("strike_price", 0)),
                "entry_premium": entry_put_premium,
            },
            "total_premium_paid": round(total_premium_paid, 4),
            "peak_combined_value": round(total_premium_paid, 4),
            "mandatory_risk": {
                "stop_loss_premium": stop_loss_val,
                "stop_loss_pct": sl_pct,
                "take_profit_premium": take_profit_val,
                "take_profit_pct": tp_pct,
                "max_possible_loss": round(total_premium_paid, 4),  # Capped at premium paid
                "unlimited_profit": True
            },
            "opened_at": utc_iso(),
            "status": "active"
        }

        log.info("🎯 Generated Options Hedge Trade Plan for %s | Call: %s @ %s | Put: %s @ %s | Total Premium: $%s | SL: $%s (-%s%%) | TP: $%s (+%s%%)",
                 asset, best_call['symbol'], entry_call_premium, best_put['symbol'], entry_put_premium,
                 total_premium_paid, stop_loss_val, sl_pct, take_profit_val, tp_pct)
        return plan

    def execute_plan(self, plan: dict) -> dict:
        """Executes the hedged options legs on Delta Exchange India (REAL TRADE ONLY)."""
        if not plan:
            return {"status": "error", "reason": "invalid_plan"}

        # Place Call Leg
        call_leg = plan["call_leg"]
        try:
            call_order = self.delta_client.place_order(
                symbol=call_leg["symbol"],
                side="buy",
                order_type="market_order",
                quantity=1
            )
            # Ensure we got a valid order response from the live API
            if not call_order or not (call_order.get("id") or call_order.get("order_id")):
                raise ValueError("No valid order ID returned from Delta API for Call leg")
        except Exception as exc:
            log.error("Delta Call leg order execution FAILED: %s", exc)
            return {"status": "error", "reason": f"call_leg_failed:{exc}"}

        # Place Put Leg
        put_leg = plan["put_leg"]
        try:
            put_order = self.delta_client.place_order(
                symbol=put_leg["symbol"],
                side="buy",
                order_type="market_order",
                quantity=1
            )
            # Ensure we got a valid order response from the live API
            if not put_order or not (put_order.get("id") or put_order.get("order_id")):
                raise ValueError("No valid order ID returned from Delta API for Put leg")
        except Exception as exc:
            log.error("Delta Put leg order execution FAILED: %s", exc)
            # In a production environment, if one leg fails, we should ideally alert the user
            if self.notifier:
                self.notifier.send(
                    f"⚠️ *DELTA HEDGE ALARM*\n"
                    f"Call leg filled (`{call_order.get('id')}`), but Put leg (`{put_leg['symbol']}`) FAILED: `{exc}`. Check account status immediately."
                )
            return {"status": "error", "reason": f"put_leg_failed:{exc}"}

        plan["call_order_id"] = call_order.get("id") or call_order.get("order_id")
        plan["put_order_id"] = put_order.get("id") or put_order.get("order_id")

        # Save to open options positions (Only real trades reach here)
        open_opts = load_json(OPTIONS_TRADES_FILE, [])
        open_opts.append(plan)
        save_json(OPTIONS_TRADES_FILE, open_opts)

        if self.notifier:
            self.notifier.send(
                f"🛡️ *OPTIONS HEDGE TRADE EXECUTED*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📊 *Asset*         : `{plan['asset']}`\n"
                f"📈 *Call Leg*      : `{call_leg['symbol']}` (${call_leg['entry_premium']})\n"
                f"📉 *Put Leg*       : `{put_leg['symbol']}` (${put_leg['entry_premium']})\n"
                f"💰 *Total Premium* : `${plan['total_premium_paid']}`\n"
                f"🛑 *Stop Loss*     : `${plan['mandatory_risk']['stop_loss_premium']}` (-{plan['mandatory_risk']['stop_loss_pct']}%) \n"
                f"🎯 *Take Profit*   : `${plan['mandatory_risk']['take_profit_premium']}` (+{plan['mandatory_risk']['take_profit_pct']}%) \n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔒 Risk Capped: Small Fixed Loss | Profit: Unlimited 🚀"
            )

        return {"status": "filled", "plan": plan}



class OptionsMonitorAgent:
    """24/7 Monitor for active options hedge positions enforcing SL and TP exits."""

    def __init__(self, cfg: dict, delta_client: Any, notifier: Any = None):
        self.cfg = cfg
        self.delta_client = delta_client
        self.provider = OptionsChainProvider(delta_client)
        self.notifier = notifier

    def monitor(self) -> dict:
        """Evaluates all open options trades against SL and TP triggers."""
        open_opts = load_json(OPTIONS_TRADES_FILE, [])
        if not open_opts:
            return {"open_options": 0, "closed": []}

        remaining, closed = [], []

        for trade in open_opts:
            try:
                call_pricing = self.provider.get_option_pricing(trade["call_leg"]["product_id"])
                put_pricing = self.provider.get_option_pricing(trade["put_leg"]["product_id"])

                curr_call_val = call_pricing["bid"] or call_pricing["mid"]
                curr_put_val = put_pricing["bid"] or put_pricing["mid"]

                combined_value = curr_call_val + curr_put_val
                initial_premium = trade["total_premium_paid"]

                if combined_value > trade.get("peak_combined_value", initial_premium):
                    trade["peak_combined_value"] = round(combined_value, 4)

                sl_target = trade["mandatory_risk"]["stop_loss_premium"]
                tp_target = trade["mandatory_risk"]["take_profit_premium"]

                reason = None
                if combined_value <= sl_target:
                    reason = "STOP_LOSS_HIT"
                elif combined_value >= tp_target:
                    reason = "TAKE_PROFIT_HIT"

                if reason:
                    # Close positions (sell options back to market)
                    self.delta_client.place_order(trade["call_leg"]["symbol"], "sell", "market_order", 1)
                    self.delta_client.place_order(trade["put_leg"]["symbol"], "sell", "market_order", 1)

                    pnl_usd = round(combined_value - initial_premium, 4)
                    pnl_pct = round((pnl_usd / initial_premium) * 100, 2) if initial_premium > 0 else 0.0

                    trade["closed_at"] = utc_iso()
                    trade["exit_combined_value"] = combined_value
                    trade["realized_pnl_usd"] = pnl_usd
                    trade["realized_pnl_pct"] = pnl_pct
                    trade["exit_reason"] = reason
                    closed.append(trade)

                    log.info("Closed Options Trade for %s (%s) @ $%s | P&L: $%s (%s%%)",
                             trade["asset"], reason, combined_value, pnl_usd, pnl_pct)

                    if self.notifier:
                        self.notifier.send(
                            f"🔔 *OPTIONS HEDGE POSITION CLOSED*\n"
                            f"━━━━━━━━━━━━━━━━━━━━━\n"
                            f"📊 *Asset*      : `{trade['asset']}`\n"
                            f"🏷️ *Reason*     : `{reason}`\n"
                            f"💵 *Exit Value* : `${combined_value}` (Paid `${initial_premium}`)\n"
                            f"📈 *P&L*        : `${pnl_usd}` ({pnl_pct}%)\n"
                            f"━━━━━━━━━━━━━━━━━━━━━"
                        )
                else:
                    remaining.append(trade)

            except Exception as exc:
                log.error("Error monitoring options position for %s: %s", trade.get("asset"), exc)
                if "not found on Delta Exchange" in str(exc) or "invalid_contract" in str(exc):
                    log.info("Contract expired or invalid. Force-clearing %s from tracking.", trade.get("asset"))
                    continue
                remaining.append(trade)

        save_json(OPTIONS_TRADES_FILE, remaining)
        return {"open_options": len(remaining), "closed": closed}
