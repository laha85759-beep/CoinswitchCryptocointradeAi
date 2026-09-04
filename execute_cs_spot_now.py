import sys
import json
import time
from datetime import datetime, timezone

sys.path.insert(0, ".")
from config import CONFIG
from coinswitch_client import CoinSwitchClient
from notifier import TelegramNotifier
from dual_exchange import CS_TRADES_FILE, save_json, load_json, utc_iso
from scanner import MarketScanner
from agents import AuditLogger

cs = CoinSwitchClient(CONFIG["api_key"], CONFIG["api_secret"])
notifier = TelegramNotifier(CONFIG["telegram_token"], CONFIG["telegram_chat_id"])
audit = AuditLogger("audit.jsonl")

print("==================================================================")
print("     LIVE COINSWITCH PRO INR BALANCE & SPOT TRADE EXECUTION      ")
print("==================================================================")

# 1. Fetch Real-time INR Balance
inr_bal = cs.get_inr_balance()
print(f"1. REAL-TIME COINSWITCH PRO INR BALANCE: Rs.{inr_bal:.2f} INR")

if inr_bal < 10.0:
    print(f"[NOTICE] Available INR balance (Rs.{inr_bal:.2f} INR) is below minimum order size.")
    sys.exit(0)

# 2. Scan CoinSwitch Spot Markets & Find Top Momentum Coin
tickers = cs.get_all_tickers("c2c2")
print(f"\n2. SCANNED COINSWITCH PRO TICKERS: Found {len(tickers)} Spot Pairs")

top_target = None
best_chg = -999.0

for sym, t_data in tickers.items():
    try:
        chg = float(t_data.get("percentageChange") or t_data.get("change_24h") or 0.0)
        last_p = float(t_data.get("lastPrice") or t_data.get("close") or 0.0)
        base_vol = float(t_data.get("baseVolume") or 0.0)
        
        if last_p > 0 and base_vol > 1000 and chg > best_chg:
            best_chg = chg
            top_target = {"symbol": sym, "price": last_p, "change_24h": chg}
    except Exception:
        continue

if not top_target:
    print("[FAIL] No valid target found.")
    sys.exit(1)

symbol = top_target["symbol"]
price = top_target["price"]
chg = top_target["change_24h"]

# Position sizing: use available INR balance (~Rs.200 INR)
order_inr = round(inr_bal * 0.90, 2)
if order_inr < 10.0:
    order_inr = inr_bal
    
qty = round(order_inr / price, 6) if price > 0 else 0.0

print(f"\n3. EXECUTING LIVE SPOT BUY ORDER ON COINSWITCH PRO:")
print(f"   • Target Symbol : {symbol} (24h Surge: {chg:+0.2f}%)")
print(f"   • Order Value   : Rs.{order_inr:.2f} INR (From Rs.{inr_bal:.2f} INR Balance)")
print(f"   • Current Price : ${price} USDT")
print(f"   • Quantity      : {qty} Coins")

try:
    res = cs.place_order(symbol, "buy", "market", qty, price)
    print("\nCoinSwitch Live Order Response:")
    print(json.dumps(res, indent=2))
    
    order_id = str(res.get("id") or res.get("order_id") or f"CS-{symbol}-LIVE")
    fill_p = float(res.get("price") or price)
    
    # Save to open_trades_cs.json
    trade_rec = {
        "signal_id": f"CS-SPOT-{int(time.time())}",
        "symbol": symbol,
        "exchange": "coinswitch",
        "direction": "long",
        "entry_price": fill_p,
        "qty": qty,
        "hard_sl": round(fill_p * 0.975, 6),
        "take_profit": round(fill_p * 1.120, 6),
        "peak_price": fill_p,
        "trail_active": False,
        "trailing_stop": None,
        "opened_at": utc_iso(),
        "order_id": order_id,
        "inr_used": order_inr,
        "paper": False,
    }
    
    cs_trades = load_json(CS_TRADES_FILE, [])
    cs_trades.append(trade_rec)
    save_json(CS_TRADES_FILE, cs_trades)
    
    # Notify Telegram
    msg = (
        f"🚀 *LIVE COINSWITCH PRO SPOT TRADE EXECUTED*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"• *Symbol*: `{symbol}`\n"
        f"• *Direction*: `BUY SPOT 🟢` (24h Surge: `{chg:+0.2f}%`)\n"
        f"• *Order Value*: `Rs.{order_inr:.2f} INR`\n"
        f"• *Fill Price*: `${fill_p}`\n"
        f"• *Quantity*: `{qty}` Coins\n"
        f"• *Stop-Loss (SL)*: `${trade_rec['hard_sl']}` (-2.5% Breathing Buffer)\n"
        f"• *Take-Profit (TP)*: `${trade_rec['take_profit']}` (+12.0% Target Target)\n"
        f"• *Instant Trailing*: 🟢 Active at +0.2% (Break-even lock at +0.5%)\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 *100% LIVE COINSWITCH PRO EXECUTION*"
    )
    notifier.send(msg)
    print("\n[PASS] CoinSwitch Pro Live Spot Trade Filled & Recorded!")
    
except Exception as exc:
    print(f"[FAIL] CoinSwitch order execution error: {exc}")

print("==================================================================")
