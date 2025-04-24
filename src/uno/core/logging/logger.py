"""
Centralized logger abstraction for Uno framework.

Wraps Python's standard logging, loads config from uno.core.config, and exposes a DI-friendly logger.
"""

import logging
import os
import sys

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

from uno.core.config.base import (
    DevSettingsConfigDict,
    ProdSettingsConfigDict,
    TestSettingsConfigDict,
)
from uno.core.di.provider import ServiceLifecycle

# Type alias for logger
Logger = logging.Logger


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

    model_config = ConfigDict(env_prefix="UNO_LOG_")


class Prod(LoggingConfig):
    model_config = ProdSettingsConfigDict


class Dev(LoggingConfig):
    model_config = DevSettingsConfigDict


class Test(LoggingConfig):
    model_config = TestSettingsConfigDict


# DI-managed LoggerService implementation
class LoggerService(ServiceLifecycle):
    """
    Dependency-injected singleton logging service for Uno.
    Handles logger configuration, lifecycle, and DI-friendly logger retrieval.
    """

    def __init__(self, config: LoggingConfig | None = None) -> None:
        self._config: LoggingConfig = config or self._load_config()
        self._initialized: bool = False
        self._loggers: dict[str, Logger] = {}

    def _load_config(self) -> LoggingConfig:
        env_settings: dict[str, type[LoggingConfig]] = {
            "dev": Dev,
            "test": Test,
            "prod": Prod,
        }
        env = os.environ.get("ENV", "dev").lower()
        return env_settings.get(env, Dev)()

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._configure_root_logger()
        self._initialized = True

    async def dispose(self) -> None:
        # Optionally flush/close handlers or perform cleanup
        self._loggers.clear()
        self._initialized = False

    def get_logger(self, name: str | None = None) -> Logger:
        if not self._initialized:
            raise RuntimeError("LoggerService must be initialized before use.")
        logger_name = name or "uno"
        if logger_name not in self._loggers:
            self._loggers[logger_name] = logging.getLogger(logger_name)
        return self._loggers[logger_name]

    def _configure_root_logger(self) -> None:
        cfg = self._config
        level = getattr(logging, cfg.LEVEL.upper(), logging.INFO)
        handlers = []
        if cfg.CONSOLE_OUTPUT:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(
                logging.Formatter(fmt=cfg.FORMAT, datefmt=cfg.DATE_FORMAT)
            )
            handlers.append(console_handler)
        if cfg.FILE_OUTPUT and cfg.FILE_PATH:
            file_handler = logging.handlers.RotatingFileHandler(
                cfg.FILE_PATH,
                maxBytes=cfg.MAX_BYTES,
                backupCount=cfg.BACKUP_COUNT,
            )
            file_handler.setFormatter(
                logging.Formatter(fmt=cfg.FORMAT, datefmt=cfg.DATE_FORMAT)
            )
            handlers.append(file_handler)
        logging.basicConfig(
            level=level,
            handlers=handlers if handlers else None,
            format=cfg.FORMAT,
            datefmt=cfg.DATE_FORMAT,
        )


# For backward compatibility: create a default singleton instance (to be deprecated)
logger_service = LoggerService()


# This function can be used for legacy code, but DI should be preferred
def get_logger(name: str | None = None) -> Logger:
    if not logger_service._initialized:
        import asyncio

        asyncio.run(logger_service.initialize())
    return logger_service.get_logger(name)
