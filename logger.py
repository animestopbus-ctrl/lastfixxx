# Rexbots
# Don't Remove Credit
# Telegram Channel @RexBots_Official

import logging
from logging.handlers import RotatingFileHandler

# ==========================================
# LOGGING CONFIGURATION
# ==========================================

# Define Log Formats
SHORT_LOG_FORMAT = "[%(asctime)s - %(levelname)s] - %(name)s - %(message)s"
FULL_LOG_FORMAT = "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s (%(filename)s:%(lineno)d)"

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format=SHORT_LOG_FORMAT,
    handlers=[
        # Rotate logs: Max 5MB per file, keep last 10 files
        RotatingFileHandler("logs.txt", maxBytes=5 * 1024 * 1024, backupCount=10),
        logging.StreamHandler()
    ]
)

# Suppress noisy logs from Pyrogram (keep only Warnings/Errors)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

def LOGGER(name: str) -> logging.Logger:
    """
    Returns a logger instance with the given name.
    """
    return logging.getLogger(name)
