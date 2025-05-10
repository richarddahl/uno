"""Tests for the Uno logging system.

This module contains tests for the logging foundation components,
including the logger protocol, configuration, and structured logging.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from contextlib import redirect_stdout
from io import StringIO
from typing import Any, Dict, Optional, cast

import pytest

from uno.errors import ErrorCategory, UnoError
from uno.logging import LogLevel, LoggerProtocol, UnoLogger, get_logger
from uno.logging.config import LoggingSettings

pytestmark = pytest.mark.usefixtures('allow_logging')


class TestLogLevel:
    """Tests for the LogLevel enum."""

    def test_log_level_values(self) -> None:
        """Test that the LogLevel enum has the expected values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"

    def test_to_stdlib_level(self) -> None:
        """Test conversion to standard library logging levels."""
        assert LogLevel.DEBUG.to_stdlib_level() == logging.DEBUG
        assert LogLevel.INFO.to_stdlib_level() == logging.INFO
        assert LogLevel.WARNING.to_stdlib_level() == logging.WARNING
        assert LogLevel.ERROR.to_stdlib_level() == logging.ERROR
        assert LogLevel.CRITICAL.to_stdlib_level() == logging.CRITICAL

    def test_from_string(self) -> None:
        """Test converting strings to LogLevel enum values."""
        assert LogLevel.from_string("DEBUG") == LogLevel.DEBUG
        assert LogLevel.from_string("info") == LogLevel.INFO
        assert LogLevel.from_string("Warning") == LogLevel.WARNING
        assert LogLevel.from_string("ERROR") == LogLevel.ERROR
        assert LogLevel.from_string("critical") == LogLevel.CRITICAL

    def test_from_string_invalid(self) -> None:
        """Test that passing an invalid string to from_string raises ValueError."""
        with pytest.raises(ValueError):
            LogLevel.from_string("TRACE")


class TestLoggingSettings:
    """Tests for the LoggingSettings class."""

    def test_default_settings(self) -> None:
        """Test default logging settings."""
        settings = LoggingSettings()

        assert settings.level == "INFO"
        assert settings.json_format is False
        assert settings.include_timestamp is True
        assert settings.include_level is True
        assert settings.console_enabled is True
        assert settings.file_enabled is False
        assert settings.file_path is None

    def test_override_settings(self) -> None:
        """Test overriding default settings."""
        settings = LoggingSettings(
            level="DEBUG",
            json_format=True,
            file_enabled=True,
            file_path="/tmp/log.txt",
        )

        assert settings.level == "DEBUG"
        assert settings.json_format is True
        assert settings.file_enabled is True
        assert settings.file_path == "/tmp/log.txt"

    def test_load_from_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading settings from environment variables."""
        monkeypatch.setenv("UNO_LOGGING_LEVEL", "DEBUG")
        monkeypatch.setenv("UNO_LOGGING_JSON_FORMAT", "true")
        monkeypatch.setenv("UNO_LOGGING_FILE_ENABLED", "true")
        monkeypatch.setenv("UNO_LOGGING_FILE_PATH", "/var/log/app.log")

        settings = LoggingSettings.load()

        assert settings.level == "DEBUG"
        assert settings.json_format is True
        assert settings.file_enabled is True
        assert settings.file_path == "/var/log/app.log"


class TestUnoLogger:
    """Tests for the UnoLogger implementation."""

    def test_create_logger(self) -> None:
        """Test creating a logger with default settings."""
        logger = UnoLogger("test_logger")

        assert logger.name == "test_logger"
        assert isinstance(logger._logger, logging.Logger)
        assert len(logger._bound_context) == 0

    def test_log_methods(self) -> None:
        """Test that all log methods work as expected."""
        buffer = StringIO()

        # Create a logger with a simple console formatter
        settings = LoggingSettings(
            level=LogLevel.DEBUG, include_timestamp=False  # Simplifies testing output
        )
        with redirect_stdout(buffer):
            logger = UnoLogger(
                f"test_methods_debug_{uuid.uuid4()}",
                level=LogLevel.DEBUG,  # Explicitly pass level parameter
                settings=settings,
            )
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")

        output = buffer.getvalue()

        # Verify all messages were logged
        assert "Debug message" in output
        assert "Info message" in output
        assert "Warning message" in output
        assert "Error message" in output
        assert "Critical message" in output

    def test_log_with_context(self) -> None:
        """Test logging with context data."""
        buffer = StringIO()

        # Create a logger with a simple console formatter
        settings = LoggingSettings(level=LogLevel.INFO, include_timestamp=False)
        with redirect_stdout(buffer):
            logger = UnoLogger("test_context", settings=settings)

            # Log with context
            logger.info("User login", user_id=123, role="admin")

        output = buffer.getvalue()

        # Verify context was included
        assert "User login" in output
        assert "user_id=123" in output
        assert "role=admin" in output

    def test_bind_context(self) -> None:
        """Test binding context to a logger."""
        buffer = StringIO()
        settings = LoggingSettings(level=LogLevel.INFO, include_timestamp=False)
        with redirect_stdout(buffer):
            logger = UnoLogger("test_bind", settings=settings)
            user_logger = logger.bind(user_id=123, session_id="abc123")
            user_logger.info("User action")
            # Add more context at log time
            user_logger.info("Another action", action="click", component="button")
        output = buffer.getvalue()

        # Verify bound context appears in all logs
        assert "user_id=123" in output
        assert "session_id=abc123" in output

        # Verify log-specific context also appears
        assert "action=click" in output
        assert "component=button" in output

    def test_context_manager(self) -> None:
        """Test the context manager for adding context."""
        buffer = StringIO()
        settings = LoggingSettings(level=LogLevel.INFO, include_timestamp=False)
        with redirect_stdout(buffer):
            logger = UnoLogger("test_context_mgr", settings=settings)
            with logger.context(request_id="req123", path="/api/users"):
                logger.info("Processing request")

                # Nested context
                with logger.context(handler="UserHandler"):
                    logger.info("In handler")

                # Back to original context
                logger.info("Request complete")

            # Outside context
            logger.info("No context")

        output = buffer.getvalue()
        lines = [line for line in output.splitlines() if line.strip()]
        last_line = lines[-1] if lines else ""

        # Verify context in the context manager
        assert "Processing request" in output
        assert "request_id=req123" in output
        assert "path=/api/users" in output

        # Verify nested context
        assert "In handler" in output
        assert "handler=UserHandler" in output

        # Verify context was removed in the last log line
        assert "No context" in last_line
        assert "request_id=" not in last_line
        assert "path=" not in last_line
        assert "handler=" not in last_line

    def test_correlation_id(self) -> None:
        """Test creating a logger with a correlation ID."""
        buffer = StringIO()
        settings = LoggingSettings(level=LogLevel.INFO, include_timestamp=False)
        with redirect_stdout(buffer):
            logger = UnoLogger("test_correlation", settings=settings)
            correlated_logger = logger.with_correlation_id("trace-123")
            correlated_logger.info("Correlated message")
        output = buffer.getvalue()
        assert "correlation_id=trace-123" in output

    def test_error_logging(self) -> None:
        """Test logging errors with context extraction."""
        buffer = StringIO()
        settings = LoggingSettings(level=LogLevel.INFO, include_timestamp=False)
        # Create the logger inside the redirect_stdout context
        with redirect_stdout(buffer):
            logger = UnoLogger("test_error", settings=settings)
            error = UnoError(
                message="Failed to connect to database",
                error_code="DB_CONNECTION_ERROR",
                category=ErrorCategory.DB,
                host="db.example.com",
                port=5432,
                retry_count=3,
            )
            logger.error("Database error occurred", exception=error)
        output = buffer.getvalue()

        # Verify error context was extracted
        assert "Database error occurred" in output
        assert "error_category=DB" in output
        assert "error_code=DB_CONNECTION_ERROR" in output
        assert "error_host=db.example.com" in output
        assert "error_port=5432" in output
        assert "error_retry_count=3" in output

    def test_json_formatter(self) -> None:
        """Test JSON formatting of log messages."""
        buffer = StringIO()
        settings = LoggingSettings(
            level=LogLevel.INFO, json_format=True, include_timestamp=True
        )
        # Create the logger INSIDE the redirect_stdout context so the handler attaches to the buffer
        with redirect_stdout(buffer):
            logger = UnoLogger("test_json", settings=settings)
            logger.info(
                "API request", method="GET", path="/users", status=200, duration_ms=45
            )
        output = buffer.getvalue()
        log_data = json.loads(output)

        # Verify JSON structure
        assert log_data["message"] == "API request"
        assert log_data["level"] == "INFO"
        assert "timestamp" in log_data
        assert log_data["method"] == "GET"
        assert log_data["path"] == "/users"
        assert log_data["status"] == 200
        assert log_data["duration_ms"] == 45

    def test_get_logger(self) -> None:
        """Test the get_logger function."""
        # Get a logger
        logger = get_logger("test_function")

        # Verify it's the right type
        assert isinstance(logger, LoggerProtocol)
        assert isinstance(logger, UnoLogger)
        assert logger.name == "test_function"

        # Test with a specific level
        debug_logger = get_logger("test_debug", LogLevel.DEBUG)
        assert isinstance(debug_logger, UnoLogger)
        # Level is set internally, can't easily verify from outside
