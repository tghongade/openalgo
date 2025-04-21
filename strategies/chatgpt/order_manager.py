# order_manager.py

import json
import os
from fyers_connect import client
from logger import log_event
from config import TEST_MODE, TEST_UNLIMITED_FUNDS

def place_market_order(symbol, qty, side="BUY", exchange="NSE"):
    """
    Place a CNC market order through Fyers.
    side: "BUY" or "SELL"
    """
    print(f"\n=== ORDER PLACEMENT STAGE FOR {symbol} ===")
    if TEST_MODE:
        print("Running in TEST MODE - Simulating order")
        log_event(f"[TEST MODE] Simulated {side} order for {symbol}, Qty: {qty}")
        return {"status": "simulated", "symbol": symbol, "qty": qty}

    print(f"Preparing {side} market order for {symbol} | Qty: {qty}")
    log_event(f"Placing {side} market order for {symbol} | Qty: {qty}")

    try:
        order_data = {
            "symbol": f"{exchange}:{symbol}-EQ",
            "qty": qty,
            "type": 2,               # 2 = Market Order
            "side": 1 if side == "BUY" else -1,
            "productType": "CNC",    # Updated from INTRADAY to CNC
            "limitPrice": 0,
            "stopPrice": 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
            "takeProfit": 0,
            "stopLoss": 0
        }

        print("Sending order to Fyers...")
        response = client.place_order(data=order_data)
        print(f"Order response received: {response}")
        log_event(f"Order response for {symbol}: {response}")
        return response

    except Exception as e:
        print(f"Error placing order: {str(e)}")
        log_event(f"Error placing order for {symbol}: {str(e)}", level="error")
        return None

def retry_pending_orders():
    """
    Retry any pending orders that failed previously
    """
    print("\n=== PENDING ORDERS RETRY STAGE ===")
    PENDING_ORDERS_FILE = "pending_orders.json"
    
    def load_pending_orders():
        print("Loading pending orders from file...")
        if os.path.exists(PENDING_ORDERS_FILE):
            with open(PENDING_ORDERS_FILE, 'r') as file:
                return json.load(file)
        print("No pending orders file found")
        return []

    def save_pending_orders(pending_orders):
        print("Saving updated pending orders...")
        with open(PENDING_ORDERS_FILE, 'w') as file:
            json.dump(pending_orders, file, indent=4)

    log_event("Checking for pending orders...")
    pending_orders = load_pending_orders()
    if not pending_orders:
        print("No pending orders to process")
        log_event("No pending orders found.")
        return

    print(f"Found {len(pending_orders)} pending orders to process")
    successful_orders = []
    for order in pending_orders:
        symbol = order['symbol']
        exchange = order['exchange']
        quantity = order['quantity']
        price = order['price']
        required_funds = price * quantity

        print(f"\nProcessing pending order for {symbol}")
        log_event(f"Retrying pending order: {symbol} | Qty: {quantity} | Req. ₹{required_funds:.2f}")

        if TEST_MODE:
            print("TEST MODE: Simulating order placement")
            response = {"status": "simulated", "symbol": symbol, "qty": quantity}
        else:
            response = place_market_order(
                symbol=symbol,
                qty=quantity,
                side="BUY",
                exchange=exchange
            )

        if response and (response.get("s") == "ok" or (TEST_MODE and response.get("status") == "simulated")):
            print(f"Successfully placed order for {symbol}")
            log_event(f"Successfully placed pending order for {symbol}")
            successful_orders.append(order)
        else:
            print(f"Order failed for {symbol}: {response}")
            log_event(f"Order failed for {symbol}: {response}", level="warning")

    # Remove successful orders
    print(f"\nUpdating pending orders list: {len(successful_orders)} orders processed successfully")
    pending_orders = [order for order in pending_orders if order not in successful_orders]
    save_pending_orders(pending_orders)
    log_event("Pending orders updated.") 