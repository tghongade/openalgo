from fyers_connect import get_client
from datetime import datetime, timedelta
import pandas as pd

def test_data_fetch():
    try:
        # Initialize client
        client = get_client()
        print("Client initialized successfully")
        
        # Set date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # Get last 30 days of data
        
        # Test symbol
        symbol = "RELIANCE"
        exchange = "NSE"
        
        print(f"\nFetching data for {symbol} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Fetch data
        response = client.history(
            symbol=symbol,
            exchange=exchange,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            interval='1D'
        )
        
        print("\nAPI Response Details:")
        print(f"Type: {type(response)}")
        if response is not None:
            print(f"Content: {response}")
            
            if isinstance(response, dict):
                print("\nDictionary keys:", response.keys())
            elif isinstance(response, list):
                print("\nList length:", len(response))
                if len(response) > 0:
                    print("First item:", response[0])
                    
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_data_fetch() 