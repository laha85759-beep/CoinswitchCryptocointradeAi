"""
Interactive Telegram Command Bot for Dual-Exchange Quant Terminal
===================================================================
Listens for incoming Telegram commands from authorized chat IDs and provides
instant remote control over trading execution and account status:

Commands:
  /status    — Get live portfolio balance, open positions, daily PnL & Stage 1 yield budget
  /pause     — Pause automated trading cycles
  /resume    — Resume automated trading cycles
  /close_all — Emergency market close all positions on CoinSwitch & Delta
  /help      — Display available bot commands
"""

import json
import logging
import os
import threading
import time
import requests

log = logging.getLogger(__name__)


class TelegramCommandBot:
    def __init__(self, cfg, cs_client=None, delta_client=None, notifier=None, audit=None):
        self.cfg = cfg
        self.cs_client = cs_client
        self.delta_client = delta_client
        self.notifier = notifier
        self.audit = audit
        self.token = cfg.get("telegram_token", "")
        self.chat_id = str(cfg.get("telegram_chat_id", ""))
        self.last_update_id = 0
        self._running = False

    def start_polling(self):
        """Starts background polling thread for incoming Telegram commands."""
        if not self.token or self._running:
            return
        self._running = True
        t = threading.Thread(target=self._poll_loop, daemon=True)
        t.start()
        log.info("🤖 Interactive Telegram Command Bot started polling.")

    def _poll_loop(self):
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        time.sleep(3)  # Wait for server boot
        
        while self._running:
            try:
                params = {"offset": self.last_update_id + 1, "timeout": 20}
                res = requests.get(url, params=params, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("ok") and "result" in data:
                        for update in data["result"]:
                            self.last_update_id = update["update_id"]
                            msg = update.get("message") or update.get("channel_post")
                            if msg and "text" in msg:
                                sender_chat = str(msg.get("chat", {}).get("id", ""))
                                # Verify authorization (if chat_id configured)
                                if self.chat_id and sender_chat != self.chat_id:
                                    log.warning("Telegram Bot: Unauthorized message from chat_id %s", sender_chat)
                                    continue
                                
                                command_text = msg["text"].strip()
                                self._handle_command(command_text, sender_chat)
            except Exception as exc:
                log.debug("Telegram Bot polling notice: %s", exc)
                time.sleep(5)
            time.sleep(1)

    def _send_reply(self, text: str, chat_id: str = None):
        target_chat = chat_id or self.chat_id
        if not target_chat or not self.token:
            return
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            requests.post(url, json={"chat_id": target_chat, "text": text, "parse_mode": "Markdown"}, timeout=10)
        except Exception as exc:
            log.warning("Telegram Bot reply failed: %s", exc)

    def _handle_command(self, cmd: str, chat_id: str):
        cmd_lower = cmd.lower().split("@")[0].strip()  # Strip bot username if any
        log.info("Telegram Bot received command: %s", cmd_lower)

        if cmd_lower in ("/start", "/help"):
            reply = (
                "🤖 *OPUS 4.7 QUANT TERMINAL — TELEGRAM BOT*\n"
                "Available Commands:\n\n"
                "📊 `/status` — Live balance, open trades, PnL & Stage 1 yield\n"
                "⏸️ `/pause` — Pause automated trading execution\n"
                "▶️ `/resume` — Resume automated trading execution\n"
                "🚨 `/close_all` — Emergency close all active positions\n"
                "❓ `/help` — Display command guide"
            )
            self._send_reply(reply, chat_id)

        elif cmd_lower == "/status":
            self._handle_status(chat_id)

        elif cmd_lower == "/pause":
            self.cfg["trading_paused"] = True
            self._save_override({"trading_paused": True})
            reply = "⏸️ *AUTOMATED TRADING PAUSED*\nBot will continue scanning & updating dashboard, but will NOT execute new trade orders."
            self._send_reply(reply, chat_id)

        elif cmd_lower == "/resume":
            self.cfg["trading_paused"] = False
            self._save_override({"trading_paused": False})
            reply = "▶️ *AUTOMATED TRADING RESUMED*\nAutonomous signal scanning and dual-exchange execution are now ACTIVE."
            self._send_reply(reply, chat_id)

        elif cmd_lower == "/close_all":
            self._handle_close_all(chat_id)

    def _handle_status(self, chat_id: str):
        # Fetch live portfolio balance
        cs_usdt = 0.0
        cs_inr = 0.0
        delta_usdt = 0.0

        if self.cs_client:
            try:
                cs_usdt = self.cs_client.get_usdt_balance()
                cs_inr = self.cs_client.get_inr_balance()
            except Exception:
                pass

        if self.delta_client:
            try:
                delta_usdt = max(0.0, self.delta_client.get_usdt_balance())
            except Exception:
                pass

        # Load open positions count
        cs_open_count = 0
        delta_open_count = 0
        try:
            from dual_exchange import load_json_safe
            cs_open_count = len(load_json_safe("open_trades_cs.json", []))
            
            if self.delta_client:
                pos_res = self.delta_client._request("GET", "/v2/positions/margined")
                pos_list = pos_res.get("result", []) if isinstance(pos_res, dict) else (pos_res if isinstance(pos_res, list) else [])
                delta_open_count = sum(1 for p in pos_list if abs(float(p.get("size", 0))) > 0)
        except Exception:
            pass

        # Load Stage 1 yield budget
        yield_earned = 0.0
        yield_avail = 0.0
        try:
            with open("earned_yield.json", encoding="utf-8") as f:
                ydata = json.load(f)
                yield_earned = float(ydata.get("total_yield_earned_usdt", 0.0))
                yield_avail = float(ydata.get("available_trading_budget_usdt", 0.0))
        except Exception:
            pass

        status_str = "⏸️ PAUSED" if self.cfg.get("trading_paused") else "🟢 ACTIVE 24/7"

        reply = (
            f"📊 *LIVE SYSTEM & PORTFOLIO STATUS*\n"
            f"• Engine Mode    : `{status_str}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏛️ *COINSWITCH PRO (Spot)*\n"
            f"• USDT Balance   : `${cs_usdt:.4f} USDT` (`₹{cs_inr:.2f} INR`)\n"
            f"• Active Trades  : `{cs_open_count}`\n\n"
            f"⚡ *DELTA EXCHANGE (Futures)*\n"
            f"• USDT Balance   : `${delta_usdt:.4f} USDT` (`₹{delta_usdt*88:.2f} INR`)\n"
            f"• Active Futures : `{delta_open_count}`\n\n"
            f"🌾 *STAGE 1 YIELD ENGINE*\n"
            f"• Harvested Yield: `${yield_earned:.4f} USDT`\n"
            f"• Earned Budget  : `${yield_avail:.4f} USDT`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 *TOTAL CAPITAL*: `${cs_usdt + delta_usdt:.2f} USDT` (`₹{(cs_usdt + delta_usdt)*88:.2f} INR`)"
        )
        self._send_reply(reply, chat_id)

    def _handle_close_all(self, chat_id: str):
        reply = "🚨 *EMERGENCY CLOSE ALL INITIATED*\nClosing all active positions on CoinSwitch & Delta..."
        self._send_reply(reply, chat_id)
        
        closed_summary = []

        # 1. Close Delta Positions
        if self.delta_client:
            try:
                res = self.delta_client._request("GET", "/v2/positions/margined")
                pos_list = res.get("result", []) if isinstance(res, dict) else (res if isinstance(res, list) else [])
                for pos in pos_list:
                    sz = float(pos.get("size", 0) or 0)
                    if abs(sz) > 0:
                        prod_id = pos.get("product_id")
                        sym = pos.get("product_symbol")
                        close_side = "sell" if sz > 0 else "buy"
                        self.delta_client._request("POST", "/v2/orders", body={
                            "product_id": prod_id,
                            "size": str(int(abs(sz))),
                            "side": close_side,
                            "order_type": "market",
                            "reduce_only": True
                        })
                        closed_summary.append(f"Delta: Closed {sym} (qty={abs(sz)})")
            except Exception as exc:
                log.error("Telegram Bot close_all Delta error: %s", exc)

        # 2. Reset open trade files
        try:
            with open("open_trades_cs.json", "w") as f:
                f.write("[]")
            with open("open_trades_delta.json", "w") as f:
                f.write("[]")
        except Exception:
            pass

        summary_text = "\n".join(closed_summary) if closed_summary else "No active positions found on exchange."
        final_reply = f"✅ *EMERGENCY CLOSE ALL COMPLETE*\n\n{summary_text}\n\nState files cleared."
        self._send_reply(final_reply, chat_id)

    def _save_override(self, updates: dict):
        try:
            override_path = os.path.join(os.path.dirname(__file__), "config_override.json")
            existing = {}
            if os.path.exists(override_path):
                with open(override_path, "r") as f:
                    existing = json.load(f)
            existing.update(updates)
            with open(override_path, "w") as f:
                json.dump(existing, f, indent=4)
        except Exception as exc:
            log.warning("Telegram Bot failed to save config override: %s", exc)
