# utils.py

import pytz
from datetime import datetime
from fyers_connect import get_client
from logger import log_event

def get_current_ist_time():
    """Get current time in IST"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

def get_cmp(symbol):
    """
    Fetches the Current Market Price (CMP) of the given symbol using Fyers quote API.
    """
    try:
        fyers = get_client()
        data = fyers.quotes([f"NSE:{symbol}"])
        if data and 'd' in data[0]:
            cmp = float(data[0]['d']['lp'])
            return round(cmp, 2)
        else:
            log_event(f"[{symbol}] CMP fetch failed: No data returned.")
            return None
    except Exception as e:
        log_event(f"[{symbol}] Error fetching CMP: {e}")
        return None
