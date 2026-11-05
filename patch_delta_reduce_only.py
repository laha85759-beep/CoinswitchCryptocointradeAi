path = 'c:/Users/karth/Downloads/CoinswitchCryptocointradeAi-main/CoinswitchCryptocointradeAi-main/delta_client.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_sig = '''    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        stop_loss_price: float | None = None,
        take_profit_price: float | None = None,
        leverage: int = 20,'''

new_sig = '''    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        stop_loss_price: float | None = None,
        take_profit_price: float | None = None,
        leverage: int = 20,
        reduce_only: bool = False,'''

content = content.replace(old_sig, new_sig, 1)

old_body = '''        body: dict = {
            "product_id": product_id,
            "size": size,
            "side": side.lower(),
            "order_type": "limit_order" if order_type.lower() == "limit" else "market_order",
        }'''

new_body = '''        body: dict = {
            "product_id": product_id,
            "size": size,
            "side": side.lower(),
            "order_type": "limit_order" if order_type.lower() == "limit" else "market_order",
        }
        if reduce_only:
            body["reduce_only"] = True'''

content = content.replace(old_body, new_body, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated delta_client.py with reduce_only successfully!")
