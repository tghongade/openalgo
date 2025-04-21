"""
Data Preparation Script for AI Trading Lab
- Fetches historical data using your strategy's API
- Computes technical indicators (RSI, ATR, moving averages, etc.)
- Saves processed data as CSV for ML modeling
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Import your existing strategy's data fetcher
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../strategies/chatgpt')))
from strategy import fetch_historical_data
from fyers_connect import get_client

# --- CONFIG ---
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)
LOOKBACK_DAYS = 365 * 2  # 2 years
SYMBOLS = [
    # Add your symbols here, or load from your watchlist
    {"symbol": "ZENSARTECH", "exchange": "NSE"},
    {"symbol": "WEL", "exchange": "NSE"},
    # ...
]

# --- MAIN ---
def compute_indicators(df):
    """Add technical indicators to DataFrame."""
    import ta
    df = df.copy()
    df['rsi_14'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['atr_21'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=21).average_true_range()
    df['sma_20'] = df['close'].rolling(20).mean()
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    return df

def main():
    client = get_client()
    for stock in SYMBOLS:
        symbol = stock['symbol']
        exchange = stock['exchange']
        print(f"Fetching historical data for {symbol} ({exchange})...")
        df = fetch_historical_data(symbol, exchange, client, lookback_days=LOOKBACK_DAYS)
        if df is None or df.empty:
            print(f"No data for {symbol}, skipping.")
            continue
        df = compute_indicators(df)
        out_path = OUTPUT_DIR / f"{symbol}_{exchange}_weekly.csv"
        df.to_csv(out_path)
        print(f"Saved: {out_path}")

if __name__ == "__main__":
    main()
