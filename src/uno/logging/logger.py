"""
Logger implementation for the Uno framework.

This module provides the default logger implementation based on Python's
standard logging module, enhanced with structured logging capabilities.
"""

from __future__ import annotations

import contextlib
import json
import logging
import sys
import threading
from contextvars import ContextVar
from logging import Handler, Logger, StreamHandler
from typing import Any, Dict, Generator, Optional, cast

from uno.errors import UnoError
from uno.logging.config import LoggingSettings
from uno.logging.protocols import LogLevel, LoggerProtocol

# Context variable for storing log context data
_log_context: ContextVar[Dict[str, Any]] = ContextVar("log_context", default={})


class StructuredFormatter(logging.Formatter):
    """Formatter that supports structured logging with context data."""

    def __init__(
        self,
        json_format: bool = False,
        include_timestamp: bool = True,
        include_level: bool = True,
    ) -> None:
        """Initialize a structured formatter.

        Args:
            json_format: Whether to format logs as JSON
            include_timestamp: Whether to include timestamps in logs
            include_level: Whether to include log level in logs
        """
        self.json_format = json_format
        self.include_timestamp = include_timestamp
        self.include_level = include_level

        # Define format string based on settings
        fmt = "%(message)s"
        if include_timestamp:
            fmt = "%(asctime)s " + fmt
        if include_level and not json_format:
            fmt = fmt + " [%(levelname)s]"

        super().__init__(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with structured data.

        Args:
            record: The log record to format

        Returns:
            Formatted log string
        """
        # Extract extra fields from record
        extra: Dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and key != "message":
                extra[key] = value

        # Add current context from context var
        context = _log_context.get()
        if context:
            extra.update(context)

        # Format based on configured style
        if self.json_format:
            return self._format_json(record, extra)
        else:
            # Get the base message from the parent formatter for text format
            message = super().format(record)
            return self._format_text(record, message, extra)

    def _format_json(self, record: logging.LogRecord, extra: Dict[str, Any]) -> str:
        """Format a log record as JSON.

        Args:
            record: Log record
            extra: Extra context data

        Returns:
            JSON-formatted log string
        """
        log_data = {"message": record.getMessage(), **extra}

        # Add level if configured
        if self.include_level:
            log_data["level"] = record.levelname

        # Add timestamp if configured
        if self.include_timestamp:
            log_data["timestamp"] = self.formatTime(record, self.datefmt)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

    def _format_text(
        self, record: logging.LogRecord, message: str, extra: Dict[str, Any]
    ) -> str:
        """Format a log record as plain text.

        Args:
            record: Log record
            message: Formatted message
            extra: Extra context data

        Returns:
            Text-formatted log string
        """
        if not extra:
            return message

        # Format the extra context as key-value pairs
        ctx_str = " ".join(f"{k}={self._format_value(v)}" for k, v in extra.items())
        return f"{message} {ctx_str}"

    def _format_value(self, value: Any) -> str:
        """Format a value for text output.

        Args:
            value: Value to format

        Returns:
            Formatted value string
        """
        if isinstance(value, str):
            # Quote strings that contain spaces
            if " " in value:
                return f'"{value}"'
            return value
        if isinstance(value, (dict, list)):
            # Convert complex types to JSON
            return json.dumps(value)
        return str(value)


class UnoLogger(LoggerProtocol):
    """Default logger implementation for the Uno framework."""

    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        settings: Optional[LoggingSettings] = None,
    ) -> None:
        """Initialize a new logger.

        Args:
            name: Logger name
            level: Default log level
            settings: Optional logger settings (loads from environment if None)
        """
        self.name = name
        self._settings = settings or LoggingSettings.load()

        # Create the underlying Python logger
        self._logger = logging.getLogger(name)

        # Configure with settings
        self._configure(level)

        # Bound context values for this logger instance
        self._bound_context: Dict[str, Any] = {}

    def _configure(self, level: LogLevel) -> None:
        """Configure the logger with the provided settings.

        Args:
            level: Default log level
        """
        # Apply module-specific level if available
        if self.name in self._settings.module_levels:
            level = self._settings.module_levels[self.name]

        # Set default level
        self._logger.setLevel(level.to_stdlib_level())

        # Clear any existing handlers
        for handler in list(self._logger.handlers):
            self._logger.removeHandler(handler)

        # Create formatter
        formatter = StructuredFormatter(
            json_format=self._settings.json_format,
            include_timestamp=self._settings.include_timestamp,
        )

        # Add console handler if enabled
        if self._settings.console_enabled:
            console = StreamHandler(sys.stdout)
            console.setFormatter(formatter)
            console.setLevel(logging.NOTSET)  # Ensure handler does not filter out DEBUG
            self._logger.addHandler(console)

        # Add file handler if enabled
        if self._settings.file_enabled and self._settings.file_path:
            file_handler = logging.FileHandler(self._settings.file_path)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

        # Make sure output is flushed immediately for testing
        self._logger.propagate = False

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message.

        Args:
            message: Log message
            **kwargs: Additional context data
        """
        self._log(logging.CRITICAL, message, **kwargs)

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Internal logging method with context handling.

        Args:
            level: Log level
            message: Log message
            **kwargs: Additional context data
        """
        # Check if this includes an error object
        exc_info = None
        extra = {**self._bound_context}

        for key, value in kwargs.items():
            if key == "exc_info" or key == "exception":
                if isinstance(value, BaseException):
                    exc_info = (type(value), value, value.__traceback__)
                elif isinstance(value, bool) and value:
                    exc_info = sys.exc_info()

                # Extract context from UnoError
                if isinstance(value, UnoError) and hasattr(value, "context"):
                    for ctx_key, ctx_value in value.context.items():
                        extra[f"error_{ctx_key}"] = ctx_value

                    # Add error category and code
                    if hasattr(value, "category"):
                        extra["error_category"] = value.category.name
                    if hasattr(value, "error_code"):
                        extra["error_code"] = value.error_code
            else:
                extra[key] = value

        # Log with all context
        self._logger.log(level, message, exc_info=exc_info, extra=extra)

        # Ensure handlers flush immediately for testing
        for handler in self._logger.handlers:
            handler.flush()

    def set_level(self, level: LogLevel) -> None:
        """Set the logger's level.

        Args:
            level: New logging level
        """
        self._logger.setLevel(level.to_stdlib_level())

    @contextlib.contextmanager
    def context(self, **kwargs: Any) -> Generator[None, None, None]:
        """Add context information to all logs within this context.

        Args:
            **kwargs: Context key-value pairs

        Yields:
            None
        """
        # Get the current context
        current = _log_context.get()

        # Create a new context with the additional values
        updated = {**current, **kwargs}

        # Set the new context
        token = _log_context.set(updated)
        try:
            yield
        finally:
            # Restore the previous context
            _log_context.reset(token)

    def bind(self, **kwargs: Any) -> LoggerProtocol:
        """Create a new logger with bound context values.

        Args:
            **kwargs: Context values to bind

        Returns:
            New logger instance with bound context
        """
        logger = UnoLogger(self.name, settings=self._settings)
        logger._bound_context = {**self._bound_context, **kwargs}
        return logger

    def with_correlation_id(self, correlation_id: str) -> LoggerProtocol:
        """Bind a correlation ID to all logs from this logger.

        Args:
            correlation_id: Correlation ID for tracing

        Returns:
            New logger instance with correlation ID
        """
        return self.bind(correlation_id=correlation_id)


def get_logger(name: str, level: Optional[LogLevel] = None) -> LoggerProtocol:
    """Get a logger for the specified name.

    Args:
        name: Logger name (typically __name__)
        level: Optional log level override

    Returns:
        Configured logger instance
    """
    settings = LoggingSettings.load()
    logger = UnoLogger(name, settings=settings)

    if level is not None:
        logger.set_level(level)

    return logger
