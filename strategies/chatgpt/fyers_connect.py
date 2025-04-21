# fyers_connect.py

from openalgo import api
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get configuration from environment variables
API_KEY = os.getenv('APP_KEY')
API_SECRET = os.getenv('BROKER_API_SECRET')
HOST = os.getenv('HOST_SERVER', 'http://127.0.0.1:5000')

# Create client once and reuse
client = None

def get_client():
    """
    Returns the OpenAlgo client for API communication.
    """
    global client
    
    if client is None:
        try:
            print(f"\nConnecting to OpenAlgo server at {HOST}")
            print(f"Using API key: {API_KEY}")
            print(f"Using API secret: {API_SECRET}")
            
            # Initialize the OpenAlgo API client
            client = api(api_key=API_KEY, host=HOST)
            
            # Test connection by trying to fetch a simple history
            try:
                test_data = client.history(
                    symbol="SBIN",
                    exchange="NSE",
                    start_date="2025-04-10",
                    end_date="2025-04-17",
                    interval="D"
                )
                if test_data is not None:
                    print("SUCCESS: Successfully connected to OpenAlgo server")
                    return client
                else:
                    print("ERROR: Failed to fetch test data")
                    return None
            except Exception as e:
                print(f"ERROR: API test failed: {str(e)}")
                return None
                
        except Exception as e:
            print(f"ERROR: Error connecting to OpenAlgo server: {str(e)}")
            return None
    
    return client
