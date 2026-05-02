"""
Centralized logging configuration for the trading bot.
Outputs structured logs to both a rotating file and the console.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "trading_bot.log"

_configured = False


def setup_logging(log_level: str = "DEBUG") -> logging.Logger:
    """
    Configure and return the root 'trading_bot' logger.

    - File handler   : DEBUG and above -> logs/trading_bot.log
    - Console handler: WARNING and above -> stderr
    """
    global _configured
    logger = logging.getLogger("trading_bot")

    if _configured:
        return logger

    LOG_DIR.mkdir(exist_ok=True)
    logger.setLevel(getattr(logging, log_level.upper(), logging.DEBUG))

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    _configured = True
    return logger
