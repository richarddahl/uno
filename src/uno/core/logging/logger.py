"""
Centralized logger abstraction for Uno framework.

Wraps Python's standard logging, loads config from uno.core.config, and exposes a DI-friendly logger.
"""

import logging
import os
import sys
from functools import lru_cache

from pydantic_settings import BaseSettings

from uno.core.config.base import (
    DevSettingsConfigDict,
    ProdSettingsConfigDict,
    TestSettingsConfigDict,
)


class LoggingConfig(BaseSettings):
    LEVEL: str = "INFO"
    FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    JSON_FORMAT: bool = False
    CONSOLE_OUTPUT: bool = True
    FILE_OUTPUT: bool = False
    FILE_PATH: str | None = None
    BACKUP_COUNT: int = 5
    MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
    PROPAGATE: bool = False
    INCLUDE_LOGGER_CONTEXT: bool = True
    INCLUDE_EXCEPTION_TRACEBACK: bool = True


class Prod(LoggingConfig):
    model_config = ProdSettingsConfigDict


class Dev(LoggingConfig):
    model_config = DevSettingsConfigDict


class Test(LoggingConfig):
    model_config = TestSettingsConfigDict


# Create a dictionary of environment settings
env_settings: dict[str, type[LoggingConfig]] = {"dev": Dev, "test": Test, "prod": Prod}
# Select the environment settings based on the ENV variable
logging_config: Dev | Test | Prod = env_settings[os.environ.get("ENV", "dev").lower()]()


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
def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger instance (optionally by name)."""
    configure_root_logger()
    return logging.getLogger(name or "uno")
