import time
from datetime import datetime, timedelta
from fyers_connect import get_client
from strategy import check_signals
from order_manager import place_market_order
from funds_manager import (
    check_funds_available, 
    update_funds_from_fyers, 
    save_pending_orders,
    process_pending_orders
)
from watchlist import load_watchlist
from logger import log_event
from config import TEST_MODE, TEST_BYPASS_TIME, TEST_UNLIMITED_FUNDS
from utils import get_current_ist_time
import pandas as pd
import logging
import traceback

# Initialize logger
logger = logging.getLogger('strategy')
logger.setLevel(logging.DEBUG)  # Changed to DEBUG for more verbose logging
if not logger.handlers:
    # File handler for detailed logging
    fh = logging.FileHandler('strategy_debug.log')
    fh.setLevel(logging.DEBUG)
    fh_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)
    
    # Console handler for important messages
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

# Set broker API key directly for this script
BROKER_API_KEY = "9c0e0c5af661612e8d52ce35064fffea44683c7cff941e5bc11fa533259c25e3"
BROKER_API_SECRET = "BATJRCG452"

def is_friday_3pm_or_later(now):
    """Check if current time is Friday 3 PM or later"""
    if TEST_MODE and TEST_BYPASS_TIME:
        print("\n=== TEST MODE: Bypassing time check for Friday 3 PM ===")
        return True
    return now.weekday() == 4 and now.hour >= 15

def is_monday_10am_or_later(now):
    """Check if current time is Monday 10 AM or later"""
    if TEST_MODE and TEST_BYPASS_TIME:
        print("\n=== TEST MODE: Bypassing time check for Monday 10 AM ===")
        return True
    return now.weekday() == 0 and now.hour >= 10

def run_test_mode(client):
    """
    Run strategy in test mode - check signals without placing trades
    """
    try:
        logger.info("\n=== Starting TEST MODE ===")
        
        # Load stocks from watchlist
        logger.debug("Attempting to load watchlist...")
        watchlist = load_watchlist()
        if not watchlist:
            logger.error("No stocks found in watchlist")
            return False
            
        logger.info(f"Loaded {len(watchlist)} stocks from watchlist.")
        
        # Test each symbol
        for stock in watchlist:
            symbol = stock['symbol']
            exchange = stock['exchange']
            logger.info(f"\n=== Testing {symbol} ===")
            
            try:
                # Check entry signals
                logger.debug(f"Checking entry conditions for {symbol}...")
                entry_signal = check_signals(symbol, exchange, client, "entry")
                if entry_signal:
                    logger.info(f"Entry signal detected for {symbol}")
                    log_event(f"Test mode: Entry signal detected for {symbol}")
                else:
                    logger.debug(f"No entry signal for {symbol}")
                    
                # Check exit signals
                logger.debug(f"Checking exit conditions for {symbol}...")
                exit_signal = check_signals(symbol, exchange, client, "exit")
                if exit_signal:
                    logger.info(f"Exit signal detected for {symbol}")
                    log_event(f"Test mode: Exit signal detected for {symbol}")
                else:
                    logger.debug(f"No exit signal for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                logger.debug(f"Stack trace for {symbol}: {traceback.format_exc()}")
                continue
                
            logger.debug(f"Completed testing {symbol}")
            
        logger.info("Test mode completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Critical error in test mode: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")
        return False

def check_entry_signals(client):
    """
    Check for entry signals and place orders if conditions are met
    """
    logger.info("Starting entry signal check...")
    watchlist = load_watchlist()
    pending_orders = []
    
    for stock in watchlist:
        symbol = stock['symbol']
        exchange = stock['exchange']
        logger.debug(f"Processing entry signals for {symbol}...")
        
        try:
            if check_signals(symbol, exchange, client, "entry"):
                logger.info(f"Entry signal confirmed for {symbol}")
                
                # Get current market price
                try:
                    logger.debug(f"Fetching market price for {symbol}...")
                    market_data = client.quotes(f"{exchange}:{symbol}-EQ")
                    current_price = market_data['ltp']
                    required_amount = current_price * 1  # For 1 quantity
                    logger.debug(f"Current price for {symbol}: ₹{current_price}")
                except Exception as e:
                    logger.error(f"Error getting market price for {symbol}: {e}")
                    log_event(f"Error getting market price for {symbol}: {e}")
                    continue
                    
                # Check if we have enough funds
                logger.debug(f"Checking funds availability for {symbol} (Required: ₹{required_amount})")
                if check_funds_available(required_amount):
                    logger.info(f"Sufficient funds (₹{required_amount}). Placing {'test' if TEST_MODE else 'live'} order for {symbol}")
                    place_market_order(symbol, 1, "BUY", exchange)
                else:
                    logger.warning(f"Insufficient funds for {symbol} (Required: ₹{required_amount})")
                    log_event(f"Insufficient funds for {symbol} (Required: ₹{required_amount})")
                    
                    # Add to pending orders
                    pending_orders.append({
                        'symbol': symbol,
                        'exchange': exchange,
                        'required_amount': required_amount,
                        'signal_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'status': 'pending_funds'
                    })
                    
                    # Save pending orders to file
                    save_pending_orders(pending_orders)
                    
                    # Try to update funds
                    logger.debug("Attempting to update funds...")
                    if update_funds_from_fyers():
                        logger.info("Funds updated successfully")
                        # Check again with updated funds
                        if check_funds_available(required_amount):
                            logger.info(f"Sufficient funds after update. Placing {'test' if TEST_MODE else 'live'} order for {symbol}")
                            place_market_order(symbol, 1, "BUY", exchange)
                            # Remove from pending orders if successful
                            pending_orders = [order for order in pending_orders if order['symbol'] != symbol]
                            save_pending_orders(pending_orders)
                        
        except Exception as e:
            logger.error(f"Error processing entry signals for {symbol}: {str(e)}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
            continue
    
    # Report pending orders
    if pending_orders:
        logger.warning("\n=== PENDING ORDERS DUE TO INSUFFICIENT FUNDS ===")
        for order in pending_orders:
            logger.warning(f"Symbol: {order['symbol']}, Required: ₹{order['required_amount']}, Time: {order['signal_time']}")
        log_event(f"Total pending orders due to insufficient funds: {len(pending_orders)}")

def check_exit_signals(client):
    """
    Check for exit signals and place orders if conditions are met
    Only for stocks present in the user's portfolio (positions).
    """
    # Fetch current positions from Fyers
    positions = get_portfolio_positions(client)
    if positions is None or positions.empty:
        print("No positions found in portfolio. Skipping exit checks.")
        return

    # Ensure positions DataFrame has a symbol column
    if 'symbol' not in positions.columns:
        print("Positions data does not have a 'symbol' column. Skipping exit checks.")
        return

    # Use only symbols present in positions
    for idx, position in positions.iterrows():
        symbol = position['symbol']
        # If you have exchange info in positions, use it, else default to 'NSE'
        exchange = position['exchange'] if 'exchange' in position else 'NSE'
        print(f"\nChecking exit signals for {symbol} (portfolio holding)...")
        if check_signals(symbol, exchange, client, "exit"):
            print(f"Exit signal confirmed for {symbol}")
            print(f"Placing exit order for {symbol}")
            place_market_order(symbol, 1, "SELL", exchange)

def get_portfolio_positions(client):
    """
    Fetch current positions from Fyers account
    """
    try:
        positions = client.positionbook()
        if isinstance(positions, pd.DataFrame):
            return positions
        print("No positions found or invalid response")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error fetching positions: {e}")
        return pd.DataFrame()

def run_strategy():
    """Main strategy execution function"""
    try:
        now = get_current_ist_time()
        logger.info(f"Strategy started at {now}")
        
        # Initialize Fyers client
        logger.debug("Initializing Fyers client...")
        client = get_client()
        if not client:
            logger.error("Failed to initialize Fyers client")
            return
            
        logger.info("Fyers client initialized successfully")
        
        if TEST_MODE:
            logger.info("Running in TEST MODE")
            run_test_mode(client)
            return
            
        # First check exit conditions for existing positions
        logger.info("\n=== CHECKING EXIT CONDITIONS FOR PORTFOLIO POSITIONS ===")
        positions = get_portfolio_positions(client)
        
        if not positions.empty:
            logger.info(f"Found {len(positions)} positions in portfolio")
            for idx, position in positions.iterrows():
                logger.debug(f"Processing position: {position}")
                # Process position logic here
        else:
            logger.info("No existing positions found")
            
        # Then check for new entry opportunities
        logger.info("\n=== CHECKING ENTRY CONDITIONS FOR WATCHLIST STOCKS ===")
        check_entry_signals(client)
        
    except Exception as e:
        logger.error(f"Critical error in strategy execution: {str(e)}")
        logger.debug(f"Stack trace: {traceback.format_exc()}")

def main():
    try:
        print("\n=== STRATEGY INITIALIZATION ===")
        log_event("=== Weekly Strategy Started ===")
        
        print(f"\n=== MODE: {'TEST' if TEST_MODE else 'LIVE'} ===")
        if TEST_MODE:
            print("Running in TEST MODE:")
            print("- Time restrictions bypassed")
            print("- Fund restrictions bypassed")
            print("- No actual trades will be placed")
            print("- All conditions will be logged")
        
        print("\n=== CONNECTION STAGE ===")
        try:
            client = get_client()
            if not client:
                print("ERROR: Failed to get client object")
                log_event("ERROR: Failed to connect to Fyers.")
                return False
                
            # Test connection by making a simple API call
            print("\nTesting API connection...")
            try:
                test_symbol = "SBIN"
                print(f"Attempting to fetch history for {test_symbol}...")
                history = client.history(
                    symbol=test_symbol,
                    exchange="NSE",
                    start_date=(datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
                    end_date=datetime.now().strftime('%Y-%m-%d'),
                    interval='D'
                )
                if history is not None:
                    print("API connection test successful")
                    print(f"Sample data received: {history[:2] if isinstance(history, list) else history.head(2) if isinstance(history, pd.DataFrame) else history}")
                else:
                    print("ERROR: API connection test failed - no data received")
                    return False
            except Exception as e:
                print(f"ERROR: API connection test failed: {str(e)}")
                print(f"Stack trace: {traceback.format_exc()}")
                return False

        except Exception as e:
            print(f"ERROR: Connection error: {str(e)}")
            print(f"Stack trace: {traceback.format_exc()}")
            return False

        log_event(f"SUCCESS: Fyers connected successfully | Mode: {'TEST' if TEST_MODE else 'LIVE'}")

        if TEST_MODE:
            return run_test_mode(client)
            
        # Live mode code here...
        return True
        
    except Exception as e:
        print(f"\nError in main: {str(e)}")
        print("Stack trace:", traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    print(f"\nStrategy {'completed successfully' if success else 'failed'}")
