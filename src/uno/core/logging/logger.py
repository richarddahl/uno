"""
Centralized logger abstraction for Uno framework.

Wraps Python's standard logging, loads config from uno.config, and exposes a DI-friendly logger.
"""

from uno.core.logging.logger import get_logger
import logging
import sys
from functools import lru_cache
from logging import Logger

from uno.config.logging import logging_config


@lru_cache(maxsize=16)
def configure_root_logger():
    """Configure the root logger according to uno.config.logging.logging_config."""
    level = getattr(logging, logging_config.LEVEL.upper(), logging.INFO)
    handlers = []

    if logging_config.CONSOLE_OUTPUT:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter(
                fmt=logging_config.FORMAT,
                datefmt=logging_config.DATE_FORMAT,
            )
        )
        handlers.append(console_handler)

    if logging_config.FILE_OUTPUT and logging_config.FILE_PATH:
        file_handler = logging.handlers.RotatingFileHandler(
            logging_config.FILE_PATH,
            maxBytes=logging_config.MAX_BYTES,
            backupCount=logging_config.BACKUP_COUNT,
        )
        file_handler.setFormatter(
            logging.Formatter(
                fmt=logging_config.FORMAT,
                datefmt=logging_config.DATE_FORMAT,
            )
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        handlers=handlers if handlers else None,
        format=logging_config.FORMAT,
        datefmt=logging_config.DATE_FORMAT,
    )


@lru_cache(maxsize=16)
def get_logger(name: str | None = None) -> Logger:
    """Get a logger instance (optionally by name)."""
    configure_root_logger()
    return get_logger(name or "uno")
