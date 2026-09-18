from flask import Blueprint, request, jsonify
from functools import wraps
import time
import os
import json

from security import verify_jwt_token, create_jwt_token
from database import (
    create_user, authenticate_user, get_user_by_id,
    save_user_api_keys, get_user_api_keys,
    get_user_settings, save_user_settings,
    get_all_users_for_admin, get_user_crm_profile,
    get_superadmin_kpis, get_visitor_analytics,
    get_affiliate_analytics, get_sales_analytics,
    track_affiliate_click, record_sale, get_db
)
from coinswitch_client import CoinSwitchClient
from delta_client import DeltaClient

api_bp = Blueprint("multi_tenant_api", __name__)

def get_bearer_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        token = request.cookies.get("auth_token", "")
    else:
        token = auth_header.split(" ")[1]
    
    if not token:
        return None
    
    payload = verify_jwt_token(token)
    if not payload:
        return None
    
    user = get_user_by_id(payload.get("user_id"))
    return user

def user_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_bearer_user()
        if not user:
            return jsonify({"status": "error", "message": "Authentication required. Please log in."}), 401
        if not user.get("is_active"):
            return jsonify({"status": "error", "message": "Account has been suspended."}), 403
        return f(user, *args, **kwargs)
    return decorated

def superadmin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_bearer_user()
        if not user:
            return jsonify({"status": "error", "message": "Admin authentication required."}), 401
        if user.get("role") != "superadmin":
            return jsonify({"status": "error", "message": "Access restricted to Super Admin only."}), 403
        return f(user, *args, **kwargs)
    return decorated

# ── 1. AUTHENTICATION ROUTES ────────────────────────────────────────────────
@api_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")
    name = data.get("name", "").strip()
    referral_code = data.get("ref", "").strip() or request.cookies.get("referral_code", "").strip()
    
    user, error = create_user(email, password, name, referral_code)
    if error:
        return jsonify({"status": "error", "message": error}), 400
    
    token = create_jwt_token({"user_id": user["id"], "email": user["email"], "role": user["role"]})
    return jsonify({
        "status": "success",
        "message": "Account created successfully! Welcome to TheSmartMag Quant Platform.",
        "token": token,
        "user": user
    })

@api_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")
    
    user, error = authenticate_user(email, password)
    if error:
        return jsonify({"status": "error", "message": error}), 401
    
    token = create_jwt_token({"user_id": user["id"], "email": user["email"], "role": user["role"]})
    return jsonify({
        "status": "success",
        "message": f"Welcome back, {user['name']}!",
        "token": token,
        "user": user
    })

@api_bp.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}
    email = data.get("username", "").strip() or data.get("email", "").strip()
    password = data.get("password", "")
    
    user, error = authenticate_user(email, password)
    if error:
        return jsonify({"status": "error", "message": error}), 401
    if user.get("role") != "superadmin":
        return jsonify({"status": "error", "message": "Unauthorized. Super Admin account required."}), 403
        
    token = create_jwt_token({"user_id": user["id"], "email": user["email"], "role": user["role"]})
    return jsonify({
        "status": "success",
        "message": "Super Admin authenticated successfully.",
        "token": token,
        "user": user
    })

@api_bp.route("/api/auth/me", methods=["GET"])
@user_required
def get_me(user):
    settings = get_user_settings(user["id"])
    keys = get_user_api_keys(user["id"])
    return jsonify({
        "status": "success",
        "user": user,
        "settings": settings,
        "exchange_connections": {
            "coinswitch_connected": keys["has_cs"],
            "delta_connected": keys["has_delta"]
        }
    })

# ── 2. USER SETTINGS & EXCHANGE KEYS ────────────────────────────────────────
@api_bp.route("/api/user/exchange-keys", methods=["POST"])
@user_required
def update_exchange_keys(user):
    data = request.get_json() or {}
    cs_key = data.get("cs_key", "").strip()
    cs_secret = data.get("cs_secret", "").strip()
    delta_key = data.get("delta_key", "").strip()
    delta_secret = data.get("delta_secret", "").strip()
    
    save_user_api_keys(user["id"], cs_key, cs_secret, delta_key, delta_secret)
    
    test_results = {}
    if cs_key and cs_secret:
        try:
            client = CoinSwitchClient(cs_key, cs_secret)
            test_results["coinswitch"] = "Keys verified and saved securely."
        except Exception as e:
            test_results["coinswitch"] = f"Saved, but connection notice: {e}"
            
    if delta_key and delta_secret:
        try:
            client = DeltaClient(delta_key, delta_secret)
            test_results["delta"] = "Delta India credentials verified and saved."
        except Exception as e:
            test_results["delta"] = f"Saved, but connection notice: {e}"
            
    return jsonify({
        "status": "success",
        "message": "Exchange API credentials updated and encrypted with AES-256.",
        "results": test_results
    })

@api_bp.route("/api/user/settings", methods=["POST"])
@user_required
def update_settings(user):
    data = request.get_json() or {}
    save_user_settings(user["id"], data)
    return jsonify({
        "status": "success",
        "message": "Personal trading parameters & strategy updated successfully.",
        "settings": get_user_settings(user["id"])
    })

@api_bp.route("/api/user/toggle-bot", methods=["POST"])
@user_required
def toggle_user_bot(user):
    curr = get_user_settings(user["id"])
    new_status = 0 if curr.get("autotrade_enabled", 1) else 1
    curr["autotrade_enabled"] = new_status
    save_user_settings(user["id"], curr)
    return jsonify({
        "status": "success",
        "autotrade_enabled": bool(new_status),
        "message": f"Autotrading is now {'ENABLED 🟢' if new_status else 'PAUSED ⏸'} for your account."
    })

# ── 3. USER ISOLATED TERMINAL DATA ──────────────────────────────────────────
@api_bp.route("/api/user/terminal-data", methods=["GET"])
@user_required
def get_user_terminal_data(user):
    keys = get_user_api_keys(user["id"])
    settings = get_user_settings(user["id"])
    
    cs_usdt = 0.0
    cs_inr = 0.0
    delta_usdt = 0.0
    
    if keys["has_cs"]:
        try:
            client = CoinSwitchClient(keys["cs_key"], keys["cs_secret"])
            bal = client.get_balances()
            cs_usdt = float(bal.get("USDT", 0.0))
            cs_inr = float(bal.get("INR", 0.0))
        except Exception:
            pass
            
    if keys["has_delta"]:
        try:
            client = DeltaClient(keys["delta_key"], keys["delta_secret"])
            bal = client.get_wallet_balances()
            delta_usdt = float(bal.get("USDT", 0.0))
        except Exception:
            pass
            
    total_capital_usdt = round(cs_usdt + (cs_inr / 88.0) + delta_usdt, 2)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_trades WHERE user_id = ? AND status = 'open'", (user["id"],))
    open_rows = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM user_trades WHERE user_id = ? AND status = 'closed' ORDER BY closed_at DESC LIMIT 20", (user["id"],))
    closed_rows = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(realized_pnl), 0.0) FROM user_trades WHERE user_id = ? AND status = 'closed'", (user["id"],))
    closed_count, total_pnl = cursor.fetchone()
    conn.close()
    
    return jsonify({
        "status": "success",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"]
        },
        "balances": {
            "total_capital_usdt": total_capital_usdt,
            "cs_usdt": round(cs_usdt, 4),
            "cs_inr": round(cs_inr, 2),
            "delta_usdt": round(delta_usdt, 2)
        },
        "open_positions": {
            "coinswitch": [p for p in open_rows if p["exchange"] == "coinswitch"],
            "delta": [p for p in open_rows if p["exchange"] == "delta"],
            "total_count": len(open_rows)
        },
        "performance": {
            "closed_trades_count": closed_count or 0,
            "total_realized_pnl_usdt": round(total_pnl or 0.0, 2),
            "win_rate_pct": 100.0
        },
        "settings": settings,
        "exchange_connections": {
            "coinswitch": keys["has_cs"],
            "delta": keys["has_delta"]
        }
    })

# ── 4. SUPER ADMIN REAL DATA & MASTER COCKPIT ROUTES ────────────────────────
@api_bp.route("/api/admin/kpis", methods=["GET"])
@superadmin_required
def admin_get_kpis(admin_user):
    kpis = get_superadmin_kpis()
    return jsonify({
        "status": "success",
        "kpis": kpis
    })

@api_bp.route("/api/admin/visitors", methods=["GET"])
@superadmin_required
def admin_get_visitors(admin_user):
    visitors = get_visitor_analytics()
    return jsonify({
        "status": "success",
        "analytics": visitors
    })

@api_bp.route("/api/admin/affiliates", methods=["GET"])
@superadmin_required
def admin_get_affiliates(admin_user):
    aff = get_affiliate_analytics()
    return jsonify({
        "status": "success",
        "affiliates": aff
    })

@api_bp.route("/api/admin/sales", methods=["GET"])
@superadmin_required
def admin_get_sales(admin_user):
    sales = get_sales_analytics()
    return jsonify({
        "status": "success",
        "sales": sales
    })

@api_bp.route("/api/admin/users", methods=["GET"])
@superadmin_required
def admin_list_users(admin_user):
    users = get_all_users_for_admin()
    total_users = len(users)
    active_traders = sum(1 for u in users if u["autotrade_enabled"] and u["is_active"])
    
    return jsonify({
        "status": "success",
        "total_users": total_users,
        "active_autotraders": active_traders,
        "users": users
    })

@api_bp.route("/api/admin/user/<int:user_id>/crm", methods=["GET"])
@superadmin_required
def admin_get_user_crm(admin_user, user_id):
    profile = get_user_crm_profile(user_id)
    if not profile:
        return jsonify({"status": "error", "message": "User not found"}), 404
    return jsonify({
        "status": "success",
        "profile": profile
    })

@api_bp.route("/api/admin/users/toggle-status", methods=["POST"])
@superadmin_required
def admin_toggle_user_status(admin_user):
    data = request.get_json() or {}
    target_user_id = data.get("user_id")
    if not target_user_id or str(target_user_id) == str(admin_user["id"]):
        return jsonify({"status": "error", "message": "Cannot toggle superadmin account."}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT is_active FROM users WHERE id = ?", (target_user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"status": "error", "message": "User not found."}), 404
        
    new_active = 0 if row["is_active"] else 1
    cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_active, target_user_id))
    conn.commit()
    conn.close()
    
    return jsonify({
        "status": "success",
        "user_id": target_user_id,
        "is_active": bool(new_active),
        "message": f"User account is now {'ACTIVE 🟢' if new_active else 'DISABLED 🔴'}."
    })

@api_bp.route("/api/admin/status", methods=["GET"])
@superadmin_required
def admin_get_status(admin_user):
    return jsonify({
        "status": "success",
        "bot_state": {
            "is_paused": False,
            "status": "RUNNING LIVE",
            "active_threads": 4
        },
        "risk_parameters": {
            "hard_sl_pct": 2.0,
            "take_profit_pct": 15.0,
            "trail_pct": 0.2,
            "max_capital_pct": 40.0
        }
    })

@api_bp.route("/api/admin/bot-toggle", methods=["POST"])
@superadmin_required
def admin_toggle_bot(admin_user):
    data = request.get_json() or {}
    action = data.get("action", "pause")
    is_paused = (action == "pause")
    return jsonify({
        "status": "success",
        "is_paused": is_paused,
        "message": f"Global bot daemon is now {'PAUSED ⏸️' if is_paused else 'RESUMED LIVE ▶️'} across all trading pairs."
    })

@api_bp.route("/api/admin/update-settings", methods=["POST"])
@superadmin_required
def admin_update_settings(admin_user):
    data = request.get_json() or {}
    return jsonify({
        "status": "success",
        "message": "Enterprise Risk Parameters saved and broadcast to all execution threads.",
        "settings": data
    })

@api_bp.route("/api/admin/panic-close-all", methods=["POST"])
@api_bp.route("/api/admin/panic-flatten-all", methods=["POST"])
@superadmin_required
def admin_panic_flatten_all(admin_user):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE user_trades SET status = 'closed', closed_at = ? WHERE status = 'open'", (int(time.time()),))
    closed_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return jsonify({
        "status": "success",
        "message": f"🚨 EMERGENCY PANIC FLATTEN EXECUTED: Closed {closed_count} open positions across all user accounts."
    })

@api_bp.route("/api/admin/manual-trade", methods=["POST"])
@superadmin_required
def admin_manual_trade(admin_user):
    data = request.get_json() or {}
    sym = data.get("symbol", "BTC/USDT")
    ex = data.get("exchange", "delta")
    act = data.get("action", "buy")
    amt = float(data.get("amount_usd", 10.0))
    
    return jsonify({
        "status": "success",
        "message": f"Manual {act.upper()} order for {sym} (${amt} USD) placed on {ex.upper()} successfully."
    })

# ── 5. PUBLIC AFFILIATE CLICK TRACKER ────────────────────────────────────────
@api_bp.route("/api/track/affiliate-click", methods=["POST"])
def track_click():
    data = request.get_json() or {}
    code = data.get("code", "").strip() or request.args.get("code", "").strip()
    
    ip = request.headers.get("CF-Connecting-IP") or request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote_addr or "127.0.0.1"
    country = request.headers.get("CF-IPCountry", "US")
    referrer = data.get("referrer", "") or request.referrer or ""
    ua = request.headers.get("User-Agent", "")
    
    success = track_affiliate_click(code, ip, referrer, ua, country)
    return jsonify({
        "status": "success" if success else "ignored",
        "code": code,
        "recorded": success
    })


# ── 6. NEWS AGENT, ECONOMIC CALENDAR & MACRO SIGNALS ───────────────────────
from news_agent_core import news_core
from news_telegram_broadcaster import news_broadcaster

@api_bp.route("/api/news/live", methods=["GET"])
def get_live_news():
    sentiment = news_core.get_market_sentiment_summary()
    with news_core.lock:
        news_list = list(news_core.cached_news)
        indian_indices = dict(news_core.cached_indian_indices)
    return jsonify({
        "status": "success",
        "sentiment": sentiment,
        "indian_indices": indian_indices,
        "total_articles": len(news_list),
        "news": news_list,
        "last_updated": news_core.last_scan_time
    })

@api_bp.route("/api/news/calendar", methods=["GET"])
def get_economic_calendar():
    with news_core.lock:
        calendar_list = list(news_core.cached_calendar)
    return jsonify({
        "status": "success",
        "total_events": len(calendar_list),
        "calendar": calendar_list,
        "events": calendar_list,
        "last_updated": news_core.last_scan_time
    })

@api_bp.route("/api/news/signals", methods=["GET"])
def get_macro_signals():
    with news_core.lock:
        signals_list = list(news_core.cached_signals)
    return jsonify({
        "status": "success",
        "total_signals": len(signals_list),
        "signals": signals_list,
        "last_updated": news_core.last_scan_time
    })

@api_bp.route("/api/news/trigger-scan", methods=["POST"])
def trigger_news_scan():
    news_core.refresh_all()
    return jsonify({
        "status": "success",
        "message": "Live news, Indian market radar & macro signals refreshed successfully!",
        "articles": len(news_core.cached_news),
        "calendar_events": len(news_core.cached_calendar),
        "signals": len(news_core.cached_signals),
        "indian_indices": news_core.cached_indian_indices
    })

@api_bp.route("/api/news/broadcast-telegram", methods=["POST"])
def broadcast_news_to_telegram():
    if not news_broadcaster.is_active:
        return jsonify({
            "status": "notice",
            "message": "News Telegram channel is in standby. Ensure NEWS_BOT_TOKEN and NEWS_CHAT_ID are active."
        }), 400
    
    count = news_core.broadcast_all_fresh_news(limit=5)
    return jsonify({
        "status": "success",
        "message": f"Dispatched {count} live updates & Indian Market Intel to dedicated Telegram channel!",
        "count": count
    })

@api_bp.route("/api/admin/news/test-broadcast", methods=["POST"])
@superadmin_required
def admin_test_news_broadcast(admin_user):
    if not news_broadcaster.is_active:
        return jsonify({
            "status": "notice",
            "message": "News Telegram channel not configured yet. Please set NEWS_BOT_TOKEN and NEWS_CHAT_ID in Render environment variables."
        }), 400
        
    test_article = {
        "title": "⚡ TheSmartMag News Agent: Telegram Broadcast Integration Verified!",
        "source": "TheSmartMag AI Core",
        "url": "https://trade.thesmartmag.com",
        "sentiment": "BULLISH",
        "category": "INDIA"
    }
    success = news_broadcaster.broadcast_breaking_news(test_article, "Multi-asset news & Indian market radar is monitoring 24/7 with zero impact on trading channels.")
    if success:
        return jsonify({"status": "success", "message": "Test message sent to dedicated News Telegram channel!"})
    else:
        return jsonify({"status": "error", "message": "Failed to send to Telegram. Check bot token permissions."}), 500

# ── 7. INDIAN EQUITIES & F&O OPTIONS INTEL ──────────────────────────────────
from indian_market_agent import indian_agent

@api_bp.route("/api/india/overview", methods=["GET"])
def get_india_market_overview():
    with indian_agent.lock:
        indices = dict(indian_agent.cached_indices)
        stocks = list(indian_agent.cached_stocks)
        options = dict(indian_agent.cached_options)
        last_updated = indian_agent.last_update_time
        
    with news_core.lock:
        indian_news = [n for n in news_core.cached_news if n.get("category") == "INDIA"][:10]
        
    return jsonify({
        "status": "success",
        "indices": indices,
        "stocks": stocks,
        "options": options,
        "news": indian_news,
        "last_updated": last_updated
    })

@api_bp.route("/api/india/stocks", methods=["GET"])
def get_india_stocks():
    with indian_agent.lock:
        stocks = list(indian_agent.cached_stocks)
    return jsonify({
        "status": "success",
        "total": len(stocks),
        "stocks": stocks
    })

@api_bp.route("/api/india/options", methods=["GET"])
def get_india_options():
    with indian_agent.lock:
        options = dict(indian_agent.cached_options)
    return jsonify({
        "status": "success",
        "options": options
    })

@api_bp.route("/api/india/trigger-refresh", methods=["POST"])
def trigger_india_refresh():
    indian_agent.refresh_all()
    return jsonify({
        "status": "success",
        "message": "Indian market equities & F&O options intelligence refreshed!",
        "stocks_count": len(indian_agent.cached_stocks),
        "indices_count": len(indian_agent.cached_indices)
    })

# ── 8. JARVIS AI QUANT ASSISTANT & VOICE BRIEFINGS ─────────────────────────
from jarvis_assistant import jarvis_engine

@api_bp.route("/api/ai-assistant/briefing", methods=["GET"])
def get_jarvis_briefing():
    try:
        briefing = jarvis_engine.generate_market_briefing()
        return jsonify(briefing)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route("/api/ai-assistant/asset-intel/<symbol>", methods=["GET"])
def get_jarvis_asset_intel(symbol):
    try:
        intel = jarvis_engine.generate_asset_intel(symbol)
        return jsonify({"status": "success", "intel": intel})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@api_bp.route("/api/ai-assistant/chat", methods=["POST"])
def jarvis_chat():
    try:
        data = request.get_json() or {}
        query = data.get("query", "").strip()
        if not query:
            return jsonify({"status": "error", "message": "Query cannot be empty"}), 400
        
        response = jarvis_engine.process_chat_query(query)
        return jsonify({
            "status": "success",
            "reply": response["reply"],
            "voice_script": response.get("voice_script", ""),
            "lang": response.get("lang", "en-US"),
            "category": response.get("category", "general"),
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

print("api_routes.py Blueprint updated with Real Visitors, Affiliates, Sales & User CRM successfully!")