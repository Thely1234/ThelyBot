"""Package initialization for the arbitrage bot.

Imports only the new open-Python modules. This package intentionally does
not import any compiled (.so) module.
"""

__version__ = "2.0.0"
__author__ = "Trading Team"

from .bot import Bot
from .connections import NonceTracker, assert_allowed_host, get_web3
from .logging_setup import setup_logger
from .market import MarketData
from .pricing import PriceFeed

__all__ = [
    "Bot",
    "NonceTracker",
    "assert_allowed_host",
    "get_web3",
    "setup_logger",
    "MarketData",
    "PriceFeed",
]