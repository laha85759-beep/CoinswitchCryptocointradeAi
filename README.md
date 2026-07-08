# 🤖 CoinSwitch Pro — AI Auto-Trading Bot

Scans 80+ crypto pairs on CoinSwitch, scores each using 6 AI signals,
and automatically buys pump candidates with maximum capital deployment.
Runs 24/7 via GitHub Actions (free).

---

## ⚙️ How It Works

```
Every 15 min (GitHub Actions)
        │
        ▼
  MONITOR open trades
  ─ TP limit order filled? → Close (profit) ✅
  ─ Price ≤ SL price?      → Market sell    🛑
        │
        ▼
  SCAN top 80 USDT pairs
  ─ Download 5-min candles
  ─ Score each coin 0–100 using 6 signals:
      EMA 9/21 cross     (20%)
      RSI                (20%)
      VWAP position      (15%)
      Volume spike       (20%)
      5-candle momentum  (15%)
      Bollinger squeeze  (10%)
        │
        ▼
  Score ≥ 72 → BUY
  ─ Market BUY with 95% of free USDT (max capital)
  ─ Limit SELL at TP (+1.5%) placed immediately
  ─ SL price (-0.7%) monitored every 15 min
  ─ Telegram alert sent 📱
```

---

## 🚀 Setup

### 1. Fork this repo
Keep it **private** (your API keys are in GitHub Secrets, but still).

### 2. Get CoinSwitch Pro API Keys
1. Log in → [CoinSwitch Pro](https://pro.coinswitch.co)
2. Go to **Settings → API Keys → Generate New Key**
3. Copy `API Key` and `Secret Key`

### 3. Add GitHub Secrets
**Settings → Secrets and variables → Actions → New repository secret**

| Secret             | Value                        |
|--------------------|------------------------------|
| `CS_API_KEY`       | CoinSwitch API key           |
| `CS_API_SECRET`    | CoinSwitch Secret key        |
| `TELEGRAM_TOKEN`   | Telegram bot token (optional)|
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID        |

### 4. Enable GitHub Actions
**Actions tab** → Enable workflows

### 5. Manually trigger first run
**Actions → CoinSwitch AI Trading Bot → Run workflow**
Check the logs to confirm it's scanning correctly.

---

## 📊 Key Settings (`config.py`)

| Setting             | Default | What it does                              |
|---------------------|---------|-------------------------------------------|
| `pump_score_min`    | 72      | Min AI score to trigger a BUY            |
| `max_capital_pct`   | 95      | % of USDT used per trade (95% = near max)|
| `max_open_trades`   | 2       | Max simultaneous positions                |
| `tp_pct`            | 1.5     | Take profit % above entry                 |
| `sl_pct`            | 0.7     | Stop loss % below entry                   |
| `top_n_by_volume`   | 80      | How many coins to scan                    |

**To be more aggressive:** lower `pump_score_min` to 65, raise `max_open_trades` to 3.
**To be safer:** raise `pump_score_min` to 78+, lower `max_capital_pct` to 50.

---

## 📱 Telegram Alerts

```
🚀 TRADE OPENED — CoinSwitch
📊 BTC/USDT — BUY
🎯 Signal Score: 81/100
💵 Entry : 67450.00
✅ TP    : 68461.75  (+1.5%)
🛑 SL    : 66977.85  (-0.7%)
📦 Qty   : 0.014 BTC
💰 USDT  : $950.00 (max capital)
⏰ 2026-07-08 14:30 UTC
```

---

## ⚠️ Important Notes

- CoinSwitch is **spot only** — no leverage available (Indian regulatory rules).
- The bot uses **95% of free USDT per trade** for maximum capital efficiency.
- SL is checked every 15 minutes (not real-time) — add a small buffer.
- Start by watching a few cycles before committing large capital.
- Never trade money you cannot afford to lose.

---

## 📁 Files

```
├── main.py                        Entry point
├── scanner.py                     AI signal engine + market scanner
├── trader.py                      Buy/sell executor + TP/SL monitor
├── coinswitch_client.py           CoinSwitch Pro REST API client
├── notifier.py                    Telegram alerts
├── config.py                      All settings
├── requirements.txt
└── .github/workflows/
    └── trading_bot.yml            GitHub Actions (every 15 min)
```
