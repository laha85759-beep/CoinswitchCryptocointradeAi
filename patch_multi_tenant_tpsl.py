path = 'c:/Users/karth/Downloads/CoinswitchCryptocointradeAi-main/CoinswitchCryptocointradeAi-main/multi_tenant_engine.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Update delta auto close to use reduce_only=True
old_delta_close = '''                        close_side = "sell" if is_long else "buy"
                        dc.place_order(symbol=symbol, side=close_side, order_type="market", quantity=qty)'''

new_delta_close = '''                        close_side = "sell" if is_long else "buy"
                        dc.place_order(symbol=symbol, side=close_side, order_type="market", quantity=qty, reduce_only=True)'''

content = content.replace(old_delta_close, new_delta_close, 1)

# Also add Coinbase handling
old_mt5_branch = '''            elif exchange == "mt5":'''

coinbase_branch = '''            elif exchange == "coinbase":
                try:
                    import os
                    from coinbase_client import CoinbaseClient
                    cb_key = os.environ.get("COINBASE_API_KEY", "")
                    cb_sec = os.environ.get("COINBASE_PRIVATE_KEY", "")
                    if cb_key and cb_sec:
                        cb = CoinbaseClient(cb_key, cb_sec)
                        cb_prod = f"{clean_base}-USD"
                        cb.create_market_order(product_id=cb_prod, side="SELL" if is_long else "BUY", base_size=str(qty))
                except Exception as ex_err:
                    log.error("Coinbase auto-close failed for User #%s: %s", user_id, ex_err)

            elif exchange == "mt5":'''

if old_mt5_branch in content:
    content = content.replace(old_mt5_branch, coinbase_branch, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated multi_tenant_engine.py with reduce_only=True and Coinbase TP/SL handler!")
