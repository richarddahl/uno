# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework# core_library/logging/interfaces.py

import datetime
import json
import logging
import socket
import traceback
import uuid
from typing import Any


class JsonFormatter(logging.Formatter):
    """Formatter that outputs JSON strings after parsing the log record"""

    def __init__(
        self,
        include_stack_info: bool = True,
        extra_fields: dict[str, Any] | None = None,
    ):
        self.include_stack_info = include_stack_info
        self.hostname = socket.gethostname()
        self.extra_fields = extra_fields or {}

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON"""
        log_data: dict[str, Any] = {
            # Basic log record info
            "timestamp": datetime.datetime.fromtimestamp(
                record.created, tz=datetime.UTC
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            # System context
            "process_id": record.process,
            "thread_id": record.thread,
            "hostname": self.hostname,
            # Include any static extra fields
            **self.extra_fields,
        }

        # Include a unique ID for each log entry (useful for tracing)
        log_data["log_id"] = str(uuid.uuid4())

        # Add contextual info from extra parameters
        for key, value in record.__dict__.items():
            # Skip standard LogRecord attributes and private attributes
            if key not in logging.LogRecord.__dict__ and not key.startswith("_"):
                log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            exc_type = record.exc_info[0]
            log_data["exception"] = {
                "type": exc_type.__name__ if exc_type else "None",
                "message": str(record.exc_info[1]),
                "traceback": (
                    traceback.format_exception(*record.exc_info)
                    if self.include_stack_info
                    else None
                ),
            }

        # Add stack info if present and enabled
        if self.include_stack_info and record.stack_info:
            log_data["stack_info"] = record.stack_info

        # Return JSON string
        return json.dumps(log_data)


class JsonLogger:
    """Logger implementation that produces structured JSON logs"""

    def __init__(
        self, logger: logging.Logger, default_context: dict[str, Any] | None = None
    ):
        self._logger = logger
        self._default_context = default_context or {}

    def _log(self, level: int, message: str, **context: Any) -> None:
        """Internal method to handle logging with merged context"""
        # Merge default context with provided context (provided context takes precedence)
        merged_context = {**self._default_context, **context}
        self._logger.log(level, message, extra=merged_context)

    def debug(self, message: str, **context: Any) -> None:
        self._log(logging.DEBUG, message, **context)

    def info(self, message: str, **context: Any) -> None:
        self._log(logging.INFO, message, **context)

    def warning(self, message: str, **context: Any) -> None:
        self._log(logging.WARNING, message, **context)

    def error(self, message: str, **context: Any) -> None:
        self._log(logging.ERROR, message, **context)

    def critical(self, message: str, **context: Any) -> None:
        self._log(logging.CRITICAL, message, **context)


class JsonLoggerFactory:
    """Factory for creating structured JSON loggers"""

    def __init__(
        self,
        root_logger_name: str = "uno",
        include_stack_info: bool = True,
        extra_fields: dict[str, Any] | None = None,
        log_level: int = logging.INFO,
        handlers: list[logging.Handler] | None = None,
    ):
        self.root_logger_name = root_logger_name
        self.include_stack_info = include_stack_info
        self.extra_fields = extra_fields or {}

        # Set up the root logger
        self.root_logger = logging.getLogger(root_logger_name)
        self.root_logger.setLevel(log_level)

        # Clear any existing handlers and add a NullHandler by default
        for handler in list(self.root_logger.handlers):
            self.root_logger.removeHandler(handler)
        self.root_logger.addHandler(logging.NullHandler())

        # Add any provided handlers
        if handlers:
            for handler in handlers:
                # Ensure each handler uses our JSON formatter
                handler.setFormatter(JsonFormatter(include_stack_info, extra_fields))
                self.root_logger.addHandler(handler)

    def create_logger(
        self, component_name: str, default_context: dict[str, Any] | None = None
    ) -> JsonLogger:
        """Create a component-specific structured JSON logger"""
        logger_name = f"{self.root_logger_name}.{component_name}"
        python_logger = logging.getLogger(logger_name)

        # Set default context for this component
        component_context = {"component": component_name}
        if default_context:
            component_context.update(default_context)

        return JsonLogger(python_logger, component_context)

    def add_handler(self, handler: logging.Handler) -> None:
        """Add a new handler to the root logger"""
        handler.setFormatter(JsonFormatter(self.include_stack_info, self.extra_fields))
        self.root_logger.addHandler(handler)

    def update_extra_fields(self, extra_fields: dict[str, Any]) -> None:
        """Update the extra fields included in all logs"""
        self.extra_fields.update(extra_fields)
        # Update formatters in all handlers
        for handler in self.root_logger.handlers:
            if not isinstance(handler, logging.NullHandler):
                handler.setFormatter(
                    JsonFormatter(self.include_stack_info, self.extra_fields)
                )
