from openalgo import api
import pandas as pd
import time
from datetime import datetime, timedelta

# API Key from OpenAlgo Portal
api_key = '9c0e0c5af661612e8d52ce35064fffea44683c7cff941e5bc11fa533259c25e3'

# Strategy Parameters
strategy = "20DMA Crossover"
symbol = "BHEL"
exchange = "NSE"
product = "MIS"
quantity = 1
dma_period = 20  # 20-day moving average

# Initialize API Client
client = api(api_key=api_key, host='http://127.0.0.1:5000')

def calculate_dma(df):
    """Calculate 20-day moving average."""
    df['20DMA'] = df['close'].rolling(window=dma_period).mean()
    return df

def dma_strategy():
    """The 20DMA crossover trading strategy."""
    position = 0

    while True:
        try:
            # Fetch 1-day historical data for the past 50 days
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=50)).strftime("%Y-%m-%d")

            df = client.history(
                symbol=symbol,
                exchange=exchange,
                interval="1D",  # Daily timeframe
                start_date=start_date,
                end_date=end_date
            )

            # Validate data
            if df.empty:
                print("DataFrame is empty. Retrying...")
                time.sleep(15)
                continue

            # Verify required columns
            if 'close' not in df.columns:
                raise KeyError("Missing 'close' column in DataFrame")

            # Calculate 20DMA
            df = calculate_dma(df)

            # Get latest values
            dma = df['20DMA'].iloc[-2]
            close_price = df['close'].iloc[-2]

            # Execute Buy Order
            if close_price > dma and position <= 0:
                position = quantity
                response = client.placesmartorder(
                    strategy=strategy,
                    symbol=symbol,
                    action="BUY",
                    exchange=exchange,
                    price_type="MARKET",
                    product=product,
                    quantity=quantity,
                    position_size=position
                )
                print("Buy Order Response:", response)

            # Execute Sell Order
            elif close_price < dma and position >= 0:
                position = quantity * -1
                response = client.placesmartorder(
                    strategy=strategy,
                    symbol=symbol,
                    action="SELL",
                    exchange=exchange,
                    price_type="MARKET",
                    product=product,
                    quantity=quantity,
                    position_size=position
                )
                print("Sell Order Response:", response)

            # Log strategy status
            print("\nStrategy Status:")
            print("-" * 50)
            print(f"Position: {position}")
            print(f"LTP: {close_price}")
            print(f"20DMA: {dma:.2f}")
            print(f"Buy Signal: {close_price > dma}")
            print(f"Sell Signal: {close_price < dma}")
            print("-" * 50)

        except Exception as e:
            print(f"Error in strategy: {str(e)}")
            time.sleep(15)
            continue

        # Wait before next cycle
        time.sleep(15)

if __name__ == "__main__":
    print(f"Starting {strategy}...")
    dma_strategy()
