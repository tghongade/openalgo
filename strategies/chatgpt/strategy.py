# strategy.py

import pandas as pd
import ta  # Technical Analysis library
from datetime import datetime, timedelta
from logger import log_event
import time
import traceback

def check_entry_conditions(data, current_price):
    """
    Check entry conditions using weekly data:
    - RSI > 60 (using weekly candles)
    """
    try:
        print("\nCalculating RSI...")
        print(f"Data shape: {data.shape}")
        print(f"Data columns: {data.columns}")
        print(f"First few rows:\n{data.head()}")
        
        # Ensure close prices are numeric
        data['close'] = pd.to_numeric(data['close'], errors='coerce')
        
        # Drop any NaN values
        data = data.dropna(subset=['close'])
        
        if len(data) < 14:
            print(f"Insufficient data for RSI calculation. Need at least 14 periods, got {len(data)}")
            return False
        
        # Calculate weekly RSI with 14 periods
        rsi = ta.momentum.RSIIndicator(close=data['close'], window=14).rsi()
        
        if rsi is None or rsi.empty:
            print("RSI calculation returned None or empty")
            return False
            
        current_rsi = rsi.iloc[-1]
        
        print(f"\nRSI calculation results:")
        print(f"RSI length: {len(rsi)}")
        print(f"Last 5 RSI values:\n{rsi.tail()}")
        print(f"Current RSI: {current_rsi:.2f}")
        
        # Entry condition: RSI > 60
        if current_rsi > 60:
            print("Entry condition met: Weekly RSI > 60")
            return True
            
        print("Entry conditions not met")
        return False
        
    except Exception as e:
        print(f"Error checking entry conditions: {str(e)}")
        print("Stack trace:", traceback.format_exc())
        return False

def check_exit_conditions(data, current_price):
    """
    Check exit conditions using weekly data:
    - Price below ATR (21 period, 1.8 multiplier)
    """
    try:
        # Calculate weekly ATR with 21 periods
        atr = ta.volatility.AverageTrueRange(
            high=data['high'],
            low=data['low'],
            close=data['close'],
            window=21
        ).average_true_range()
        
        current_atr = atr.iloc[-1]
        atr_threshold = current_price - (current_atr * 1.8)  # Price - (ATR * 1.8)
        
        print(f"Weekly ATR: {current_atr:.2f}")
        print(f"ATR Threshold: {atr_threshold:.2f}")
        print(f"Current Price: {current_price:.2f}")
        
        # Exit condition: Price below ATR threshold
        if current_price < atr_threshold:
            print("Exit condition met: Price below ATR threshold")
            return True
            
        print("Exit conditions not met")
        return False
        
    except Exception as e:
        print(f"Error checking exit conditions: {str(e)}")
        return False

def aggregate_to_weekly(daily_data):
    """
    Convert daily data to weekly timeframe
    """
    try:
        if not isinstance(daily_data.index, pd.DatetimeIndex):
            print("Error: Data index is not datetime")
            return None
            
        weekly_data = pd.DataFrame()
        weekly_data['open'] = daily_data['open'].resample('W').first()
        weekly_data['high'] = daily_data['high'].resample('W').max()
        weekly_data['low'] = daily_data['low'].resample('W').min()
        weekly_data['close'] = daily_data['close'].resample('W').last()
        weekly_data['volume'] = daily_data['volume'].resample('W').sum()
        
        # Forward fill any missing data
        weekly_data.ffill(inplace=True)
        
        return weekly_data
        
    except Exception as e:
        print(f"Error aggregating to weekly: {str(e)}")
        return None

def fetch_historical_data(symbol, exchange, client, lookback_days=200):
    """
    Fetch historical data and convert to weekly timeframe
    """
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        print(f"Fetching data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Fetch daily data
        response = client.history(
            symbol=symbol,
            exchange=exchange,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            interval='D'  # Use 'D' for daily data
        )
        
        print("\nAPI Response Details:")
        print(f"Type: {type(response)}")
        if response is None:
            print(f"No data received for {symbol}")
            return None
            
        # Convert response to DataFrame
        try:
            # If response is already a DataFrame
            if isinstance(response, pd.DataFrame):
                print("Response is already a DataFrame")
                data = response.copy()
            # If response is a dictionary with candles
            elif isinstance(response, dict) and 'candles' in response:
                print("Response is a dictionary with candles")
                data = pd.DataFrame(response['candles'], 
                                  columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            # If response is a list of lists
            elif isinstance(response, list):
                print("Response is a list")
                if len(response) > 0:
                    print(f"First row: {response[0]}")
                data = pd.DataFrame(response, 
                                  columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            else:
                print(f"Unexpected data format for {symbol}")
                print(f"Response type: {type(response)}")
                print(f"Response: {response}")
                return None
                
            print("\nDataFrame before processing:")
            print(f"Shape: {data.shape}")
            print(f"Columns: {data.columns}")
            print(f"First few rows:\n{data.head()}")
            
            # Reset index if timestamp is already the index
            if data.index.name == 'timestamp':
                data = data.reset_index()
            
            # Ensure timestamp column exists
            if 'timestamp' not in data.columns:
                print("No timestamp column found")
                return None
            
            # Convert timestamp to datetime
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            
            # Set timestamp as index
            data.set_index('timestamp', inplace=True)
            
            # Ensure numeric columns
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            data[numeric_columns] = data[numeric_columns].apply(pd.to_numeric)
            
            # Sort index
            data = data.sort_index()
            
            # Aggregate to weekly data
            weekly_data = aggregate_to_weekly(data)
            
            if weekly_data is None or len(weekly_data) < 2:
                print(f"Insufficient weekly data points for {symbol}")
                return None
                
            print("\nWeekly data after processing:")
            print(f"Shape: {weekly_data.shape}")
            print(f"First few rows:\n{weekly_data.head()}")
            
            return weekly_data
            
        except Exception as e:
            print(f"Error processing data for {symbol}: {str(e)}")
            print(f"Response type: {type(response)}")
            print(f"Response: {response}")
            return None
            
    except Exception as e:
        print(f"Error fetching data for {symbol}: {str(e)}")
        return None

def check_signals(symbol, exchange, client, signal_type="entry"):
    """
    Check for entry/exit signals for a given symbol using weekly data
    """
    try:
        print(f"\n=== {signal_type.upper()} SIGNAL CHECK STAGE FOR {symbol} ===")
        # Get historical data for last 200 days to ensure enough data for weekly aggregation
        end_date = datetime.now()
        start_date = end_date - timedelta(days=200)
        
        print(f"Fetching data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Use retry logic for fetching data
        weekly_data = fetch_historical_data(symbol, exchange, client)
        
        if weekly_data is None:
            print("Failed to fetch historical data")
            log_event(f"Failed to fetch historical data for {symbol}")
            return False
        
        print(f"Weekly data shape: {weekly_data.shape}")
        
        # Ensure we have enough weekly data points for calculations
        min_required_points = 25  # Need enough weekly candles for indicators
        if len(weekly_data) < min_required_points:
            print(f"Insufficient weekly data points. Need at least {min_required_points}, got {len(weekly_data)}")
            log_event(f"Insufficient data points for {symbol}")
            return False
            
        # Get current price from the last weekly close
        current_price = weekly_data['close'].iloc[-1]
        print(f"Current weekly closing price: {current_price}")
        
        # Check conditions based on signal type
        if signal_type == "entry":
            should_act = check_entry_conditions(weekly_data, current_price)
        else:
            should_act = check_exit_conditions(weekly_data, current_price)
        
        if should_act:
            print(f"{signal_type.capitalize()} signal confirmed")
            log_event(f"{signal_type.capitalize()} signal detected for {symbol}")
        else:
            print(f"No {signal_type} signal detected")
            
        return should_act
        
    except Exception as e:
        print(f"Error in {signal_type} signal check: {str(e)}")
        log_event(f"Error checking {signal_type} signals for {symbol}: {str(e)}")
        return False 