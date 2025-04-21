# watchlist.py

import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategies.chatgpt.logger import log_event

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WATCHLIST_FILE = os.path.join(SCRIPT_DIR, "watchlist.json")

def load_watchlist():
    """
    Load the list of stocks to be monitored from the watchlist JSON file.
    """
    if not os.path.exists(WATCHLIST_FILE):
        log_event(f"Watchlist file '{WATCHLIST_FILE}' not found.", level="error")
        return []

    try:
        with open(WATCHLIST_FILE, 'r') as f:
            watchlist = json.load(f)
        log_event(f"Loaded {len(watchlist['stocks'])} stocks from watchlist.")
        return watchlist['stocks']
    except json.JSONDecodeError as e:
        log_event(f"Error parsing watchlist JSON: {str(e)}", level="error")
        return []
    except Exception as e:
        log_event(f"Error reading watchlist: {str(e)}", level="error")
        return []

def save_watchlist(watchlist):
    """
    Save the watchlist to JSON file
    """
    try:
        with open(WATCHLIST_FILE, 'w') as f:
            json.dump({"stocks": watchlist}, f, indent=4)
        log_event(f"Watchlist saved with {len(watchlist)} stocks.")
        return True
    except Exception as e:
        log_event(f"Error saving watchlist: {str(e)}", level="error")
        return False 