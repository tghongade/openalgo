# config.py

# Test mode settings
TEST_MODE = True  # Set to False for live trading
TEST_BYPASS_TIME = True  # Set to True to bypass time restrictions in test mode
TEST_UNLIMITED_FUNDS = True  # Set to True to bypass fund restrictions in test mode

# Strategy settings
MAX_POSITIONS = 5  # Maximum number of positions to hold
POSITION_SIZE_PERCENT = 20  # Percentage of capital to use per position
MIN_FUNDS_REQUIRED = 10000  # Minimum funds required to place a trade

# Strategy parameters
RISK_PER_TRADE = 0.02  # 2% risk per trade
STOP_LOSS_ATR = 1.8    # ATR multiplier for stop loss
POSITION_SIZE = 1      # Number of shares per trade
