"""Colored console + file logging.

Safety contract: logging never includes the private key or any mnemonic.
Log files live under ./logs and only contain bot operational messages.
"""

import logging
import os
from datetime import datetime

import colorlog

_LOG_DIR = "logs"
_LOG_FILE_PREFIX = "arb_bot_"


def setup_logger(name: str = "ArbBot", level: str = "INFO") -> logging.Logger:
    logger = colorlog.getLogger(name)

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    logger.handlers.clear()

    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s %(name)-12s %(levelname)-8s %(message)s%(reset)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    os.makedirs(_LOG_DIR, exist_ok=True)
    log_filename = os.path.join(
        _LOG_DIR,
        "{}{}.log".format(_LOG_FILE_PREFIX, datetime.now().strftime("%Y%m%d")),
    )
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(numeric_level)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger