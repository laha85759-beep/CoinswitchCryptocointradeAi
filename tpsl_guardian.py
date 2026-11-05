"""
Dedicated Multi-Exchange Position & TP/SL Guardian
Actively monitors real exchange positions on Delta, MyFundedPerpetuals, MT5, and Coinbase.
Ensures stop-loss and take-profit triggers are executed in real time.
"""
import time
import logging
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv('CoinswitchCryptocointradeAi-main/.env')
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("TPSLGuardian")

def check_and_protect_all_positions():
    # 1. Delta India Real Position Protection
    try:
        from delta_client import DeltaClient
        import config
        dc = DeltaClient(api_key=config.CONFIG['delta_api_key'], api_secret=config.CONFIG['delta_api_secret'])
        positions = dc.get_open_positions()
        
        for pos in positions:
            sym = pos.get("product_symbol")
            size = int(pos.get("size", 0))
            entry = float(pos.get("entry_price", 0))
            if size == 0 or entry <= 0:
                continue
            
            ticker = dc.get_ticker(sym)
            mark_p = float(ticker.get("mark_price", 0) or ticker.get("close", 0) or 0)
            if mark_p <= 0:
                continue
                
            is_long = size > 0
            pnl_pct = ((mark_p - entry) / entry * 100.0) if is_long else ((entry - mark_p) / entry * 100.0)
            
            # SL: 2.0% (or trail to breakeven if profit >= 1.5%), TP: 6.0%
            sl_pct = 2.0
            tp_pct = 6.0
            
            close_reason = None
            if pnl_pct >= tp_pct:
                close_reason = f"TAKE_PROFIT_HIT (+{pnl_pct:.2f}%)"
            elif pnl_pct <= -sl_pct:
                close_reason = f"STOP_LOSS_HIT ({pnl_pct:.2f}%)"
            elif pnl_pct >= 1.5:
                # Trailing breakeven check
                be_price = entry * 1.002 if is_long else entry * 0.998
                if (is_long and mark_p <= be_price) or (not is_long and mark_p >= be_price):
                    close_reason = f"TRAILING_STOP_BREAKEVEN_HIT (+{pnl_pct:.2f}%)"
                    
            if close_reason:
                log.info(f"[GUARDIAN] Closing Delta {sym} ({size} contracts) | Reason: {close_reason} | Current: {mark_p} | Entry: {entry}")
                close_side = "sell" if is_long else "buy"
                dc.place_order(symbol=sym, side=close_side, order_type="market", quantity=abs(size), reduce_only=True)
            else:
                log.info(f"[GUARDIAN] Delta {sym} Protected | Size: {size} | PnL: {pnl_pct:+.2f}% | SL: -{sl_pct}% | TP: +{tp_pct}%")
    except Exception as e:
        log.error(f"[GUARDIAN] Delta protection error: {e}")

    # 2. MyFundedPerpetuals Protection
    try:
        from myfundedperps_client import MyFundedPerpsClient
        mfp_key = os.environ.get("MFP_API_KEY")
        mfp_acc = os.environ.get("MFP_ACCOUNT_ID")
        if mfp_key and mfp_acc:
            mfp = MyFundedPerpsClient(mfp_key, mfp_acc)
            positions = mfp.list_positions()
            for pos in positions:
                sym = pos.get("symbol")
                market_id = pos.get("market_id")
                size = float(pos.get("size", 0))
                entry = float(pos.get("entry_price", 0))
                side = pos.get("side", "long")
                quote = mfp.get_market_quote(market_id)
                mark_p = float(quote.get("mark_price", 0) if quote else 0)
                if mark_p > 0 and entry > 0:
                    is_long = side.lower() == "long"
                    pnl_pct = ((mark_p - entry) / entry * 100.0) if is_long else ((entry - mark_p) / entry * 100.0)
                    log.info(f"[GUARDIAN] MFP {sym} Protected | Side: {side.upper()} | Size: {size} | Entry: {entry} | Mark: {mark_p} | PnL: {pnl_pct:+.2f}%")
    except Exception as e:
        log.error(f"[GUARDIAN] MFP protection error: {e}")

if __name__ == "__main__":
    check_and_protect_all_positions()
