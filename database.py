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
        role TEXT DEFAULT "user",
        is_active INTEGER DEFAULT 1,
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
    
    conn.commit()
    
    # Check default super admin
    cursor.execute("SELECT id FROM users WHERE email = ?", ("admin@thesmartmag.com",))
    admin_row = cursor.fetchone()
    if not admin_row:
        admin_pass_hash = hash_password("SmartMag@Quant2026!")
        now = int(time.time())
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, role, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
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

# USER OPERATIONS
def create_user(email: str, password: str, name: str = "") -> tuple[dict | None, str | None]:
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
            "INSERT INTO users (email, password_hash, name, role, is_active, created_at) VALUES (?, ?, ?, 'user', 1, ?)",
            (email, pass_hash, name or email.split("@")[0], now)
        )
        user_id = cursor.lastrowid
        
        # Default settings
        cursor.execute(
            "INSERT INTO user_settings (user_id, hard_sl_pct, take_profit_pct, trail_pct, max_capital_pct, active_strategy, autotrade_enabled, updated_at) VALUES (?, 2.0, 15.0, 0.2, 40.0, 'ai_consensus', 1, ?)",
            (user_id, now)
        )
        conn.commit()
        
        user = {
            "id": user_id,
            "email": email,
            "name": name or email.split("@")[0],
            "role": "user",
            "is_active": 1,
            "created_at": now
        }
        conn.close()
        return user, None
    except Exception as e:
        conn.close()
        return None, str(e)

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
        "created_at": row["created_at"]
    }
    return user, None

def get_user_by_id(user_id: int) -> dict | None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name, role, is_active, created_at FROM users WHERE id = ?", (user_id,))
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
    SELECT u.id, u.email, u.name, u.role, u.is_active, u.created_at,
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

# Initialize on import
init_db()
print("Database initialized successfully!")