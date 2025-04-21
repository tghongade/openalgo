# funds_manager.py

import json
import os
from fyers_connect import client
from logger import log_event
from config import TEST_MODE, TEST_UNLIMITED_FUNDS, MIN_FUNDS_REQUIRED

FUNDS_FILE = "funds.json"

def load_funds():
    """
    Load available funds from local file
    """
    print("\n=== FUNDS LOADING STAGE ===")
    if TEST_MODE and TEST_UNLIMITED_FUNDS:
        print("TEST MODE: Using unlimited funds")
        return float('inf')
        
    if os.path.exists(FUNDS_FILE):
        print("Reading funds from local file...")
        with open(FUNDS_FILE, 'r') as f:
            data = json.load(f)
            funds = data.get("available_funds", 0)
            print(f"Loaded funds: ₹{funds}")
            return funds
    print("No funds file found, returning 0")
    return 0

def save_funds(amount):
    """
    Save available funds to local file
    """
    print("\n=== FUNDS SAVING STAGE ===")
    if TEST_MODE and TEST_UNLIMITED_FUNDS:
        print("TEST MODE: Skipping funds save (unlimited funds)")
        return
        
    print(f"Saving funds: ₹{amount}")
    with open(FUNDS_FILE, 'w') as f:
        json.dump({"available_funds": amount}, f, indent=4)
    log_event(f"Funds updated: ₹{amount}")

def fetch_fyers_funds():
    """
    Fetch available funds from Fyers
    """
    print("\n=== FETCHING FYERS FUNDS STAGE ===")
    if TEST_MODE and TEST_UNLIMITED_FUNDS:
        print("TEST MODE: Using unlimited funds")
        return float('inf')
        
    try:
        print("Requesting funds from Fyers...")
        if TEST_MODE:
            # In test mode, use local funds file instead of real API
            funds = load_funds()
            print(f"TEST MODE: Using local funds: ₹{funds}")
            return funds
            
        profile = client.funds()
        equity_cash = profile['fund_limit'][0]['equityAmount']
        print(f"Fyers funds received: ₹{equity_cash}")
        log_event(f"Available funds on Fyers: ₹{equity_cash}")
        return equity_cash
    except Exception as e:
        print(f"Error fetching Fyers funds: {e}")
        log_event(f"Failed to fetch Fyers funds: {e}", level="error")
        return None

def update_funds_from_fyers():
    """
    Update local funds with Fyers balance
    """
    print("\n=== FUNDS UPDATE FROM FYERS STAGE ===")
    if TEST_MODE and TEST_UNLIMITED_FUNDS:
        print("TEST MODE: Skipping Fyers funds update (unlimited funds)")
        return True
        
    fyers_funds = fetch_fyers_funds()
    if fyers_funds is not None:
        print(f"Updating local funds with {'test' if TEST_MODE else 'Fyers'} balance: ₹{fyers_funds}")
        save_funds(fyers_funds)
        return True
    print("Failed to update funds")
    return False

def check_funds_available(required_amount):
    """
    Check if required funds are available
    """
    if TEST_MODE and TEST_UNLIMITED_FUNDS:
        print("TEST MODE: Bypassing fund check")
        return True
        
    available_funds = get_funds_available()
    if available_funds >= required_amount:
        print(f"Sufficient funds available: ₹{available_funds} >= ₹{required_amount}")
        return True
        
    print(f"Insufficient funds: ₹{available_funds} < ₹{required_amount}")
    log_event(f"Insufficient funds for trade. Required: ₹{required_amount}, Available: ₹{available_funds}")
    return False

def get_funds_available():
    """
    Get available funds
    """
    if TEST_MODE and TEST_UNLIMITED_FUNDS:
        print("TEST MODE: Returning unlimited funds")
        return float('inf')
        
    try:
        funds = load_funds()
        return funds.get('available_funds', 0)
    except Exception as e:
        print(f"Error getting available funds: {e}")
        log_event(f"Error getting available funds: {e}", level="error")
        return 0

def save_pending_orders(orders):
    """
    Save pending orders to a JSON file
    """
    PENDING_ORDERS_FILE = "pending_orders.json"
    try:
        with open(PENDING_ORDERS_FILE, 'w') as f:
            json.dump({"pending_orders": orders}, f, indent=4)
        print(f"Saved {len(orders)} pending orders")
        return True
    except Exception as e:
        print(f"Error saving pending orders: {e}")
        log_event(f"Error saving pending orders: {e}", level="error")
        return False

def load_pending_orders():
    """
    Load pending orders from JSON file
    """
    PENDING_ORDERS_FILE = "pending_orders.json"
    try:
        if os.path.exists(PENDING_ORDERS_FILE):
            with open(PENDING_ORDERS_FILE, 'r') as f:
                data = json.load(f)
                orders = data.get("pending_orders", [])
            print(f"Loaded {len(orders)} pending orders")
            return orders
        return []
    except Exception as e:
        print(f"Error loading pending orders: {e}")
        log_event(f"Error loading pending orders: {e}", level="error")
        return []

def process_pending_orders():
    """
    Try to process pending orders if funds are now available
    """
    print("\n=== PROCESSING PENDING ORDERS ===")
    pending_orders = load_pending_orders()
    if not pending_orders:
        print("No pending orders to process")
        return
        
    successful_orders = []
    for order in pending_orders:
        symbol = order['symbol']
        required_amount = order['required_amount']
        
        print(f"\nChecking funds for pending order: {symbol} (Required: ₹{required_amount})")
        if check_funds_available(required_amount):
            print(f"Sufficient funds now available for {symbol}")
            # Place the order
            from order_manager import place_market_order
            result = place_market_order(
                symbol=symbol,
                qty=1,
                side="BUY",
                exchange=order['exchange']
            )
            
            if result:
                print(f"Successfully placed order for {symbol}")
                successful_orders.append(order)
                log_event(f"Processed pending order for {symbol}")
            else:
                print(f"Failed to place order for {symbol}")
        else:
            print(f"Still insufficient funds for {symbol}")
            
    # Remove successful orders from pending list
    if successful_orders:
        pending_orders = [order for order in pending_orders if order not in successful_orders]
        save_pending_orders(pending_orders)
        print(f"Processed {len(successful_orders)} pending orders")

def main():
    print("Welcome to Funds Manager")
    print("-" * 40)

    while True:
        current = load_funds()
        print(f"\nLocal available funds: ₹{current}")
        print("Options:")
        print("1. Update local funds manually")
        print("2. Reset local funds to 0")
        print("3. Fetch funds from Fyers and update")
        print("4. Exit")

        choice = input("Enter your choice (1/2/3/4): ").strip()

        if choice == "1":
            try:
                new_amount = float(input("Enter new funds amount: ₹").strip())
                if new_amount < 0:
                    raise ValueError
                save_funds(new_amount)
            except ValueError:
                print("ERROR: Please enter a valid positive number.")
        elif choice == "2":
            save_funds(0)
        elif choice == "3":
            if update_funds_from_fyers():
                print("SUCCESS: Funds updated from Fyers.")
        elif choice == "4":
            print("Exiting Funds Manager.")
            break
        else:
            print("ERROR: Invalid choice. Please select 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()
