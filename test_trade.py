"""
Quick connectivity + live order test for CoinSwitch and Delta Exchange India.

Tests:
  1. Fetch ticker price on both exchanges
  2. Fetch USDT balance on both exchanges
  3. Place a minimum-size BUY limit order on both (well below market = won't fill)
  4. Cancel both orders immediately after
  5. Print full results

This verifies API auth, order placement, and cancellation work end-to-end
without actually executing a trade.
"""

import os
import sys
import time
import logging

# Load .env
_dotenv = os.path.join(os.path.dirname(__file__), ".env")
if os.path.isfile(_dotenv):
    with open(_dotenv) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("test_trade")

from coinswitch_client import CoinSwitchClient
from delta_client import DeltaClient

CS_KEY    = os.getenv("CS_API_KEY", "")
CS_SECRET = os.getenv("CS_API_SECRET", "")
DX_KEY    = os.getenv("DELTA_API_KEY", "")
DX_SECRET = os.getenv("DELTA_API_SECRET", "")

TEST_SYMBOL = "BTC/USDT"   # highly liquid — safe for test orders
# Place limit order 5% BELOW market → will not fill, safe to cancel immediately
LIMIT_OFFSET_PCT = 5.0
MIN_QTY_USDT = 12.0        # just above CoinSwitch min order of $10


def sep(title: str) -> None:
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


def test_coinswitch() -> dict:
    sep("COINSWITCH TEST")
    result = {"exchange": "CoinSwitch", "price": None, "balance": None,
              "order_id": None, "cancelled": False, "error": None}
    try:
        cs = CoinSwitchClient(CS_KEY, CS_SECRET, rate_limit_delay=1.0)

        # 1. Price
        price = cs.get_ticker_price(TEST_SYMBOL)
        result["price"] = price
        log.info("CS price %s = %.4f", TEST_SYMBOL, price)

        # 2. Balance
        balance = cs.get_usdt_balance()
        result["balance"] = balance
        log.info("CS USDT balance = %.4f", balance)

        # 3. Place a limit BUY 5% below market (won't fill)
        limit_price = round(price * (1 - LIMIT_OFFSET_PCT / 100.0), 4)
        qty = round(MIN_QTY_USDT / limit_price, 6)
        log.info("CS placing test BUY limit: qty=%.6f @ %.4f (5%% below market)", qty, limit_price)

        order = cs.place_order(TEST_SYMBOL, "buy", "limit", qty, price=limit_price)
        order_id = order.get("order_id") or order.get("id")
        result["order_id"] = order_id
        log.info("CS order placed: order_id=%s", order_id)

        time.sleep(2)

        # 4. Cancel immediately
        if order_id:
            cs.cancel_order(order_id)
            result["cancelled"] = True
            log.info("CS order cancelled: %s", order_id)

        print(f"\n  ✅ CoinSwitch: PASS")
        print(f"     Price   : {price}")
        print(f"     Balance : {balance:.4f} USDT")
        print(f"     Order   : {order_id} → CANCELLED")

    except Exception as e:
        result["error"] = str(e)
        log.error("CoinSwitch test FAILED: %s", e)
        print(f"\n  ❌ CoinSwitch: FAIL — {e}")

    return result


def test_delta() -> dict:
    sep("DELTA EXCHANGE INDIA TEST")
    result = {"exchange": "Delta India", "price": None, "balance": None,
              "order_id": None, "cancelled": False, "error": None}
    try:
        dx = DeltaClient(DX_KEY, DX_SECRET, rate_limit_delay=0.5)

        # 1. Price
        price = dx.get_ticker_price(TEST_SYMBOL)
        result["price"] = price
        log.info("Delta price %s = %.4f", TEST_SYMBOL, price)

        # 2. Balance
        balance = dx.get_usdt_balance()
        result["balance"] = balance
        log.info("Delta USDT balance = %.4f", balance)

        # 3. Product ID lookup
        product_id = dx.symbol_to_product_id(TEST_SYMBOL)
        log.info("Delta product_id for %s = %s", TEST_SYMBOL, product_id)

        if not product_id:
            raise ValueError(f"Could not find product_id for {TEST_SYMBOL} on Delta India")

        # 4. Place limit BUY 5% below market
        limit_price = round(price * (1 - LIMIT_OFFSET_PCT / 100.0), 2)
        qty = round(MIN_QTY_USDT / limit_price, 6)
        log.info("Delta placing test BUY limit: qty=%.6f @ %.2f (5%% below market)", qty, limit_price)

        order = dx.place_order(TEST_SYMBOL, "buy", "limit", qty, price=limit_price)
        order_id = order.get("id") or order.get("order_id")
        result["order_id"] = order_id
        log.info("Delta order placed: order_id=%s", order_id)

        time.sleep(2)

        # 5. Cancel immediately
        if order_id:
            dx.cancel_order(order_id, product_id)
            result["cancelled"] = True
            log.info("Delta order cancelled: %s", order_id)

        print(f"\n  ✅ Delta India: PASS")
        print(f"     Price      : {price}")
        print(f"     Balance    : {balance:.4f} USDT")
        print(f"     Product ID : {product_id}")
        print(f"     Order      : {order_id} → CANCELLED")

    except Exception as e:
        result["error"] = str(e)
        log.error("Delta test FAILED: %s", e)
        print(f"\n  ❌ Delta India: FAIL — {e}")

    return result


def main():
    print("\n" + "="*55)
    print("  DUAL EXCHANGE CONNECTIVITY TEST")
    print("  Symbol: BTC/USDT | Orders placed 5% below market")
    print("  Orders are cancelled immediately — no actual trade")
    print("="*55)

    if not CS_KEY or not CS_SECRET:
        print("❌ CoinSwitch credentials missing in .env")
        sys.exit(1)
    if not DX_KEY or not DX_SECRET:
        print("❌ Delta credentials missing in .env")
        sys.exit(1)

    cs_result    = test_coinswitch()
    delta_result = test_delta()

    sep("SUMMARY")
    for r in [cs_result, delta_result]:
        status = "✅ PASS" if not r["error"] else "❌ FAIL"
        print(f"  {r['exchange']:20} {status}")
        if r["error"]:
            print(f"    Error: {r['error']}")

    both_ok = not cs_result["error"] and not delta_result["error"]
    print(f"\n{'✅ BOTH EXCHANGES WORKING — bot is ready for live trading' if both_ok else '⚠️  CHECK ERRORS ABOVE'}\n")
    sys.exit(0 if both_ok else 1)


if __name__ == "__main__":
    main()
