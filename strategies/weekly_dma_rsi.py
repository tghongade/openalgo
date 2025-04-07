from openalgo import api
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WeeklyDMARSIStrategy:
    def __init__(self, api_key, watchlist, risk_amount=2000, min_stoploss=50, trail_profit_threshold=2000):
        """
        Initialize the strategy
        api_key: OpenAlgo API key
        watchlist: List of stock symbols to monitor
        risk_amount: Amount willing to risk per trade (default 2000)
        min_stoploss: Minimum stoploss value (default 50)
        trail_profit_threshold: Profit threshold to start trailing stoploss (default 2000)
        """
        self.client = api(api_key=api_key)
        self.watchlist = watchlist
        self.risk_amount = risk_amount
        self.min_stoploss = min_stoploss
        self.trail_profit_threshold = trail_profit_threshold
        self.positions = {}
        
    def calculate_rsi(self, data, periods=14):
        """Calculate RSI for the given data"""
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def get_weekly_data(self, symbol):
        """Fetch and process weekly historical data"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)  # 1 year of data for reliable calculations
            
            # Fetch daily data
            df = self.client.history(
                symbol=symbol,
                exchange="NSE",
                interval="1d",
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )
            
            if df.empty:
                logger.warning(f"No data received for {symbol}")
                return None
            
            # Resample to weekly timeframe
            weekly_df = df.resample('W').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })
            
            # Calculate indicators
            weekly_df['20_DMA'] = weekly_df['close'].rolling(window=20).mean()
            weekly_df['RSI'] = self.calculate_rsi(weekly_df)
            
            return weekly_df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None
    
    def calculate_position_size(self, current_price, dma_20):
        """Calculate number of shares based on risk amount"""
        stoploss = max(current_price - dma_20, self.min_stoploss)  # Ensure minimum stoploss
        if stoploss <= 0:
            return 0
            
        shares = int(self.risk_amount / stoploss)
        return shares, stoploss
    
    def check_buy_signal(self, df):
        """Check if buy conditions are met"""
        if len(df) < 20:  # Need at least 20 periods for DMA
            return False
            
        last_close = df['close'].iloc[-1]
        last_dma = df['20_DMA'].iloc[-1]
        last_rsi = df['RSI'].iloc[-1]
        
        return (last_close > last_dma) and (last_rsi > 60)
    
    def update_trailing_stoploss(self, symbol, current_price):
        """Update trailing stoploss based on profit levels"""
        if symbol not in self.positions:
            return
            
        position = self.positions[symbol]
        entry_price = position['entry_price']
        quantity = position['quantity']
        current_stoploss = position['stoploss']
        
        # Calculate current profit
        total_profit = (current_price - entry_price) * quantity
        
        if total_profit >= self.trail_profit_threshold:
            # Calculate how many profit thresholds have been crossed
            profit_levels = int(total_profit / self.trail_profit_threshold)
            
            # Initial trail to entry price when first threshold is hit
            if profit_levels == 1 and current_stoploss < entry_price:
                new_stoploss = entry_price
                logger.info(f"Trailing stoploss to entry price for {symbol}")
            else:
                # Trail by 2000 increments for each profit threshold crossed
                min_trail = entry_price + (profit_levels - 1) * self.trail_profit_threshold/quantity
                new_stoploss = max(current_stoploss, min_trail)
                
            # Update stoploss if it's higher than current
            if new_stoploss > current_stoploss:
                self.positions[symbol]['stoploss'] = new_stoploss
                logger.info(f"Updated trailing stoploss for {symbol} to {new_stoploss}")
                
                # Update stoploss order
                try:
                    response = self.client.modifyorder(
                        symbol=symbol,
                        exchange="NSE",
                        order_id=position['order_id'],
                        stoploss=new_stoploss
                    )
                    logger.info(f"Modified stoploss order for {symbol}: {response}")
                except Exception as e:
                    logger.error(f"Error updating stoploss order for {symbol}: {str(e)}")
    
    def execute_trades(self):
        """Execute trades based on signals"""
        # First update trailing stoploss for existing positions
        for symbol in list(self.positions.keys()):
            try:
                current_price = float(self.client.ltp(symbol, "NSE")['ltp'])
                self.update_trailing_stoploss(symbol, current_price)
            except Exception as e:
                logger.error(f"Error updating trailing stoploss for {symbol}: {str(e)}")
        
        # Then check for new entry signals
        for symbol in self.watchlist:
            try:
                # Skip if already in position
                if symbol in self.positions:
                    continue
                    
                # Get and analyze data
                weekly_data = self.get_weekly_data(symbol)
                if weekly_data is None:
                    continue
                
                # Check buy conditions
                if self.check_buy_signal(weekly_data):
                    current_price = weekly_data['close'].iloc[-1]
                    dma_20 = weekly_data['20_DMA'].iloc[-1]
                    
                    # Calculate position size and initial stoploss
                    quantity, initial_stoploss = self.calculate_position_size(current_price, dma_20)
                    if quantity <= 0:
                        logger.warning(f"Invalid position size calculated for {symbol}")
                        continue
                    
                    # Place buy order
                    response = self.client.placesmartorder(
                        strategy="Weekly DMA-RSI Strategy",
                        symbol=symbol,
                        action="BUY",
                        exchange="NSE",
                        price_type="MARKET",
                        product="CNC",
                        quantity=quantity,
                        stoploss=initial_stoploss
                    )
                    
                    logger.info(f"Buy order placed for {symbol}: {response}")
                    self.positions[symbol] = {
                        'quantity': quantity,
                        'entry_price': current_price,
                        'stoploss': initial_stoploss,
                        'order_id': response.get('order_id')  # Store order ID for modifications
                    }
                    
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
    
    def run_strategy(self):
        """Main strategy loop"""
        logger.info("Starting Weekly DMA-RSI Strategy...")
        
        while True:
            try:
                # Only execute during market hours
                current_time = datetime.now().time()
                if current_time >= time(9, 15) and current_time <= time(15, 30):
                    self.execute_trades()
                    
                # Sleep for 1 hour before next check
                # Since it's a weekly strategy, we don't need frequent checks
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"Strategy error: {str(e)}")
                time.sleep(300)  # Sleep for 5 minutes on error

if __name__ == "__main__":
    # Example usage
    API_KEY = "9c0e0c5af661612e8d52ce35064fffea44683c7cff941e5bc11fa533259c25e3"
    WATCHLIST = [
        "RELIANCE",
        "TCS",
        "HDFCBANK",
        # Add more symbols from your watchlist
    ]
    
    strategy = WeeklyDMARSIStrategy(
        API_KEY,
        WATCHLIST,
        risk_amount=2000,
        min_stoploss=50,
        trail_profit_threshold=2000
    )
    strategy.run_strategy() 