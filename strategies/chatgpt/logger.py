# logger.py

import logging
from datetime import datetime
import os

# Create logs directory if not exists
os.makedirs("logs", exist_ok=True)

# Configure the logger
log_file = f"logs/strategy_log_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def log_event(message, level="info"):
    """
    Logs a message to both console and log file.
    Level can be: 'info', 'warning', 'error', 'critical'
    """
    message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}"
    print(message)

    if level == "info":
        logging.info(message)
    elif level == "warning":
        logging.warning(message)
    elif level == "error":
        logging.error(message)
    elif level == "critical":
        logging.critical(message)
