"""
TradingView Webhook & Zing Trade Bridge Server
===============================================
Listens for incoming TradingView alerts / Zing Trade webhooks and instantly
executes live trades across CoinSwitch Pro & Delta Exchange India.

Compatible with PineScript alertcondition() & Zing Trade webhook format:
{
    "symbol": "SOL/USDT",
    "action": "buy",   # "buy" / "sell" / "pump" / "dump"
    "price": 74.50,
    "secret": "coinswitch_bot_secret_123"
}
"""

import logging
import time
from flask import Flask, request, jsonify

from coinswitch_client import CoinSwitchClient
from delta_client import DeltaClient
from config import CONFIG
from dual_exchange import DualExecutionAgent
from agents import AuditLogger, RiskManagerAgent
from notifier import TelegramNotifier

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = Flask(__name__)

cs_client = CoinSwitchClient(CONFIG["api_key"], CONFIG["api_secret"])
delta_client = DeltaClient(CONFIG["delta_api_key"], CONFIG["delta_api_secret"])
notifier = TelegramNotifier(CONFIG.get("telegram_bot_token", ""), CONFIG.get("telegram_chat_id", ""))
audit = AuditLogger(CONFIG.get("log_file", "trading.log"))

dual_executor = DualExecutionAgent(CONFIG, cs_client, delta_client, notifier, audit)
risk_manager = RiskManagerAgent(CONFIG, cs_client, audit, delta_client=delta_client)

WEBHOOK_SECRET = CONFIG.get("webhook_secret", "coinswitch_bot_secret_123")


from flask import send_from_directory
import os

@app.route("/", methods=["GET"])
def serve_dashboard():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "index.html")

@app.route("/<path:filename>", methods=["GET"])
def serve_static(filename):
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), filename)


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "empty_payload"}), 400

        # Optional security key check
        if data.get("secret") and data.get("secret") != WEBHOOK_SECRET:
            return jsonify({"error": "unauthorized"}), 401

        raw_symbol = str(data.get("symbol", "BTC/USDT")).upper().strip()
        if "/" not in raw_symbol:
            base = raw_symbol.replace("USDT", "").replace("USD", "").replace("INR", "")
            raw_symbol = f"{base}/USDT"

        action = str(data.get("action", "buy")).lower().strip()
        signal_type = "pump" if action in ("buy", "long", "pump") else "dump"
        
        fetched_price = 0.0
        try:
            fetched_price = float(cs_client.get_ticker_price(raw_symbol))
        except Exception:
            pass

        price = float(data.get("price", 0) or fetched_price or 100.0)

        signal = {
            "signal_id": f"TV-{int(time.time()*1000)}",
            "symbol": raw_symbol,
            "signal": signal_type,
            "confidence": 0.95,
            "reason": f"tradingview_webhook_{action}",
            "supporting_data": {
                "price": price,
                "volume_ratio": 2.5,
                "change_5m": 1.5 if signal_type == "pump" else -1.5,
            }
        }

        log.info("Received TradingView / Zing Webhook Signal: %s | Action: %s | Price: %s", raw_symbol, action.upper(), price)

        # Risk Manager Approval
        approval = risk_manager._evaluate_one(signal, False)
        if not approval.get("approved"):
            log.warning("RiskManager rejected webhook signal for %s: %s", raw_symbol, approval.get("reason"))
            return jsonify({"status": "rejected", "reason": approval.get("reason")}), 200

        # Execute live trade across CoinSwitch Pro & Delta Exchange India
        results = dual_executor.execute([approval])
        return jsonify({"status": "executed", "symbol": raw_symbol, "direction": approval.get("direction"), "results": results}), 200

    except Exception as exc:
        log.error("Webhook processing error: %s", exc, exc_info=True)
        return jsonify({"error": str(exc)}), 500


@app.route("/forex-news", methods=["POST"])
def handle_forex_news():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "empty_payload"}), 400

        from forex_factory_agent import ForexFactoryNewsAgent
        ff_agent = ForexFactoryNewsAgent(CONFIG, cs_client, delta_client, notifier, audit)
        results = ff_agent.process_and_execute_news_trades(data)
        return jsonify({"status": "processed", "executed": len(results), "results": results}), 200

    except Exception as exc:
        log.error("Forex news webhook error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/us-earnings", methods=["POST"])
def handle_us_earnings():
    try:
        data = request.get_json(force=True) if request.data else {}
        from us_stocks_earnings_agent import USStocksEarningsAgent
        earn_agent = USStocksEarningsAgent(CONFIG, cs_client, delta_client, notifier, audit)
        results = earn_agent.process_and_execute_earnings_trades(data if data else None)
        return jsonify({"status": "processed", "executed": len(results), "results": results}), 200

    except Exception as exc:
        log.error("US earnings webhook error: %s", exc)
        return jsonify({"error": str(exc)}), 500


@app.route("/ai-trader", methods=["POST"])
def handle_ai_trader():
    try:
        data = request.get_json(force=True) if request.data else {}
        from ai_trader_agent import AITraderAgent
        ai_trader = AITraderAgent(CONFIG, cs_client, delta_client, notifier, audit)
        results = ai_trader.fetch_top_ai_signals_and_copytrade()
        return jsonify({"status": "processed", "executed": len(results), "results": results}), 200

    except Exception as exc:
        log.error("AI-Trader webhook error: %s", exc)
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    port = CONFIG.get("webhook_port", 5000)
    log.info("Starting TradingView, Forex, US Earnings & HKUDS AI-Trader Webhook Bridge Server on port %s...", port)
    app.run(host="0.0.0.0", port=port)
