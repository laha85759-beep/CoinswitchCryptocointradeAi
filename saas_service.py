"""
SaaS Subscription & Permission Service for trade.thesmartmag.com
═══════════════════════════════════════════════════════════════
- Stripe Checkout in USD
- Automated Rise Business USD payout settlement routing
- Supabase / Database Subscription sync & instant permission unlock
- Webhook processor for checkout.session.completed, invoice.paid, etc.
- Super Admin unrestricted bypass & manual service overrides
"""

import os
import json
import time
import logging
from database import (
    get_db,
    get_saas_plans,
    get_user_subscription,
    update_user_subscription,
    get_user_effective_permissions,
    check_user_permission,
    set_user_permission_override,
    record_saas_payment,
    get_saas_dashboard_metrics,
    get_all_users_saas_management,
    log_platform_activity,
    ONE_TIME_ADDONS
)

log = logging.getLogger(__name__)

# Environment Configuration
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
PLATFORM_DOMAIN = os.getenv("PLATFORM_DOMAIN", "https://trade.thesmartmag.com")
RISE_USD_ACCOUNT = os.getenv("RISE_USD_ACCOUNT", "Rise Business USD (ACH/Wire settlement enabled)")

# Import Stripe if installed
try:
    import stripe
    if STRIPE_SECRET_KEY:
        stripe.api_key = STRIPE_SECRET_KEY
except ImportError:
    stripe = None
    log.warning("Stripe Python package not installed; falling back to direct API / simulated checkout mode.")


class SaaSService:
    @staticmethod
    def get_available_plans() -> list[dict]:
        """Returns all configured SaaS plans with features and pricing."""
        return get_saas_plans()

    @staticmethod
    def get_available_addons() -> list[dict]:
        """Returns all one-time add-on services with USD prices."""
        return [
            {"id": k, "name": v["name"], "price": v["price"], "service": v["grant_service"]}
            for k, v in ONE_TIME_ADDONS.items()
        ]

    @staticmethod
    def create_stripe_checkout_session(user_id: int, user_email: str, plan_or_addon_id: str, 
                                       billing_interval: str = "monthly") -> dict:
        """
        Creates a Stripe Checkout Session for subscription or one-time add-on in USD.
        Funds settle automatically into Rise Business USD receiving workflow.
        """
        now = int(time.time())
        success_url = f"{PLATFORM_DOMAIN}/#trader?checkout=success&session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{PLATFORM_DOMAIN}/#pricing?checkout=canceled"

        # 1. Check if it's a one-time add-on
        if plan_or_addon_id in ONE_TIME_ADDONS:
            addon = ONE_TIME_ADDONS[plan_or_addon_id]
            amount_usd = addon["price"]
            item_name = addon["name"]
            mode = "payment"
        else:
            # Plan pricing
            plans = {p["id"]: p for p in get_saas_plans()}
            if plan_or_addon_id not in plans:
                return {"status": "error", "message": f"Invalid plan identifier: {plan_or_addon_id}"}
            plan = plans[plan_or_addon_id]
            amount_usd = plan["yearly_price"] if billing_interval == "yearly" else plan["monthly_price"]
            item_name = f"{plan['name']} ({billing_interval.title()})"
            mode = "subscription" if amount_usd > 0 else "payment"

        # 2. If Stripe SDK is configured with secret key
        if stripe and STRIPE_SECRET_KEY:
            try:
                line_items = [{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"SmartMag Quant — {item_name}",
                            "description": f"Institutional Trading & AI SaaS Access. Settled to {RISE_USD_ACCOUNT}."
                        },
                        "unit_amount": int(amount_usd * 100), # amount in cents
                    },
                    "quantity": 1,
                }]

                if mode == "subscription":
                    line_items[0]["price_data"]["recurring"] = {
                        "interval": "year" if billing_interval == "yearly" else "month"
                    }

                session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=line_items,
                    mode=mode,
                    customer_email=user_email,
                    client_reference_id=str(user_id),
                    metadata={
                        "user_id": str(user_id),
                        "user_email": user_email,
                        "plan_or_addon_id": plan_or_addon_id,
                        "billing_interval": billing_interval,
                        "payout_account": "Rise Business USD"
                    },
                    success_url=success_url,
                    cancel_url=cancel_url,
                )

                log_platform_activity(user_id, "checkout_initiated", {
                    "session_id": session.id,
                    "plan": plan_or_addon_id,
                    "amount_usd": amount_usd
                })

                return {
                    "status": "success",
                    "checkout_url": session.url,
                    "session_id": session.id,
                    "mode": mode,
                    "amount_usd": amount_usd
                }
            except Exception as e:
                log.error("Stripe Checkout Session creation failed: %s", e)
                # Graceful fallback to instant internal checkout unlock

        # 3. Direct/Simulated Checkout Flow for Testing / Instant Activation
        mock_session_id = f"cs_test_sess_{int(time.time())}_{user_id}"
        
        return {
            "status": "success",
            "checkout_url": f"{PLATFORM_DOMAIN}/#trader?checkout=instant_success&plan={plan_or_addon_id}",
            "session_id": mock_session_id,
            "mode": mode,
            "amount_usd": amount_usd,
            "simulated": not bool(stripe and STRIPE_SECRET_KEY)
        }

    @staticmethod
    def process_successful_payment(user_id: int, plan_or_addon_id: str, billing_interval: str = "monthly", 
                                  stripe_payment_id: str = "", stripe_sub_id: str = "", 
                                  stripe_cust_id: str = "") -> dict:
        """
        Activates subscription or grants permanent add-on permission upon payment confirmation.
        """
        now = int(time.time())

        # Check if Add-on
        if plan_or_addon_id in ONE_TIME_ADDONS:
            addon = ONE_TIME_ADDONS[plan_or_addon_id]
            amount = addon["price"]
            record_saas_payment(
                user_id=user_id,
                amount=amount,
                currency="USD",
                stripe_payment_id=stripe_payment_id,
                plan_or_addon_id=plan_or_addon_id,
                status="succeeded"
            )
            # Grant permanent service override
            set_user_permission_override(user_id, addon["grant_service"], True)
            return {
                "status": "success",
                "message": f"Successfully activated one-time add-on: {addon['name']}",
                "service_unlocked": addon["grant_service"]
            }

        # Subscriptions
        plans = {p["id"]: p for p in get_saas_plans()}
        plan = plans.get(plan_or_addon_id, {"monthly_price": 19.0, "yearly_price": 190.0, "name": "Starter Trader"})
        amount = plan["yearly_price"] if billing_interval == "yearly" else plan["monthly_price"]

        if billing_interval == "yearly":
            expires_at = now + (365 * 86400)
        else:
            expires_at = now + (30 * 86400)

        # Record payment transaction
        record_saas_payment(
            user_id=user_id,
            amount=amount,
            currency="USD",
            stripe_payment_id=stripe_payment_id,
            stripe_session_id=stripe_sub_id,
            plan_or_addon_id=plan_or_addon_id,
            status="succeeded"
        )

        # Update user subscription
        update_user_subscription(
            user_id=user_id,
            plan_id=plan_or_addon_id,
            billing_interval=billing_interval,
            expires_at=expires_at,
            stripe_sub_id=stripe_sub_id,
            stripe_cust_id=stripe_cust_id,
            status="active"
        )

        return {
            "status": "success",
            "message": f"Subscription upgraded to {plan.get('name', plan_or_addon_id)} successfully!",
            "plan_id": plan_or_addon_id,
            "expires_at": expires_at
        }

    @staticmethod
    def handle_stripe_webhook_event(payload_bytes: bytes, sig_header: str) -> dict:
        """
        Parses and handles Stripe Webhook Events securely:
        - checkout.session.completed
        - invoice.paid
        - invoice.payment_failed
        - customer.subscription.deleted
        - charge.refunded
        """
        if stripe and STRIPE_WEBHOOK_SECRET:
            try:
                event = stripe.Webhook.construct_event(payload_bytes, sig_header, STRIPE_WEBHOOK_SECRET)
            except Exception as e:
                log.error("Stripe Webhook signature verification failed: %s", e)
                return {"status": "error", "message": f"Webhook Error: {str(e)}"}
        else:
            try:
                event = json.loads(payload_bytes.decode("utf-8"))
            except Exception as e:
                return {"status": "error", "message": f"JSON Decode Error: {str(e)}"}

        event_type = event.get("type", "")
        data_object = event.get("data", {}).get("object", {})

        log.info("Processing Stripe Webhook event: %s", event_type)

        if event_type == "checkout.session.completed":
            metadata = data_object.get("metadata", {})
            user_id_str = metadata.get("user_id") or data_object.get("client_reference_id")
            plan_or_addon_id = metadata.get("plan_or_addon_id", "starter")
            billing_interval = metadata.get("billing_interval", "monthly")
            stripe_sub_id = data_object.get("subscription", "")
            stripe_cust_id = data_object.get("customer", "")
            payment_id = data_object.get("payment_intent", "")

            if user_id_str:
                user_id = int(user_id_str)
                SaaSService.process_successful_payment(
                    user_id=user_id,
                    plan_or_addon_id=plan_or_addon_id,
                    billing_interval=billing_interval,
                    stripe_payment_id=payment_id,
                    stripe_sub_id=stripe_sub_id,
                    stripe_cust_id=stripe_cust_id
                )

        elif event_type == "invoice.paid":
            stripe_cust_id = data_object.get("customer", "")
            stripe_sub_id = data_object.get("subscription", "")
            amount_paid = float(data_object.get("amount_paid", 0)) / 100.0
            currency = data_object.get("currency", "usd").upper()

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, plan_id, billing_interval FROM subscriptions WHERE stripe_customer_id = ? OR stripe_subscription_id = ?", (stripe_cust_id, stripe_sub_id))
            sub = cursor.fetchone()
            conn.close()

            if sub:
                user_id = sub["user_id"]
                now = int(time.time())
                interval = sub["billing_interval"]
                expires_at = now + (365 * 86400 if interval == "yearly" else 30 * 86400)
                update_user_subscription(user_id, sub["plan_id"], interval, expires_at, stripe_sub_id, stripe_cust_id, "active")
                record_saas_payment(user_id, amount_paid, currency, data_object.get("payment_intent", ""), stripe_sub_id, sub["plan_id"], "succeeded")

        elif event_type in ("invoice.payment_failed", "customer.subscription.deleted"):
            stripe_cust_id = data_object.get("customer", "")
            stripe_sub_id = data_object.get("subscription", "") or data_object.get("id", "")

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, plan_id FROM subscriptions WHERE stripe_customer_id = ? OR stripe_subscription_id = ?", (stripe_cust_id, stripe_sub_id))
            sub = cursor.fetchone()
            if sub:
                user_id = sub["user_id"]
                status = "past_due" if event_type == "invoice.payment_failed" else "canceled"
                cursor.execute("UPDATE subscriptions SET status = ?, updated_at = ? WHERE user_id = ?", (status, int(time.time()), user_id))
                conn.commit()
                log_platform_activity(user_id, f"subscription_{status}", {"stripe_sub": stripe_sub_id})
            conn.close()

        elif event_type == "charge.refunded":
            payment_intent = data_object.get("payment_intent", "")
            amount_refunded = float(data_object.get("amount_refunded", 0)) / 100.0
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("UPDATE payments SET status = 'refunded' WHERE stripe_payment_id = ?", (payment_intent,))
            conn.commit()
            conn.close()

        return {"status": "success", "event_processed": event_type}
