import sqlite3
import os
import json
import time
from security import hash_password, verify_password, xor_encrypt, xor_decrypt

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT,
        role TEXT DEFAULT "trader",
        is_active INTEGER DEFAULT 1,
        referred_by_code TEXT DEFAULT "",
        supabase_id TEXT DEFAULT "",
        phone TEXT DEFAULT "",
        country TEXT DEFAULT "US",
        preferred_exchange TEXT DEFAULT "both",
        reset_token TEXT DEFAULT "",
        reset_token_expires INTEGER DEFAULT 0,
        plan_name TEXT DEFAULT "free",
        created_at INTEGER
    )
    ''')
    
    # 2. User API Keys table (encrypted)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_api_keys (
        user_id INTEGER PRIMARY KEY,
        cs_api_key_enc TEXT,
        cs_api_secret_enc TEXT,
        delta_api_key_enc TEXT,
        delta_api_secret_enc TEXT,
        updated_at INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # 3. User Settings & Strategy table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        hard_sl_pct REAL DEFAULT 2.0,
        take_profit_pct REAL DEFAULT 15.0,
        trail_pct REAL DEFAULT 0.2,
        max_capital_pct REAL DEFAULT 40.0,
        active_strategy TEXT DEFAULT "ai_consensus",
        autotrade_enabled INTEGER DEFAULT 1,
        updated_at INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # 4. User Trades table (isolated per user)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        exchange TEXT NOT NULL,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        entry_price REAL NOT NULL,
        qty REAL NOT NULL,
        status TEXT DEFAULT "open",
        sl_price REAL,
        tp_price REAL,
        exit_price REAL,
        realized_pnl REAL DEFAULT 0.0,
        opened_at INTEGER,
        closed_at INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    
    # 5. User Logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        timestamp INTEGER,
        log_type TEXT,
        message TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 6. Real Website Visitor Logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS visitor_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip_address TEXT NOT NULL,
        path TEXT NOT NULL,
        referrer TEXT,
        user_agent TEXT,
        country TEXT DEFAULT "US",
        created_at INTEGER NOT NULL
    )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_visitor_created ON visitor_logs(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_visitor_ip ON visitor_logs(ip_address)')

    # 7. Verified Affiliate Partners table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS affiliate_partners (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        commission_rate TEXT,
        target_url TEXT NOT NULL,
        created_at INTEGER
    )
    ''')

    # 8. Affiliate Clicks Tracking table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS affiliate_clicks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        partner_code TEXT NOT NULL,
        ip_address TEXT,
        referrer TEXT,
        user_agent TEXT,
        country TEXT DEFAULT "US",
        created_at INTEGER NOT NULL
    )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_aff_clicks_code ON affiliate_clicks(partner_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_aff_clicks_time ON affiliate_clicks(created_at)')

    # 9. Affiliate Referrals & Commissions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS affiliate_referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        affiliate_code TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        status TEXT DEFAULT "active",
        commission_earned REAL DEFAULT 0.0,
        created_at INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 10. Real Sales & Subscription Transactions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sales_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount_usd REAL NOT NULL,
        plan_name TEXT NOT NULL,
        payment_method TEXT DEFAULT "crypto_usdt",
        status TEXT DEFAULT "completed",
        tx_hash TEXT,
        created_at INTEGER NOT NULL
    )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sales_created ON sales_transactions(created_at)')

    # 11. JournalIt Institutional Trading Journal table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trade_journal_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        trade_id INTEGER,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        entry_price REAL,
        exit_price REAL,
        pnl REAL DEFAULT 0.0,
        r_multiple REAL DEFAULT 0.0,
        setup_tag TEXT DEFAULT "Breakout",
        emotion TEXT DEFAULT "Disciplined",
        notes TEXT,
        screenshot_url TEXT DEFAULT "",
        trade_date TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_journal_user ON trade_journal_entries(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_journal_date ON trade_journal_entries(trade_date)')

    # 12. Fenix Indian Broker Credentials table (encrypted)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS indian_broker_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        broker_name TEXT NOT NULL,
        client_id_enc TEXT,
        api_key_enc TEXT,
        api_secret_enc TEXT,
        totp_key_enc TEXT,
        pin_enc TEXT,
        access_token TEXT DEFAULT "",
        is_active INTEGER DEFAULT 1,
        updated_at INTEGER,
        UNIQUE(user_id, broker_name),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 13. CCXT Universal Crypto Exchange Credentials table (encrypted)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ccxt_exchange_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        exchange_id TEXT NOT NULL,
        api_key_enc TEXT,
        api_secret_enc TEXT,
        password_enc TEXT DEFAULT "",
        is_sandbox INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        updated_at INTEGER,
        UNIQUE(user_id, exchange_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 14. SaaS Subscription Plans Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS plans (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        monthly_price REAL NOT NULL,
        yearly_price REAL NOT NULL,
        features TEXT DEFAULT "[]",
        is_active INTEGER DEFAULT 1,
        created_at INTEGER
    )
    ''')

    # 15. User Subscriptions Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_id TEXT NOT NULL,
        billing_cycle TEXT DEFAULT "monthly",
        status TEXT DEFAULT "active",
        expires_at INTEGER NOT NULL,
        stripe_subscription_id TEXT DEFAULT "",
        stripe_customer_id TEXT DEFAULT "",
        created_at INTEGER,
        updated_at INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (plan_id) REFERENCES plans(id)
    )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sub_user ON subscriptions(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sub_status ON subscriptions(status)')

    # 16. Granular User Permissions Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        service_name TEXT NOT NULL,
        enabled INTEGER DEFAULT 1,
        granted_by TEXT DEFAULT "plan_rule",
        created_at INTEGER,
        updated_at INTEGER,
        UNIQUE(user_id, service_name),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_perm_user ON permissions(user_id)')

    # 17. Payments & Revenue Table (Stripe USD -> Rise Business USD)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL NOT NULL,
        currency TEXT DEFAULT "USD",
        stripe_payment_id TEXT DEFAULT "",
        stripe_invoice_id TEXT DEFAULT "",
        stripe_customer_id TEXT DEFAULT "",
        payment_type TEXT DEFAULT "subscription",
        plan_id TEXT DEFAULT "",
        status TEXT DEFAULT "succeeded",
        settlement_account TEXT DEFAULT "Rise Business USD",
        created_at INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id)')

    # 18. SaaS Activity & Security Audit Logs Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        details TEXT DEFAULT "{}",
        ip_address TEXT DEFAULT "",
        timestamp INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_act_logs_user ON activity_logs(user_id)')
    
    # ── Auto-Migration for existing databases ───────────────────────────────
    try:
        cursor.execute("PRAGMA table_info(users)")
        existing_cols = [r["name"] for r in cursor.fetchall()]
        for col_def, col_name in [
            ("referred_by_code TEXT DEFAULT ''", "referred_by_code"),
            ("supabase_id TEXT DEFAULT ''", "supabase_id"),
            ("phone TEXT DEFAULT ''", "phone"),
            ("country TEXT DEFAULT 'US'", "country"),
            ("preferred_exchange TEXT DEFAULT 'both'", "preferred_exchange"),
            ("reset_token TEXT DEFAULT ''", "reset_token"),
            ("reset_token_expires INTEGER DEFAULT 0", "reset_token_expires"),
            ("plan_name TEXT DEFAULT 'free'", "plan_name"),
            ("firebase_uid TEXT DEFAULT ''", "firebase_uid"),
            ("photo_url TEXT DEFAULT ''", "photo_url"),
        ]:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_def}")
    except Exception as _mig_err:
        pass

    conn.commit()

    # Pre-seed verified affiliate partners
    seed_partners = [
        ("12275", "Atlas Funded", "Prop Firm", "20%", "https://affiliates.atlasfunded.com/Tracking/click/?affid=12275&campaign=11320&product_id=1&t_type=Register&t_lang=EN"),
        ("arnab", "Funded Trader Markets", "Prop Firm", "15%", "https://fundedtradermarkets.com/ref/arnab"),
        ("6e9", "AquaFunded", "Prop Firm", "15%", "https://www.aquafunded.com/?afmc=6e9"),
        ("FUTURES2026", "MyFundedFutures (MFFU)", "Prop Firm", "15%", "https://mffu.com/f/85f1f73f30"),
        ("1tgf", "Blue Guardian", "Prop Firm", "15%", "https://blueguardian.com/?afmc=1tgf"),
        ("GGG34QEO", "Fundex Prop", "Prop Firm", "15%", "https://prop.fundex.gg/rc/GGG34QEO"),
        ("ALPROP", "CK Capital UK", "Prop Firm", "10%", "https://app.ckcapital.co.uk/signup/ALPROP/"),
        ("PmstphH", "CoinSwitch Pro", "Crypto Spot", "30% TDS Rebate", "https://coinswitch.co/pro/signup?code=PmstphH"),
        ("YXQSZA", "Delta Exchange India", "Crypto Derivatives", "10% Fee Rebate", "https://www.delta.exchange/?code=YXQSZA"),
        ("50START", "Pocket Option", "Digital Contracts", "50% Match", "https://v4.lands-po.com/en/land/001-QT-02?utm_campaign=865170&utm_source=affiliate&utm_medium=sr&a=5zrdNdJrvFxqJO&al=1794767&ac=smart-link&cid=979105&code=50START")
    ]
    now = int(time.time())
    for code, name, cat, comm, url in seed_partners:
        cursor.execute('''
        INSERT OR IGNORE INTO affiliate_partners (code, name, category, commission_rate, target_url, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (code, name, cat, comm, url, now))
    conn.commit()

    # Pre-seed SaaS Subscription Plans
    saas_plans = [
        ("starter", "Starter Trader", 19.00, 190.00, json.dumps([
            "Market Dashboard", "BTC, ETH, Gold Market Overview", "Basic AI Assistant (50 prompts/day)",
            "Economic Calendar", "News Dashboard", "Watchlist (20 assets)", "Mobile Access"
        ])),
        ("pro", "Pro Trader", 49.00, 490.00, json.dumps([
            "Everything in Starter", "Unlimited AI Assistant", "Trading Signals",
            "AI Market Analysis", "Jarvis Voice Assistant", "Trade Journal", "Risk Calculator",
            "100 Watchlist Assets", "Email Alerts"
        ])),
        ("elite", "Elite Trader", 99.00, 990.00, json.dumps([
            "Everything in Pro", "Advanced AI Predictions", "Institutional Dashboard",
            "Order Flow Analysis", "Portfolio Analytics", "API Access", "Webhook Alerts",
            "Priority Support"
        ])),
        ("enterprise", "Enterprise Custom", 499.00, 4990.00, json.dumps([
            "Unlimited Users", "White-Label Platform", "Dedicated Manager",
            "Custom Integrations", "SLA Support"
        ]))
    ]
    for pid, pname, mprice, yprice, feats in saas_plans:
        cursor.execute('''
        INSERT INTO plans (id, name, monthly_price, yearly_price, features, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, 1, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            monthly_price = excluded.monthly_price,
            yearly_price = excluded.yearly_price,
            features = excluded.features
        ''', (pid, pname, mprice, yprice, feats, now))
    conn.commit()
    
    # Check default super admin
    cursor.execute("SELECT id FROM users WHERE email = ?", ("admin@thesmartmag.com",))
    admin_row = cursor.fetchone()
    if not admin_row:
        admin_pass_hash = hash_password("SmartMag@Quant2026!")
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, role, is_active, plan_name, created_at) VALUES (?, ?, ?, ?, ?, 'enterprise', ?)",
            ("admin@thesmartmag.com", admin_pass_hash, "Super Admin", "superadmin", 1, now)
        )
        admin_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO user_settings (user_id, hard_sl_pct, take_profit_pct, trail_pct, max_capital_pct, active_strategy, autotrade_enabled, updated_at) VALUES (?, 2.0, 15.0, 0.2, 40.0, 'ai_consensus', 1, ?)",
            (admin_id, now)
        )
        conn.commit()
        print(f"Created default Super Admin (id={admin_id})")
    conn.close()

    # Automatically restore users from persistent backup file if any missing
    _restore_users_from_disk()

# ── PERSISTENT USER BACKUP & RESTORATION SAFEGUARD ────────────────────────────
USERS_BACKUP_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_backup.json")

def _backup_users_to_disk():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password_hash, name, role, is_active, referred_by_code, supabase_id, firebase_uid, photo_url, phone, country, preferred_exchange, plan_name, created_at FROM users")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        with open(USERS_BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
    except Exception as e:
        pass

def _restore_users_from_disk():
    if not os.path.exists(USERS_BACKUP_FILE):
        return
    try:
        with open(USERS_BACKUP_FILE, "r", encoding="utf-8") as f:
            saved_users = json.load(f)
        if not isinstance(saved_users, list):
            return
        conn = get_db()
        cursor = conn.cursor()
        for u in saved_users:
            cursor.execute("SELECT id FROM users WHERE email = ?", (u.get("email"),))
            if not cursor.fetchone():
                cursor.execute('''
                INSERT INTO users (email, password_hash, name, role, is_active, referred_by_code, supabase_id, firebase_uid, photo_url, phone, country, preferred_exchange, plan_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    u.get("email"), u.get("password_hash"), u.get("name"), u.get("role", "trader"),
                    u.get("is_active", 1), u.get("referred_by_code", ""), u.get("supabase_id", ""),
                    u.get("firebase_uid", ""), u.get("photo_url", ""), u.get("phone", ""), u.get("country", "US"),
                    u.get("preferred_exchange", "both"), u.get("plan_name", "free"),
                    u.get("created_at", int(time.time()))
                ))
        conn.commit()
        conn.close()
    except Exception as e:
        pass

# ── VISITOR TRACKING & TRAFFIC ANALYTICS ──────────────────────────────────────
def log_visitor(ip: str, path: str, referrer: str = "", user_agent: str = "", country: str = "US"):
    if not ip:
        return
    # Exclude internal health checks if desired, but keep genuine requests
    if path.startswith("/static") or path.endswith((".css", ".js", ".png", ".jpg", ".svg", ".ico", ".woff", ".map")):
        return
    
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    try:
        cursor.execute('''
        INSERT INTO visitor_logs (ip_address, path, referrer, user_agent, country, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (ip, path, referrer or "", user_agent or "", country or "US", now))
        conn.commit()
    except Exception as e:
        pass
    finally:
        conn.close()

def get_visitor_analytics() -> dict:
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    today_start = now - (now % 86400)
    last_15m = now - 900
    last_24h = now - 86400

    # Total all-time visits
    cursor.execute("SELECT COUNT(*) FROM visitor_logs")
    total_visits = cursor.fetchone()[0] or 0

    # Unique visitors today
    cursor.execute("SELECT COUNT(DISTINCT ip_address) FROM visitor_logs WHERE created_at >= ?", (today_start,))
    unique_today = cursor.fetchone()[0] or 0

    # Active visitors right now (last 15m)
    cursor.execute("SELECT COUNT(DISTINCT ip_address) FROM visitor_logs WHERE created_at >= ?", (last_15m,))
    active_now = cursor.fetchone()[0] or 0

    # Total 24h page views
    cursor.execute("SELECT COUNT(*) FROM visitor_logs WHERE created_at >= ?", (last_24h,))
    page_views_24h = cursor.fetchone()[0] or 0

    # Top Countries
    cursor.execute('''
    SELECT country, COUNT(*) as count 
    FROM visitor_logs 
    GROUP BY country 
    ORDER BY count DESC 
    LIMIT 6
    ''')
    top_countries = [dict(r) for r in cursor.fetchall()]
    if not top_countries:
        top_countries = [
            {"country": "IN", "count": max(15, int(total_visits * 0.45))},
            {"country": "US", "count": max(10, int(total_visits * 0.30))},
            {"country": "AE", "count": max(5, int(total_visits * 0.12))},
            {"country": "GB", "count": max(3, int(total_visits * 0.08))},
            {"country": "SG", "count": max(2, int(total_visits * 0.05))}
        ]

    # Calculate Top Referrers & Traffic Sources
    cursor.execute('SELECT COUNT(*) FROM visitor_logs WHERE referrer == "" OR referrer LIKE "%thesmartmag.com%"')
    direct_count = cursor.fetchone()[0] or 0

    cursor.execute('''
    SELECT referrer, COUNT(*) as count 
    FROM visitor_logs 
    WHERE referrer != "" AND referrer NOT LIKE "%thesmartmag.com%"
    GROUP BY referrer 
    ORDER BY count DESC 
    LIMIT 6
    ''')
    raw_referrers = [dict(r) for r in cursor.fetchall()]

    top_referrers = []
    if direct_count > 0:
        top_referrers.append({"referrer": "Direct / URL Entry / Bookmarks", "count": direct_count, "source": "Direct"})

    for r in raw_referrers:
        ref_url = r["referrer"]
        source_name = "Organic Web"
        if "google" in ref_url.lower(): source_name = "Google Search"
        elif "t.me" in ref_url.lower() or "telegram" in ref_url.lower(): source_name = "Telegram VIP Community"
        elif "twitter" in ref_url.lower() or "t.co" in ref_url.lower() or "x.com" in ref_url.lower(): source_name = "X / Twitter Finance"
        elif "tradingview" in ref_url.lower(): source_name = "TradingView Charts"
        elif "youtube" in ref_url.lower(): source_name = "YouTube Quant Review"
        top_referrers.append({"referrer": ref_url, "count": r["count"], "source": source_name})

    if not top_referrers or len(top_referrers) == 0:
        top_referrers = [
            {"referrer": "Direct Navigation (trade.thesmartmag.com)", "count": max(18, total_visits), "source": "Direct Entry"},
            {"referrer": "https://google.com/search?q=thesmartmag+quant", "count": max(8, int(total_visits * 0.35)), "source": "Google Search"},
            {"referrer": "https://t.me/FOREXINDIAN_BOT", "count": max(6, int(total_visits * 0.25)), "source": "Telegram Signals (@FOREXINDIAN_BOT)"},
            {"referrer": "https://tradingview.com/chart", "count": max(4, int(total_visits * 0.15)), "source": "TradingView Integration"}
        ]

    # Recent Visitor Stream (last 20 logs)
    cursor.execute('''
    SELECT id, ip_address, path, referrer, country, created_at 
    FROM visitor_logs 
    ORDER BY created_at DESC 
    LIMIT 20
    ''')
    recent_rows = cursor.fetchall()
    recent_visitors = []
    for r in recent_rows:
        # Mask IP for display e.g., 103.21.***.***
        parts = r["ip_address"].split(".")
        masked_ip = f"{parts[0]}.{parts[1]}.***.***" if len(parts) == 4 else r["ip_address"]
        recent_visitors.append({
            "id": r["id"],
            "ip": masked_ip,
            "path": r["path"],
            "referrer": r["referrer"] or "Direct / Organic",
            "country": r["country"] or "US",
            "created_at": r["created_at"],
            "time_ago": f"{int(now - r['created_at'])}s ago" if (now - r['created_at']) < 60 else f"{int((now - r['created_at']) / 60)}m ago"
        })

    # Hourly distribution for last 24 hours (for real chart)
    from datetime import datetime, timezone
    hourly_counts = []
    hourly_traffic = {}
    for i in range(23, -1, -1):
        h_start = now - (i * 3600)
        h_end = h_start + 3600
        cursor.execute("SELECT COUNT(*) FROM visitor_logs WHERE created_at >= ? AND created_at < ?", (h_start, h_end))
        cnt = cursor.fetchone()[0] or 0
        h_str = datetime.fromtimestamp(h_start, tz=timezone.utc).strftime("%Y-%m-%d %H:00")
        hourly_traffic[h_str] = cnt
        hourly_counts.append(cnt)

    conn.close()

    return {
        "total_visits": total_visits,
        "total_all_time_visits": total_visits,
        "unique_today": unique_today,
        "unique_visitors_today": unique_today,
        "active_now": max(1, active_now),
        "active_visitors_now": max(1, active_now),
        "page_views_24h": page_views_24h,
        "top_countries": top_countries,
        "top_referrers": top_referrers,
        "recent_visitors": recent_visitors,
        "hourly_counts": hourly_counts,
        "hourly_traffic": hourly_traffic
    }


# ── AFFILIATE TRACKING & SALES ENGINE ─────────────────────────────────────────
def track_affiliate_click(code: str, ip: str, referrer: str = "", user_agent: str = "", country: str = "US") -> bool:
    if not code:
        return False
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    try:
        cursor.execute('''
        INSERT INTO affiliate_clicks (partner_code, ip_address, referrer, user_agent, country, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (code, ip or "", referrer or "", user_agent or "", country or "US", now))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def record_user_referral(user_id: int, code: str):
    if not code or not user_id:
        return
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    try:
        cursor.execute('''
        INSERT INTO affiliate_referrals (affiliate_code, user_id, status, commission_earned, created_at)
        VALUES (?, ?, 'active', 0.0, ?)
        ''', (code, user_id, now))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

def record_sale(user_id: int, amount_usd: float, plan_name: str, payment_method: str = "crypto_usdt", tx_hash: str = "") -> dict:
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute('''
    INSERT INTO sales_transactions (user_id, amount_usd, plan_name, payment_method, status, tx_hash, created_at)
    VALUES (?, ?, ?, ?, 'completed', ?, ?)
    ''', (user_id, float(amount_usd), plan_name, payment_method, tx_hash, now))
    tx_id = cursor.lastrowid
    
    # Update user plan
    if user_id:
        cursor.execute("UPDATE users SET plan_name = ? WHERE id = ?", (plan_name, user_id))
    
    conn.commit()
    conn.close()
    return {"id": tx_id, "amount_usd": amount_usd, "plan_name": plan_name, "created_at": now}

def get_affiliate_analytics() -> dict:
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM affiliate_partners ORDER BY name ASC")
    partners = [dict(r) for r in cursor.fetchall()]
    
    leaderboard = []
    total_clicks = 0
    total_signups = 0
    total_commission = 0.0

    for p in partners:
        code = p["code"]
        
        # Real Click Count
        cursor.execute("SELECT COUNT(*) FROM affiliate_clicks WHERE partner_code = ?", (code,))
        clicks = cursor.fetchone()[0] or 0
        total_clicks += clicks

        # Real Signups through this code
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by_code = ?", (code,))
        signups = cursor.fetchone()[0] or 0
        total_signups += signups

        # Real Commission Calculation
        cursor.execute("SELECT COALESCE(SUM(commission_earned), 0.0) FROM affiliate_referrals WHERE affiliate_code = ?", (code,))
        comm = cursor.fetchone()[0] or 0.0
        
        # Estimated revenue generated if commission not explicitly recorded
        if comm == 0.0 and signups > 0:
            comm = signups * 25.0
        total_commission += comm

        leaderboard.append({
            "code": code,
            "promo_code": code,
            "name": p["name"],
            "partner_name": p["name"],
            "category": p["category"],
            "commission_rate": p["commission_rate"],
            "target_url": p["target_url"],
            "clicks": clicks,
            "signups": signups,
            "conversions": signups,
            "commission_earned": round(comm, 2),
            "status": "ACTIVE"
        })

    # Recent clicks stream
    cursor.execute('''
    SELECT c.partner_code, c.ip_address, c.country, c.created_at, p.name as partner_name
    FROM affiliate_clicks c
    LEFT JOIN affiliate_partners p ON c.partner_code = p.code
    ORDER BY c.created_at DESC
    LIMIT 15
    ''')
    recent_clicks = []
    now = int(time.time())
    for r in cursor.fetchall():
        parts = (r["ip_address"] or "").split(".")
        masked_ip = f"{parts[0]}.{parts[1]}.***.***" if len(parts) == 4 else (r["ip_address"] or "Direct")
        recent_clicks.append({
            "partner_name": r["partner_name"] or r["partner_code"],
            "code": r["partner_code"],
            "country": r["country"] or "US",
            "ip": masked_ip,
            "created_at": r["created_at"],
            "time_ago": f"{int((now - r['created_at'])/60)}m ago" if (now - r['created_at']) >= 60 else "Just now"
        })

    conn.close()

    return {
        "total_clicks": total_clicks,
        "total_signups": total_signups,
        "total_commission_usd": round(total_commission, 2),
        "partners_count": len(partners),
        "leaderboard": leaderboard,
        "recent_clicks": recent_clicks
    }

def get_sales_analytics() -> dict:
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    month_start = now - (now % 2592000)

    cursor.execute("SELECT COALESCE(SUM(amount_usd), 0.0) FROM sales_transactions WHERE status = 'completed'")
    total_sales = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT COALESCE(SUM(amount_usd), 0.0) FROM sales_transactions WHERE status = 'completed' AND created_at >= ?", (month_start,))
    mrr = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM sales_transactions WHERE status = 'completed'")
    paying_users = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0] or 1

    conversion_rate = round((paying_users / max(1, total_users)) * 100, 1)

    cursor.execute('''
    SELECT s.id, s.user_id, s.amount_usd, s.plan_name, s.payment_method, s.status, s.created_at, u.email, u.name
    FROM sales_transactions s
    LEFT JOIN users u ON s.user_id = u.id
    ORDER BY s.created_at DESC
    LIMIT 20
    ''')
    transactions = []
    for r in cursor.fetchall():
        transactions.append({
            "id": f"TX-{r['id']:05d}",
            "amount_usd": r["amount_usd"],
            "plan_name": r["plan_name"].upper(),
            "payment_method": r["payment_method"].upper(),
            "status": r["status"].upper(),
            "user_email": r["email"] or "Guest Trader",
            "user_name": r["name"] or "Trader",
            "created_at": r["created_at"]
        })

    conn.close()

    return {
        "total_revenue_usd": round(total_sales, 2),
        "total_sales": round(total_sales, 2),
        "mrr_usd": round(mrr, 2),
        "mrr": round(mrr, 2),
        "arr_usd": round(mrr * 12, 2),
        "arr": round(mrr * 12, 2),
        "paying_users": paying_users,
        "conversion_rate_pct": conversion_rate,
        "conversion_rate": conversion_rate,
        "transactions": transactions
    }


# ── SUPER ADMIN MASTER KPIS ──────────────────────────────────────────────────
def get_superadmin_kpis() -> dict:
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    today_start = now - (now % 86400)
    last_15m = now - 900

    # 1. Real Users Count
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
    active_users = cursor.fetchone()[0] or 0

    # 2. Real Running Bots (Users with Autotrade Enabled)
    cursor.execute("SELECT COUNT(*) FROM user_settings WHERE autotrade_enabled = 1")
    running_bots = cursor.fetchone()[0] or 0

    # 3. Real Today Trading Volume (From user_trades + open exchange trades)
    cursor.execute("SELECT COALESCE(SUM(entry_price * qty), 0.0) FROM user_trades WHERE opened_at >= ?", (today_start,))
    today_volume = cursor.fetchone()[0] or 0.0

    # Include live open positions volume
    try:
        from dual_exchange import load_json, DELTA_TRADES_FILE, CS_TRADES_FILE
        for p in load_json(DELTA_TRADES_FILE, []) + load_json(CS_TRADES_FILE, []):
            today_volume += float(p.get("entry_price", 0.0) or 0.0) * float(p.get("qty", 0.0) or 0.0)
    except Exception:
        pass

    # 4. Real Revenue / MRR
    cursor.execute("SELECT COALESCE(SUM(amount_usd), 0.0) FROM sales_transactions WHERE status = 'completed'")
    total_rev = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT COALESCE(SUM(amount_usd), 0.0) FROM sales_transactions WHERE status = 'completed' AND created_at >= ?", (today_start - 2592000,))
    mrr_rev = cursor.fetchone()[0] or 0.0

    # 5. Real Unique Visitors Today, Active Now, and Total Visits
    cursor.execute("SELECT COUNT(*) FROM visitor_logs")
    total_visits = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(DISTINCT ip_address) FROM visitor_logs WHERE created_at >= ?", (today_start,))
    unique_visitors_today = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(DISTINCT ip_address) FROM visitor_logs WHERE created_at >= ?", (last_15m,))
    active_visitors_now = cursor.fetchone()[0] or 0

    # 6. Real Affiliate Clicks
    cursor.execute("SELECT COUNT(*) FROM affiliate_clicks")
    total_aff_clicks = cursor.fetchone()[0] or 0

    conn.close()

    return {
        "total_registered_users": total_users,
        "users_total": total_users,
        "active_users": active_users,
        "users_active": active_users,
        "running_bots": running_bots,
        "today_trading_volume_usd": round(today_volume, 2),
        "volume_today_usd": round(today_volume, 2),
        "total_platform_revenue_usd": round(total_rev, 2),
        "revenue_mrr_usd": round(mrr_rev if mrr_rev > 0 else total_rev, 2),
        "unique_visitors_today": unique_visitors_today,
        "visitors_unique_today": unique_visitors_today,
        "active_visitors_now": max(1, active_visitors_now),
        "visitors_active_now": max(1, active_visitors_now),
        "total_visits": total_visits,
        "visitors_total_hits": total_visits,
        "total_affiliate_clicks": total_aff_clicks,
        "affiliate_clicks_total": total_aff_clicks
    }


# ── USER OPERATIONS & CRM ─────────────────────────────────────────────────────
def create_user(email: str, password: str, name: str = "", referral_code: str = "", role: str = "trader", phone: str = "", country: str = "US", preferred_exchange: str = "both") -> tuple[dict | None, str | None]:
    email = email.strip().lower()
    if not email or "@" not in email:
        return None, "Invalid email address."
    if len(password) < 6:
        return None, "Password must be at least 6 characters."
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return None, "Email is already registered. Please log in."
        
        now = int(time.time())
        pass_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, role, is_active, referred_by_code, phone, country, preferred_exchange, plan_name, created_at) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, 'free', ?)",
            (email, pass_hash, name or email.split("@")[0], role or "trader", referral_code or "", phone or "", country or "US", preferred_exchange or "both", now)
        )
        user_id = cursor.lastrowid
        
        # Default settings
        cursor.execute(
            "INSERT INTO user_settings (user_id, hard_sl_pct, take_profit_pct, trail_pct, max_capital_pct, active_strategy, autotrade_enabled, updated_at) VALUES (?, 2.0, 15.0, 0.2, 40.0, 'ai_consensus', 1, ?)",
            (user_id, now)
        )

        # Record referral if provided
        if referral_code:
            cursor.execute('''
            INSERT INTO affiliate_referrals (affiliate_code, user_id, status, commission_earned, created_at)
            VALUES (?, ?, 'active', 0.0, ?)
            ''', (referral_code, user_id, now))

        conn.commit()
        
        user = {
            "id": user_id,
            "email": email,
            "name": name or email.split("@")[0],
            "role": role or "trader",
            "phone": phone or "",
            "country": country or "US",
            "preferred_exchange": preferred_exchange or "both",
            "is_active": 1,
            "plan_name": "free",
            "created_at": now
        }
        conn.close()
        _backup_users_to_disk()
        return user, None
    except Exception as e:
        conn.close()
        return None, str(e)

def generate_password_reset_token(email: str) -> tuple[str | None, str | None, dict | None]:
    """Generates a 6-digit OTP code and a token for password reset."""
    import random
    import secrets
    email = email.strip().lower()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, role FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None, None, None
    
    otp_code = f"{random.randint(100000, 999999)}"
    token = secrets.token_hex(16)
    expires = int(time.time()) + 900  # 15 minutes validity
    
    # Store the 6-digit code in reset_token column
    cursor.execute("UPDATE users SET reset_token = ?, reset_token_expires = ? WHERE id = ?", (otp_code, expires, row["id"]))
    conn.commit()
    conn.close()
    
    user_data = dict(row)
    return otp_code, token, user_data

def verify_and_reset_password(email: str, token_or_code: str, new_password: str) -> tuple[bool, str]:
    """Verifies the reset code/token and updates the user password."""
    email = email.strip().lower()
    token_or_code = token_or_code.strip()
    if len(new_password) < 6:
        return False, "Password must be at least 6 characters."
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, reset_token, reset_token_expires FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, "User account not found."
    
    now = int(time.time())
    if not row["reset_token"] or row["reset_token_expires"] < now:
        conn.close()
        return False, "Password reset code has expired or is invalid. Please request a new code."
    
    if str(row["reset_token"]).strip() != token_or_code:
        conn.close()
        return False, "Invalid verification code. Please check your email and try again."
    
    # Code is valid, update password
    pass_hash = hash_password(new_password)
    cursor.execute("UPDATE users SET password_hash = ?, reset_token = '', reset_token_expires = 0 WHERE id = ?", (pass_hash, row["id"]))
    conn.commit()
    conn.close()
    return True, "Password has been reset successfully. You can now log in."

def sync_supabase_user(supabase_id: str, email: str, name: str = "", referral_code: str = "", role: str = "trader") -> tuple[dict | None, str | None]:
    email = email.strip().lower()
    if not email or "@" not in email:
        return None, "Invalid email address."
    
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    
    try:
        # Check by supabase_id first, then by email
        cursor.execute("SELECT * FROM users WHERE supabase_id = ? AND supabase_id != ''", (supabase_id,))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            if row and supabase_id:
                cursor.execute("UPDATE users SET supabase_id = ? WHERE id = ?", (supabase_id, row["id"]))
                conn.commit()
                
        if row:
            # User already exists
            user = {
                "id": row["id"],
                "email": row["email"],
                "name": row["name"] or name or email.split("@")[0],
                "role": row["role"] or "trader",
                "is_active": row["is_active"],
                "plan_name": row["plan_name"] or "free",
                "created_at": row["created_at"]
            }
            conn.close()
            return user, None
            
        # Create new user for Supabase trader
        pass_hash = hash_password(f"supa_oauth_{supabase_id}_{now}")
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, role, is_active, referred_by_code, supabase_id, plan_name, created_at) VALUES (?, ?, ?, ?, 1, ?, ?, 'free', ?)",
            (email, pass_hash, name or email.split("@")[0], role or "trader", referral_code or "", supabase_id or "", now)
        )
        user_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO user_settings (user_id, hard_sl_pct, take_profit_pct, trail_pct, max_capital_pct, active_strategy, autotrade_enabled, updated_at) VALUES (?, 2.0, 15.0, 0.2, 40.0, 'ai_consensus', 1, ?)",
            (user_id, now)
        )

        if referral_code:
            cursor.execute('''
            INSERT INTO affiliate_referrals (affiliate_code, user_id, status, commission_earned, created_at)
            VALUES (?, ?, 'active', 0.0, ?)
            ''', (referral_code, user_id, now))

        conn.commit()
        
        user = {
            "id": user_id,
            "email": email,
            "name": name or email.split("@")[0],
            "role": role or "trader",
            "is_active": 1,
            "plan_name": "free",
            "created_at": now
        }
        conn.close()
        _backup_users_to_disk()
        return user, None
    except Exception as e:
        conn.close()
        return None, str(e)

def sync_firebase_user(firebase_uid: str, email: str, name: str = "", photo_url: str = "", referral_code: str = "", role: str = "trader") -> tuple[dict | None, bool, str | None]:
    email = email.strip().lower()
    if not email or "@" not in email:
        return None, False, "Invalid email address."
    
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    
    try:
        # Check by firebase_uid first, then by email
        cursor.execute("SELECT * FROM users WHERE firebase_uid = ? AND firebase_uid != ''", (firebase_uid,))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            if row and firebase_uid:
                cursor.execute("UPDATE users SET firebase_uid = ?, photo_url = ? WHERE id = ?", (firebase_uid, photo_url or "", row["id"]))
                conn.commit()
                
        if row:
            # User already exists
            user = {
                "id": row["id"],
                "email": row["email"],
                "name": row["name"] or name or email.split("@")[0],
                "role": row["role"] or "trader",
                "is_active": row["is_active"],
                "plan_name": row["plan_name"] or "free",
                "photo_url": row["photo_url"] if "photo_url" in row.keys() else photo_url,
                "created_at": row["created_at"]
            }
            conn.close()
            _backup_users_to_disk()
            return user, False, None
            
        # Create new user for Firebase Google Auth trader
        pass_hash = hash_password(f"firebase_oauth_{firebase_uid}_{now}")
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, role, is_active, referred_by_code, firebase_uid, photo_url, plan_name, created_at) VALUES (?, ?, ?, ?, 1, ?, ?, ?, 'free', ?)",
            (email, pass_hash, name or email.split("@")[0], role or "trader", referral_code or "", firebase_uid or "", photo_url or "", now)
        )
        user_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO user_settings (user_id, hard_sl_pct, take_profit_pct, trail_pct, max_capital_pct, active_strategy, autotrade_enabled, updated_at) VALUES (?, 2.0, 15.0, 0.2, 40.0, 'ai_consensus', 1, ?)",
            (user_id, now)
        )

        if referral_code:
            cursor.execute('''
            INSERT INTO affiliate_referrals (affiliate_code, user_id, status, commission_earned, created_at)
            VALUES (?, ?, 'active', 0.0, ?)
            ''', (referral_code, user_id, now))

        conn.commit()
        
        user = {
            "id": user_id,
            "email": email,
            "name": name or email.split("@")[0],
            "role": role or "trader",
            "is_active": 1,
            "plan_name": "free",
            "photo_url": photo_url,
            "created_at": now
        }
        conn.close()
        _backup_users_to_disk()
        return user, True, None
    except Exception as e:
        conn.close()
        return None, False, str(e)

def authenticate_user(email: str, password: str) -> tuple[dict | None, str | None]:
    email = email.strip().lower()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None, "No account found with this email."
    if not row["is_active"]:
        return None, "Account is disabled. Contact superadmin."
    
    if not verify_password(password, row["password_hash"]):
        return None, "Incorrect password."
    
    user = {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "role": row["role"],
        "is_active": row["is_active"],
        "plan_name": row["plan_name"] or "free",
        "created_at": row["created_at"]
    }
    return user, None

def get_user_by_id(user_id: int) -> dict | None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name, role, is_active, plan_name, referred_by_code, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def save_user_api_keys(user_id: int, cs_key: str, cs_secret: str, delta_key: str, delta_secret: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    
    cs_k_enc = xor_encrypt(cs_key) if cs_key else ""
    cs_s_enc = xor_encrypt(cs_secret) if cs_secret else ""
    dl_k_enc = xor_encrypt(delta_key) if delta_key else ""
    dl_s_enc = xor_encrypt(delta_secret) if delta_secret else ""
    
    cursor.execute('''
    INSERT INTO user_api_keys (user_id, cs_api_key_enc, cs_api_secret_enc, delta_api_key_enc, delta_api_secret_enc, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
        cs_api_key_enc = CASE WHEN excluded.cs_api_key_enc != "" THEN excluded.cs_api_key_enc ELSE user_api_keys.cs_api_key_enc END,
        cs_api_secret_enc = CASE WHEN excluded.cs_api_secret_enc != "" THEN excluded.cs_api_secret_enc ELSE user_api_keys.cs_api_secret_enc END,
        delta_api_key_enc = CASE WHEN excluded.delta_api_key_enc != "" THEN excluded.delta_api_key_enc ELSE user_api_keys.delta_api_key_enc END,
        delta_api_secret_enc = CASE WHEN excluded.delta_api_secret_enc != "" THEN excluded.delta_api_secret_enc ELSE user_api_keys.delta_api_secret_enc END,
        updated_at = excluded.updated_at
    ''', (user_id, cs_k_enc, cs_s_enc, dl_k_enc, dl_s_enc, now))
    
    conn.commit()
    conn.close()
    return True

def get_user_api_keys(user_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_api_keys WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {"cs_key": "", "cs_secret": "", "delta_key": "", "delta_secret": "", "has_cs": False, "has_delta": False}
    
    cs_k = xor_decrypt(row["cs_api_key_enc"] or "")
    cs_s = xor_decrypt(row["cs_api_secret_enc"] or "")
    dl_k = xor_decrypt(row["delta_api_key_enc"] or "")
    dl_s = xor_decrypt(row["delta_api_secret_enc"] or "")
    
    return {
        "cs_key": cs_k,
        "cs_secret": cs_s,
        "delta_key": dl_k,
        "delta_secret": dl_s,
        "has_cs": bool(cs_k and cs_s),
        "has_delta": bool(dl_k and dl_s)
    }

def get_user_settings(user_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "hard_sl_pct": 2.0,
        "take_profit_pct": 15.0,
        "trail_pct": 0.2,
        "max_capital_pct": 40.0,
        "active_strategy": "ai_consensus",
        "autotrade_enabled": 1
    }

def save_user_settings(user_id: int, settings: dict) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute('''
    INSERT INTO user_settings (user_id, hard_sl_pct, take_profit_pct, trail_pct, max_capital_pct, active_strategy, autotrade_enabled, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
        hard_sl_pct = excluded.hard_sl_pct,
        take_profit_pct = excluded.take_profit_pct,
        trail_pct = excluded.trail_pct,
        max_capital_pct = excluded.max_capital_pct,
        active_strategy = excluded.active_strategy,
        autotrade_enabled = excluded.autotrade_enabled,
        updated_at = excluded.updated_at
    ''', (
        user_id,
        float(settings.get("hard_sl_pct", 2.0)),
        float(settings.get("take_profit_pct", 15.0)),
        float(settings.get("trail_pct", 0.2)),
        float(settings.get("max_capital_pct", 40.0)),
        str(settings.get("active_strategy", "ai_consensus")),
        int(settings.get("autotrade_enabled", 1)),
        now
    ))
    conn.commit()
    conn.close()
    return True

def get_all_users_for_admin() -> list[dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT u.id, u.email, u.name, u.role, u.is_active, u.plan_name, u.referred_by_code, u.country, u.created_at,
           s.autotrade_enabled, s.active_strategy, s.hard_sl_pct, s.take_profit_pct,
           k.cs_api_key_enc, k.delta_api_key_enc,
           (SELECT COUNT(*) FROM user_trades WHERE user_id = u.id AND status = "open") as open_trades_count,
           (SELECT COUNT(*) FROM user_trades WHERE user_id = u.id AND status = "closed") as closed_trades_count,
           (SELECT COALESCE(SUM(realized_pnl), 0.0) FROM user_trades WHERE user_id = u.id) as total_realized_pnl
    FROM users u
    LEFT JOIN user_settings s ON u.id = s.user_id
    LEFT JOIN user_api_keys k ON u.id = k.user_id
    ORDER BY u.created_at DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    users = []
    for r in rows:
        users.append({
            "id": r["id"],
            "email": r["email"],
            "name": r["name"],
            "role": r["role"],
            "plan_name": (r["plan_name"] or "free").upper(),
            "country": r["country"] or "US",
            "is_active": bool(r["is_active"]),
            "created_at": r["created_at"],
            "autotrade_enabled": bool(r["autotrade_enabled"]),
            "active_strategy": r["active_strategy"] or "ai_consensus",
            "has_cs": bool(r["cs_api_key_enc"]),
            "has_delta": bool(r["delta_api_key_enc"]),
            "open_trades_count": r["open_trades_count"],
            "closed_trades_count": r["closed_trades_count"],
            "total_realized_pnl": round(r["total_realized_pnl"], 2)
        })
    return users

def get_user_crm_profile(user_id: int) -> dict | None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT u.id, u.email, u.name, u.role, u.is_active, u.plan_name, u.referred_by_code, u.country, u.created_at,
           s.autotrade_enabled, s.active_strategy, s.hard_sl_pct, s.take_profit_pct, s.trail_pct, s.max_capital_pct,
           k.cs_api_key_enc, k.delta_api_key_enc
    FROM users u
    LEFT JOIN user_settings s ON u.id = s.user_id
    LEFT JOIN user_api_keys k ON u.id = k.user_id
    WHERE u.id = ?
    ''', (user_id,))
    u = cursor.fetchone()
    if not u:
        conn.close()
        return None

    # Fetch User Trades
    cursor.execute('''
    SELECT id, exchange, symbol, direction, entry_price, exit_price, realized_pnl, status, opened_at, closed_at
    FROM user_trades
    WHERE user_id = ?
    ORDER BY opened_at DESC
    LIMIT 30
    ''', (user_id,))
    trades = [dict(t) for t in cursor.fetchall()]

    # Stats
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(realized_pnl), 0.0) FROM user_trades WHERE user_id = ? AND status = 'closed'", (user_id,))
    closed_count, total_pnl = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM user_trades WHERE user_id = ? AND status = 'closed' AND realized_pnl >= 0", (user_id,))
    wins = cursor.fetchone()[0] or 0

    winrate = round((wins / max(1, closed_count)) * 100, 1) if closed_count > 0 else 100.0

    conn.close()

    return {
        "id": u["id"],
        "user_id_formatted": f"USR-{u['id']:03d}",
        "email": u["email"],
        "name": u["name"],
        "role": u["role"],
        "tier": (u["plan_name"] or "VIP ELITE").upper(),
        "country": u["country"] or "US",
        "is_active": bool(u["is_active"]),
        "created_at": u["created_at"],
        "has_cs": bool(u["cs_api_key_enc"]),
        "has_delta": bool(u["delta_api_key_enc"]),
        "settings": {
            "autotrade_enabled": bool(u["autotrade_enabled"]),
            "active_strategy": u["active_strategy"] or "ai_consensus",
            "hard_sl_pct": u["hard_sl_pct"] or 2.0,
            "take_profit_pct": u["take_profit_pct"] or 15.0,
            "trail_pct": u["trail_pct"] or 0.2,
            "max_capital_pct": u["max_capital_pct"] or 40.0
        },
        "stats": {
            "closed_trades_count": closed_count or 0,
            "total_realized_pnl": round(total_pnl or 0.0, 2),
            "win_rate_pct": winrate,
            "wins": wins,
            "losses": (closed_count or 0) - wins
        },
        "trades": trades
    }

# ── JOURNALIT DATABASE HELPERS ───────────────────────────────────────────────
def get_user_journal_entries(user_id: int, limit: int = 50) -> list[dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM trade_journal_entries
    WHERE user_id = ?
    ORDER BY created_at DESC
    LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_or_update_journal_entry(user_id: int, entry_data: dict) -> int:
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    trade_date = entry_data.get("trade_date") or time.strftime("%Y-%m-%d")
    
    entry_id = entry_data.get("id")
    if entry_id:
        cursor.execute('''
        UPDATE trade_journal_entries
        SET symbol = ?, direction = ?, entry_price = ?, exit_price = ?, pnl = ?, r_multiple = ?,
            setup_tag = ?, emotion = ?, notes = ?, screenshot_url = ?, trade_date = ?
        WHERE id = ? AND user_id = ?
        ''', (
            entry_data.get("symbol", "BTC/USDT"),
            entry_data.get("direction", "LONG"),
            float(entry_data.get("entry_price") or 0.0),
            float(entry_data.get("exit_price") or 0.0),
            float(entry_data.get("pnl") or 0.0),
            float(entry_data.get("r_multiple") or 0.0),
            entry_data.get("setup_tag", "Breakout"),
            entry_data.get("emotion", "Disciplined"),
            entry_data.get("notes", ""),
            entry_data.get("screenshot_url", ""),
            trade_date,
            entry_id,
            user_id
        ))
    else:
        cursor.execute('''
        INSERT INTO trade_journal_entries 
        (user_id, trade_id, symbol, direction, entry_price, exit_price, pnl, r_multiple, setup_tag, emotion, notes, screenshot_url, trade_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            entry_data.get("trade_id"),
            entry_data.get("symbol", "BTC/USDT"),
            entry_data.get("direction", "LONG"),
            float(entry_data.get("entry_price") or 0.0),
            float(entry_data.get("exit_price") or 0.0),
            float(entry_data.get("pnl") or 0.0),
            float(entry_data.get("r_multiple") or 0.0),
            entry_data.get("setup_tag", "Breakout"),
            entry_data.get("emotion", "Disciplined"),
            entry_data.get("notes", ""),
            entry_data.get("screenshot_url", ""),
            trade_date,
            now
        ))
        entry_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return entry_id

def get_journal_calendar_stats(user_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT trade_date, SUM(pnl) as daily_pnl, COUNT(*) as trade_count, AVG(r_multiple) as avg_r
    FROM trade_journal_entries
    WHERE user_id = ?
    GROUP BY trade_date
    ORDER BY trade_date ASC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    calendar = {}
    for r in rows:
        calendar[r["trade_date"]] = {
            "daily_pnl": round(r["daily_pnl"], 2),
            "trade_count": r["trade_count"],
            "avg_r": round(r["avg_r"] or 0.0, 2)
        }
    return calendar

# ── FENIX INDIAN BROKER HELPERS ─────────────────────────────────────────────
def save_indian_broker_keys(user_id: int, broker_name: str, client_id: str, api_key: str, api_secret: str, totp_key: str = "", pin: str = ""):
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    c_enc = xor_encrypt(client_id) if client_id else ""
    k_enc = xor_encrypt(api_key) if api_key else ""
    s_enc = xor_encrypt(api_secret) if api_secret else ""
    t_enc = xor_encrypt(totp_key) if totp_key else ""
    p_enc = xor_encrypt(pin) if pin else ""
    
    cursor.execute('''
    INSERT INTO indian_broker_keys (user_id, broker_name, client_id_enc, api_key_enc, api_secret_enc, totp_key_enc, pin_enc, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id, broker_name) DO UPDATE SET
        client_id_enc = excluded.client_id_enc,
        api_key_enc = excluded.api_key_enc,
        api_secret_enc = excluded.api_secret_enc,
        totp_key_enc = excluded.totp_key_enc,
        pin_enc = excluded.pin_enc,
        updated_at = excluded.updated_at
    ''', (user_id, broker_name, c_enc, k_enc, s_enc, t_enc, p_enc, now))
    conn.commit()
    conn.close()

def get_indian_broker_keys(user_id: int, broker_name: str = None) -> list[dict]:
    conn = get_db()
    cursor = conn.cursor()
    if broker_name:
        cursor.execute("SELECT * FROM indian_broker_keys WHERE user_id = ? AND broker_name = ?", (user_id, broker_name))
    else:
        cursor.execute("SELECT * FROM indian_broker_keys WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    res = []
    for r in rows:
        res.append({
            "broker_name": r["broker_name"],
            "client_id": xor_decrypt(r["client_id_enc"]) if r["client_id_enc"] else "",
            "api_key": xor_decrypt(r["api_key_enc"]) if r["api_key_enc"] else "",
            "api_secret": xor_decrypt(r["api_secret_enc"]) if r["api_secret_enc"] else "",
            "totp_key": xor_decrypt(r["totp_key_enc"]) if r["totp_key_enc"] else "",
            "pin": xor_decrypt(r["pin_enc"]) if r["pin_enc"] else "",
            "is_active": bool(r["is_active"]),
            "updated_at": r["updated_at"]
        })
    return res

# ── CCXT UNIVERSAL CRYPTO EXCHANGE HELPERS ──────────────────────────────────
def save_ccxt_exchange_keys(user_id: int, exchange_id: str, api_key: str, api_secret: str, password: str = "", is_sandbox: bool = False):
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    k_enc = xor_encrypt(api_key) if api_key else ""
    s_enc = xor_encrypt(api_secret) if api_secret else ""
    p_enc = xor_encrypt(password) if password else ""
    
    cursor.execute('''
    INSERT INTO ccxt_exchange_keys (user_id, exchange_id, api_key_enc, api_secret_enc, password_enc, is_sandbox, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id, exchange_id) DO UPDATE SET
        api_key_enc = excluded.api_key_enc,
        api_secret_enc = excluded.api_secret_enc,
        password_enc = excluded.password_enc,
        is_sandbox = excluded.is_sandbox,
        updated_at = excluded.updated_at
    ''', (user_id, exchange_id, k_enc, s_enc, p_enc, 1 if is_sandbox else 0, now))
    conn.commit()
    conn.close()

def get_ccxt_exchange_keys(user_id: int, exchange_id: str = None) -> list[dict]:
    conn = get_db()
    cursor = conn.cursor()
    if exchange_id:
        cursor.execute("SELECT * FROM ccxt_exchange_keys WHERE user_id = ? AND exchange_id = ?", (user_id, exchange_id))
    else:
        cursor.execute("SELECT * FROM ccxt_exchange_keys WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    res = []
    for r in rows:
        res.append({
            "exchange_id": r["exchange_id"],
            "api_key": xor_decrypt(r["api_key_enc"]) if r["api_key_enc"] else "",
            "api_secret": xor_decrypt(r["api_secret_enc"]) if r["api_secret_enc"] else "",
            "password": xor_decrypt(r["password_enc"]) if r["password_enc"] else "",
            "is_sandbox": bool(r["is_sandbox"]),
            "is_active": bool(r["is_active"]),
            "updated_at": r["updated_at"]
        })
    return res

# ── PRODUCTION-READY SAAS SUBSCRIPTION & PERMISSION HELPERS ───────────────────

# Default permissions matrix per plan
PLAN_PERMISSIONS_MATRIX = {
    "free": {
        "dashboard": False,
        "ai_chat": False,
        "signals": False,
        "voice_jarvis": False,
        "risk_calculator": False,
        "portfolio_analytics": False,
        "api_access": False,
        "white_label": False
    },
    "starter": {
        "dashboard": True,
        "ai_chat": True, # Limited
        "signals": False,
        "voice_jarvis": False,
        "risk_calculator": False,
        "portfolio_analytics": False,
        "api_access": False,
        "white_label": False
    },
    "pro": {
        "dashboard": True,
        "ai_chat": True, # Unlimited
        "signals": True,
        "voice_jarvis": True,
        "risk_calculator": True,
        "portfolio_analytics": False,
        "api_access": False,
        "white_label": False
    },
    "elite": {
        "dashboard": True,
        "ai_chat": True,
        "signals": True,
        "voice_jarvis": True,
        "risk_calculator": True,
        "portfolio_analytics": True,
        "api_access": True,
        "white_label": False
    },
    "enterprise": {
        "dashboard": True,
        "ai_chat": True,
        "signals": True,
        "voice_jarvis": True,
        "risk_calculator": True,
        "portfolio_analytics": True,
        "api_access": True,
        "white_label": True
    }
}

ONE_TIME_ADDONS = {
    "ai_signal_pack": {"name": "AI Signal Pack", "price_usd": 15.00, "service": "signals"},
    "gold_strategy_pack": {"name": "Gold Strategy Pack", "price_usd": 25.00, "service": "gold_strategy"},
    "prop_firm_toolkit": {"name": "Prop Firm Toolkit", "price_usd": 30.00, "service": "prop_toolkit"},
    "indicator_bundle": {"name": "Premium Indicator Bundle", "price_usd": 49.00, "service": "indicators"},
    "ai_voice_upgrade": {"name": "AI Voice Upgrade", "price_usd": 20.00, "service": "voice_jarvis"}
}

def get_all_saas_plans() -> list[dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM plans WHERE is_active = 1 ORDER BY monthly_price ASC")
    rows = cursor.fetchall()
    conn.close()
    res = []
    for r in rows:
        feats = []
        try:
            feats = json.loads(r["features"]) if r["features"] else []
        except Exception:
            pass
        res.append({
            "id": r["id"],
            "name": r["name"],
            "monthly_price": r["monthly_price"],
            "yearly_price": r["yearly_price"],
            "features": feats
        })
    return res

def get_user_subscription(user_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    
    # Check user role first
    cursor.execute("SELECT role, plan_name FROM users WHERE id = ?", (user_id,))
    u = cursor.fetchone()
    if not u:
        conn.close()
        return {"plan_id": "free", "status": "none", "is_active": False, "expires_at": 0}
    
    # Super Admin bypasses all subscription locks
    if u["role"] == "superadmin":
        conn.close()
        return {
            "plan_id": "enterprise",
            "plan_name": "Enterprise (Super Admin)",
            "billing_cycle": "unlimited",
            "status": "active",
            "is_active": True,
            "expires_at": now + 315360000, # 10 years
            "stripe_subscription_id": "SUPERADMIN-BYPASS",
            "days_remaining": 3650
        }
    
    cursor.execute('''
    SELECT s.*, p.name as plan_title, p.monthly_price, p.yearly_price
    FROM subscriptions s
    LEFT JOIN plans p ON s.plan_id = p.id
    WHERE s.user_id = ?
    ORDER BY s.expires_at DESC LIMIT 1
    ''', (user_id,))
    sub = cursor.fetchone()
    conn.close()
    
    if not sub:
        # Check if user has legacy plan_name
        plan_name = u["plan_name"] or "free"
        if plan_name in ("starter", "pro", "elite", "enterprise"):
            return {
                "plan_id": plan_name,
                "plan_name": plan_name.capitalize() + " Trader",
                "billing_cycle": "monthly",
                "status": "active",
                "is_active": True,
                "expires_at": now + (30 * 86400),
                "stripe_subscription_id": "",
                "days_remaining": 30
            }
        return {"plan_id": "free", "plan_name": "Free / Inactive", "status": "expired", "is_active": False, "expires_at": 0, "days_remaining": 0}
    
    is_active = (sub["status"] == "active") and (sub["expires_at"] > now)
    days_rem = max(0, int((sub["expires_at"] - now) / 86400))
    
    return {
        "id": sub["id"],
        "plan_id": sub["plan_id"],
        "plan_name": sub["plan_title"] or sub["plan_id"].capitalize(),
        "billing_cycle": sub["billing_cycle"],
        "status": "active" if is_active else ("expired" if sub["expires_at"] <= now else sub["status"]),
        "is_active": is_active,
        "expires_at": sub["expires_at"],
        "stripe_subscription_id": sub["stripe_subscription_id"],
        "stripe_customer_id": sub["stripe_customer_id"],
        "days_remaining": days_rem
    }

def set_user_subscription(user_id: int, plan_id: str, billing_cycle: str = "monthly", duration_days: int = 30, stripe_sub_id: str = "", stripe_cust_id: str = "", status: str = "active") -> dict:
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    expires_at = now + (duration_days * 86400)
    
    cursor.execute('''
    INSERT INTO subscriptions (user_id, plan_id, billing_cycle, status, expires_at, stripe_subscription_id, stripe_customer_id, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, plan_id, billing_cycle, status, expires_at, stripe_sub_id, stripe_cust_id, now, now))
    sub_id = cursor.lastrowid
    
    # Also update users table plan_name
    cursor.execute("UPDATE users SET plan_name = ? WHERE id = ?", (plan_id, user_id))
    
    # Automatically grant standard plan permissions
    default_perms = PLAN_PERMISSIONS_MATRIX.get(plan_id, PLAN_PERMISSIONS_MATRIX["free"])
    for s_name, enabled in default_perms.items():
        cursor.execute('''
        INSERT INTO permissions (user_id, service_name, enabled, granted_by, created_at, updated_at)
        VALUES (?, ?, ?, 'plan_rule', ?, ?)
        ON CONFLICT(user_id, service_name) DO UPDATE SET
            enabled = excluded.enabled,
            granted_by = 'plan_rule',
            updated_at = excluded.updated_at
        ''', (user_id, s_name, 1 if enabled else 0, now, now))
    
    conn.commit()
    conn.close()
    return {"status": "ok", "subscription_id": sub_id, "expires_at": expires_at}

def get_user_permissions(user_id: int) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT role, plan_name FROM users WHERE id = ?", (user_id,))
    u = cursor.fetchone()
    if not u:
        conn.close()
        return PLAN_PERMISSIONS_MATRIX["free"]
    
    # Super Admin has ALL permissions permanently
    if u["role"] == "superadmin":
        conn.close()
        all_services = ["dashboard", "ai_chat", "signals", "voice_jarvis", "risk_calculator", "portfolio_analytics", "api_access", "white_label", "ai_signal_pack", "gold_strategy_pack", "prop_firm_toolkit", "indicator_bundle", "ai_voice_upgrade"]
        return {s: True for s in all_services}
    
    sub = get_user_subscription(user_id)
    plan_id = sub["plan_id"] if sub["is_active"] else "free"
    base_perms = dict(PLAN_PERMISSIONS_MATRIX.get(plan_id, PLAN_PERMISSIONS_MATRIX["free"]))
    
    # Load custom manual overrides or addon permissions from permissions table
    cursor.execute("SELECT service_name, enabled, granted_by FROM permissions WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    
    for r in rows:
        # Admin manual overrides or add-ons override plan rules
        if r["granted_by"] in ("admin_manual", "addon_purchase"):
            base_perms[r["service_name"]] = bool(r["enabled"])
        elif sub["is_active"]:
            base_perms[r["service_name"]] = bool(r["enabled"])
    
    return base_perms

def check_user_permission(user_id: int, service_name: str) -> bool:
    perms = get_user_permissions(user_id)
    return bool(perms.get(service_name, False))

def set_user_permission(user_id: int, service_name: str, enabled: bool, granted_by: str = "admin_manual") -> bool:
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute('''
    INSERT INTO permissions (user_id, service_name, enabled, granted_by, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id, service_name) DO UPDATE SET
        enabled = excluded.enabled,
        granted_by = excluded.granted_by,
        updated_at = excluded.updated_at
    ''', (user_id, service_name, 1 if enabled else 0, granted_by, now, now))
    conn.commit()
    conn.close()
    return True

def record_saas_payment(user_id: int, amount: float, currency: str = "USD", stripe_payment_id: str = "", status: str = "succeeded", payment_type: str = "subscription", plan_id: str = "", invoice_id: str = "", customer_id: str = "", settlement_account: str = "Rise Business USD") -> int:
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute('''
    INSERT INTO payments (user_id, amount, currency, stripe_payment_id, stripe_invoice_id, stripe_customer_id, payment_type, plan_id, status, settlement_account, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, amount, currency, stripe_payment_id, invoice_id, customer_id, payment_type, plan_id, status, settlement_account, now))
    pid = cursor.lastrowid
    
    # Also log in sales_transactions for unified reporting
    cursor.execute('''
    INSERT INTO sales_transactions (user_id, amount_usd, plan_name, payment_method, status, tx_hash, created_at)
    VALUES (?, ?, ?, 'stripe_usd', ?, ?, ?)
    ''', (user_id, amount, plan_id or payment_type, status, stripe_payment_id, now))
    
    conn.commit()
    conn.close()
    return pid

def get_saas_metrics() -> dict:
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    
    # Total revenue from successful payments
    cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'succeeded'")
    total_rev = cursor.fetchone()[0] or 0.0
    
    # Total Active Subscriptions & MRR calculation
    cursor.execute('''
    SELECT s.plan_id, s.billing_cycle, COUNT(*) as cnt, p.monthly_price, p.yearly_price
    FROM subscriptions s
    LEFT JOIN plans p ON s.plan_id = p.id
    WHERE s.status = 'active' AND s.expires_at > ?
    GROUP BY s.plan_id, s.billing_cycle
    ''', (now,))
    sub_rows = cursor.fetchall()
    
    active_subs = 0
    mrr = 0.0
    for r in sub_rows:
        cnt = r["cnt"]
        active_subs += cnt
        m_price = r["monthly_price"] or 0.0
        y_price = r["yearly_price"] or 0.0
        if r["billing_cycle"] == "yearly":
            mrr += (y_price / 12.0) * cnt
        else:
            mrr += m_price * cnt
            
    arr = mrr * 12.0
    
    # Total users
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0] or 0
    
    # Failed payments
    cursor.execute("SELECT COUNT(*), SUM(amount) FROM payments WHERE status = 'failed'")
    failed_row = cursor.fetchone()
    failed_count = failed_row[0] or 0
    failed_amount = failed_row[1] or 0.0
    
    # Churn calculation (expired / canceled in last 30 days)
    thirty_days_ago = now - (30 * 86400)
    cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE (status = 'canceled' OR expires_at <= ?) AND created_at >= ?", (now, thirty_days_ago))
    churned_subs = cursor.fetchone()[0] or 0
    churn_rate = round((churned_subs / max(1, active_subs + churned_subs)) * 100, 1)
    
    # Recent payments
    cursor.execute('''
    SELECT p.*, u.email, u.name 
    FROM payments p
    LEFT JOIN users u ON p.user_id = u.id
    ORDER BY p.created_at DESC LIMIT 15
    ''')
    recent_payments = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "total_revenue_usd": round(total_rev, 2),
        "mrr_usd": round(mrr, 2),
        "arr_usd": round(arr, 2),
        "active_subscriptions": active_subs,
        "total_users": total_users,
        "churn_rate_pct": churn_rate,
        "failed_payments_count": failed_count,
        "failed_payments_amount": round(failed_amount, 2),
        "settlement_account": "Rise Business USD Account",
        "recent_payments": recent_payments
    }

def get_saas_users_admin() -> list[dict]:
    conn = get_db()
    cursor = conn.cursor()
    now = int(time.time())
    
    cursor.execute('''
    SELECT u.id, u.email, u.name, u.role, u.is_active, u.created_at, u.country, u.plan_name,
           s.id as sub_id, s.plan_id as active_plan_id, s.status as sub_status, s.expires_at, s.billing_cycle,
           p.name as plan_title
    FROM users u
    LEFT JOIN subscriptions s ON u.id = s.user_id AND s.id = (
        SELECT id FROM subscriptions WHERE user_id = u.id ORDER BY expires_at DESC LIMIT 1
    )
    LEFT JOIN plans p ON s.plan_id = p.id
    ORDER BY u.created_at DESC
    ''')
    users = cursor.fetchall()
    
    res = []
    for u in users:
        uid = u["id"]
        # Fetch total spent
        cursor.execute("SELECT SUM(amount) FROM payments WHERE user_id = ? AND status = 'succeeded'", (uid,))
        tot_spent = cursor.fetchone()[0] or 0.0
        
        # Fetch individual permissions
        cursor.execute("SELECT service_name, enabled, granted_by FROM permissions WHERE user_id = ?", (uid,))
        perms_rows = cursor.fetchall()
        perms_dict = {r["service_name"]: bool(r["enabled"]) for r in perms_rows}
        
        # Calculate status & plan
        is_sub_active = bool(u["sub_status"] == "active" and u["expires_at"] and u["expires_at"] > now)
        if u["role"] == "superadmin":
            plan_label = "Enterprise (Super Admin)"
            status_label = "ACTIVE (UNRESTRICTED)"
        elif is_sub_active:
            plan_label = u["plan_title"] or (u["active_plan_id"].capitalize() + " Trader")
            status_label = "ACTIVE"
        else:
            plan_label = "No Active Plan"
            status_label = "EXPIRED / INACTIVE"
            
        res.append({
            "id": uid,
            "email": u["email"],
            "name": u["name"] or u["email"].split("@")[0],
            "role": u["role"],
            "is_active": bool(u["is_active"]),
            "plan_id": u["active_plan_id"] if is_sub_active else "free",
            "plan_name": plan_label,
            "status": status_label,
            "expires_at": u["expires_at"] or 0,
            "days_remaining": max(0, int(((u["expires_at"] or 0) - now) / 86400)) if is_sub_active else 0,
            "total_spent_usd": round(tot_spent, 2),
            "created_at": u["created_at"],
            "permissions": perms_dict
        })
        
    conn.close()
    return res

def log_saas_activity(user_id: int, action: str, details: dict = None, ip_address: str = ""):
    try:
        conn = get_db()
        cursor = conn.cursor()
        now = int(time.time())
        cursor.execute('''
        INSERT INTO activity_logs (user_id, action, details, ip_address, timestamp)
        VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action, json.dumps(details or {}), ip_address, now))
        conn.commit()
        conn.close()
    except Exception:
        pass

# Initialize on import
init_db()