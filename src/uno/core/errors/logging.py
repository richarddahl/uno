# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Structured logging with context for the Uno framework.

DI-FIRST POLICY: All Uno code should use DI-injected LoggerService for all logging operations. Direct use of Python's logging module is permitted ONLY for system bootstrapping (e.g., configure_logging) or in legacy/compatibility contexts where DI is not yet available. All fallback logger usage must be clearly documented and minimized.

This module provides utilities for structured logging with contextual information and integration with the error handling system. Decorators/utilities that log errors should accept a logger parameter for DI injection whenever possible.
"""

import contextvars
import functools
import inspect
import json
import logging
import logging.config
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from uno.core.errors.base import FrameworkError

# Context variable for logging context
_logging_context = contextvars.ContextVar[dict[str, Any]]("logging_context", default={})


@dataclass
class LogConfig:
    """
    Configuration for logging.

    This class provides a structured way to configure logging
    with sensible defaults.
    """

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    json_format: bool = False
    console_output: bool = True
    file_output: bool = False
    file_path: str | None = None
    backup_count: int = 5
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    propagate: bool = False
    include_logger_context: bool = True
    include_exception_traceback: bool = True


class StructuredLogAdapter(logging.LoggerAdapter):
    """
    Adapter for structured logging.

    This adapter enhances log messages with contextual information.

    NOTE: Uno code should prefer DI-injected LoggerService for logging. This adapter is retained for compatibility with the Python logging system during bootstrapping or legacy scenarios.
    """

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """
        Process the log message and inject context.

        Args:
            msg: The log message
            kwargs: Additional logging parameters

        Returns:
            Tuple of (message, kwargs) with context injected
        """
        # Get a copy of the current logging context
        context = _logging_context.get().copy()

        # Merge with extra provided in the call
        if "extra" in kwargs:
            extra = kwargs["extra"].copy() if kwargs["extra"] else {}
            # Overwrite context with explicit extra values if they conflict
            merged = {**context, **extra}
            kwargs["extra"] = merged
        else:
            kwargs["extra"] = context

        return msg, kwargs


class StructuredJsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logs.

    This formatter converts log records to JSON format with additional contextual information.

    NOTE: Uno code should prefer DI-injected LoggerService for logging. This formatter is retained for compatibility with the Python logging system during bootstrapping or legacy scenarios.
    """

    def __init__(
        self,
        include_logger_context: bool = True,
        include_exception_traceback: bool = True,
    ):
        """
        Initialize the formatter.

        Args:
            include_logger_context: Whether to include logger context in logs
            include_exception_traceback: Whether to include exception traceback in logs
        """
        super().__init__()
        self.include_logger_context = include_logger_context
        self.include_exception_traceback = include_exception_traceback

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as JSON.

        Args:
            record: The log record to format

        Returns:
            JSON string representation of the log record
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
        }

        # Add context if available
        if self.include_logger_context and hasattr(record, "context"):
            log_data["context"] = record.context

        # Add extra attributes if available
        if hasattr(record, "extra"):
            # Avoid duplicate context
            extra = {k: v for k, v in record.extra.items() if k != "context"}
            log_data.update(extra)

        # Add exception info if available
        if record.exc_info and self.include_exception_traceback:
            exc_type, exc_value, exc_tb = record.exc_info
            log_data["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value) if exc_value else None,
            }

            if self.include_exception_traceback and exc_tb:
                log_data["exception"]["traceback"] = self.formatException(
                    record.exc_info
                )

            # Add FrameworkError specific fields
            if isinstance(exc_value, FrameworkError):
                log_data["exception"]["error_code"] = exc_value.error_code
                if hasattr(exc_value, "context") and exc_value.context:
                    log_data["exception"]["error_context"] = exc_value.context

        return json.dumps(log_data, default=str)


def configure_logging(config: LogConfig = None) -> None:
    """
    Configure logging for the application.

    Args:
        config: Logging configuration (optional, uses defaults if not provided)
    """
    config = config or LogConfig()

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.level))

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure console handler
    if config.console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        if config.json_format:
            formatter = StructuredJsonFormatter(
                include_logger_context=config.include_logger_context,
                include_exception_traceback=config.include_exception_traceback,
            )
        else:
            formatter = logging.Formatter(config.format, datefmt=config.date_format)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Configure file handler
    if config.file_output and config.file_path:
        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(
            config.file_path, maxBytes=config.max_bytes, backupCount=config.backup_count
        )
        if config.json_format:
            formatter = StructuredJsonFormatter(
                include_logger_context=config.include_logger_context,
                include_exception_traceback=config.include_exception_traceback,
            )
        else:
            formatter = logging.Formatter(config.format, datefmt=config.date_format)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def add_logging_context(**context: Any) -> None:
    """
    Add key-value pairs to the current logging context.

    Args:
        **context: Key-value pairs to add to the context
    """
    current = _logging_context.get().copy()
    current.update(context)
    _logging_context.set(current)


def get_logging_context() -> dict[str, Any]:
    """
    Get the current logging context.

    Returns:
        The current logging context dictionary
    """
    ctx = _logging_context.get(None)
    if ctx is None:
        return {}
    return ctx.copy()


def clear_logging_context() -> None:
    """
    Clear the current logging context.
    """
    _logging_context.set({})


def with_logging_context(func: Callable) -> Callable:
    """
    Decorator that adds function parameters to logging context.

    This decorator adds the function parameters to the logging context
    when the function is called, and removes them when the function returns.

    Args:
        func: The function to decorate

    Returns:
        The decorated function

    DI Logging Policy:
        If the decorated function receives a 'logger' argument (must be a LoggerService or compatible), it will be used for error logging.
        If not, falls back to legacy logging (documented, discouraged except for bootstrapping/legacy scenarios).
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Get the signature of the function
        sig = inspect.signature(func)

        # Bind the arguments to the signature
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()

        # Get arguments as a dict, filtering out self/cls for methods
        arg_dict = {}
        for key, value in bound.arguments.items():
            if key not in ("self", "cls"):
                if isinstance(value, (str, int, float, bool)) or value is None:
                    arg_dict[key] = value
                else:
                    arg_dict[key] = f"<{type(value).__name__}>"

        # Get the current context
        current_context = _logging_context.get().copy()
        new_context = current_context.copy()
        new_context.update(
            {"function": func.__name__, "module": func.__module__, "args": arg_dict}
        )
        token = _logging_context.set(new_context)

        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Prefer DI-injected logger if available
            logger = None
            if "logger" in bound.arguments:
                logger = bound.arguments["logger"]
            if logger is not None and hasattr(logger, "structured_log"):
                logger.structured_log(
                    "ERROR",
                    f"Exception in {func.__name__}: {e!s}",
                    exc_info=e,
                    context=new_context,
                )
            else:
                # Fallback to legacy structured logging (discouraged)
                legacy_logger = logging.getLogger(func.__module__)
                legacy_logger = StructuredLogAdapter(legacy_logger, {})
                legacy_logger.exception(
                    f"Exception in {func.__name__}: {e!s}", exc_info=e
                )
            raise
        finally:
            _logging_context.reset(token)

    return wrapper
