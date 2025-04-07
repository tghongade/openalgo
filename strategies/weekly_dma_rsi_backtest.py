import pandas as pd
import numpy as np
from openalgo import api
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backtest_results.log'),
        logging.StreamHandler()
    ]
)

class WeeklyDMARSIBacktest:
    def __init__(self, api_key, symbol, exchange="NSE", initial_capital=100000):
        self.api_key = api_key
        self.symbol = symbol
        self.exchange = exchange
        self.initial_capital = initial_capital
        self.client = api(api_key=api_key, host='http://127.0.0.1:5000')
        
    def get_weekly_data(self, start_date, end_date):
        """Fetch daily data and resample to weekly timeframe"""
        logging.info(f"Fetching data for {self.symbol} from {start_date} to {end_date}")
        
        # Fetch daily data
        response = self.client.history(
            symbol=self.symbol,
            exchange=self.exchange,
            interval="1d",
            start_date=start_date,
            end_date=end_date
        )
        
        # Debug: Print response structure
        logging.info(f"API Response type: {type(response)}")
        if isinstance(response, dict):
            logging.info(f"Response keys: {response.keys()}")
            if 'data' in response:
                logging.info(f"Data type: {type(response['data'])}")
                if isinstance(response['data'], list):
                    logging.info(f"Number of data points: {len(response['data'])}")
                    if len(response['data']) > 0:
                        logging.info(f"Sample data point: {response['data'][0]}")
        
        # Convert response to DataFrame
        if isinstance(response, dict):
            if 'data' in response and isinstance(response['data'], list):
                df = pd.DataFrame(response['data'])
            elif 'candles' in response and isinstance(response['candles'], list):
                df = pd.DataFrame(response['candles'])
            else:
                raise ValueError(f"Unexpected response format: {response}")
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")
            
        # Ensure we have the required columns
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            logging.error(f"Available columns: {df.columns}")
            raise ValueError(f"Missing required columns. Available columns: {df.columns}")
            
        # Convert timestamp to datetime if it's not already
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        
        # Resample to weekly timeframe
        df_weekly = df.resample('W').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        # Calculate 20-day moving average (4 weeks)
        df_weekly['sma_20'] = df_weekly['close'].rolling(window=4).mean()
        
        # Calculate RSI
        delta = df_weekly['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df_weekly['rsi'] = 100 - (100 / (1 + rs))
        
        return df_weekly
    
    def run_backtest(self, start_date, end_date):
        """Run the backtest"""
        logging.info("Starting backtest...")
        
        # Get weekly data
        df = self.get_weekly_data(start_date, end_date)
        
        # Initialize variables
        position = 0
        capital = self.initial_capital
        trades = []
        
        # Iterate through the data
        for i in range(4, len(df)):  # Start from index 4 to have enough data for SMA
            current_price = df['close'].iloc[i]
            sma_20 = df['sma_20'].iloc[i]
            rsi = df['rsi'].iloc[i]
            
            # Trading logic
            if position == 0:  # No position
                if current_price > sma_20 and rsi < 70:  # Buy signal
                    position = 1
                    entry_price = current_price
                    shares = capital // entry_price
                    capital -= shares * entry_price
                    trades.append({
                        'date': df.index[i],
                        'type': 'BUY',
                        'price': entry_price,
                        'shares': shares,
                        'capital': capital
                    })
                    logging.info(f"BUY: {shares} shares at {entry_price}")
            
            elif position == 1:  # Long position
                if current_price < sma_20 or rsi > 80:  # Sell signal
                    position = 0
                    exit_price = current_price
                    capital += shares * exit_price
                    trades.append({
                        'date': df.index[i],
                        'type': 'SELL',
                        'price': exit_price,
                        'shares': shares,
                        'capital': capital
                    })
                    logging.info(f"SELL: {shares} shares at {exit_price}")
        
        # Calculate performance metrics
        trades_df = pd.DataFrame(trades)
        if len(trades_df) > 0:
            total_trades = len(trades_df[trades_df['type'] == 'BUY'])
            winning_trades = len(trades_df[trades_df['type'] == 'SELL'][trades_df['price'] > trades_df['price'].shift(1)])
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            final_capital = capital + (shares * df['close'].iloc[-1]) if position == 1 else capital
            returns = ((final_capital - self.initial_capital) / self.initial_capital) * 100
            
            logging.info(f"\nBacktest Results:")
            logging.info(f"Initial Capital: {self.initial_capital}")
            logging.info(f"Final Capital: {final_capital:.2f}")
            logging.info(f"Total Returns: {returns:.2f}%")
            logging.info(f"Total Trades: {total_trades}")
            logging.info(f"Win Rate: {win_rate:.2f}%")
            
            return trades_df, returns, win_rate
        else:
            logging.info("No trades executed during the backtest period")
            return pd.DataFrame(), 0, 0

if __name__ == "__main__":
    # Load API key from environment variables
    api_key = os.getenv('OPENALGO_API_KEY')
    if not api_key:
        raise ValueError("OPENALGO_API_KEY not found in .env file")
        
    symbol = "JINDRILL"
    start_date = "2023-01-01"
    end_date = "2024-03-16"
    
    backtest = WeeklyDMARSIBacktest(api_key, symbol)
    trades_df, returns, win_rate = backtest.run_backtest(start_date, end_date)
    
    # Save trades to CSV file
    if not trades_df.empty:
        trades_df.to_csv('backtest_trades.csv', index=True)
        logging.info(f"\nTrades have been saved to 'backtest_trades.csv'") 