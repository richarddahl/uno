"""Tests for the Uno logging system.

This module contains tests for the logging foundation components,
including the logger protocol, configuration, and structured logging.
"""

from __future__ import annotations

import json
import logging
import uuid
from contextlib import redirect_stdout
from enum import Enum, auto
from io import StringIO
from typing import Any

import pytest

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError
from uno.logging import LoggerProtocol, LogLevel, UnoLogger, get_logger
from uno.logging.config import LoggingSettings

pytestmark = pytest.mark.usefixtures("allow_logging")


# Define a test-specific enum for error categories if needed
class ErrorCategory(Enum):
    DB = auto()
    API = auto()
    AUTH = auto()


# Create a test-specific database error subclass
class MockDatabaseError(UnoError):
    """Test database error for logging tests."""

    def __init__(
        self,
        message: str,
        code: str,
        category: ErrorCategory = ErrorCategory.DB,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **kwargs: Any,
    ) -> None:
        """Initialize a test database error.

        Args:
            message: Error message
            code: Error code
            category: Error category
            severity: Error severity
            **kwargs: Additional error attributes
        """
        # Initialize the base class with proper parameters
        # Store extra attributes in the context dictionary
        context = kwargs.copy()

        super().__init__(
            code=code,
            message=message,
            category=category,
            severity=severity,
            context=context,
        )

        # Also set attributes directly on the error object for convenience
        for key, value in kwargs.items():
            setattr(self, key, value)


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

    @pytest.mark.asyncio  # Ensure this is an async test
    async def test_log_methods(self) -> None:
        """Test that all log methods work."""
        buffer = StringIO()

        # Create a logger with a simple console formatter
        settings = LoggingSettings(
            level=LogLevel.DEBUG,
            include_timestamp=False,  # Simplifies testing output
        )
        with redirect_stdout(buffer):
            logger = UnoLogger(
                f"test_methods_debug_{uuid.uuid4()}",
                level=LogLevel.DEBUG,  # Explicitly pass level parameter
                settings=settings,
            )
            await logger.debug("Debug message")
            await logger.info("Info message")
            await logger.warning("Warning message")
            await logger.error("Error message")
            await logger.critical("Critical message")

        output = buffer.getvalue()

        # Verify all messages were logged
        assert "Debug message" in output
        assert "Info message" in output
        assert "Warning message" in output
        assert "Error message" in output
        assert "Critical message" in output

    @pytest.mark.asyncio  # Ensure this is an async test
    async def test_log_with_context(self) -> None:
        """Test logging with context values."""
        buffer = StringIO()

        # Create a logger with a simple console formatter
        settings = LoggingSettings(level=LogLevel.INFO, include_timestamp=False)
        with redirect_stdout(buffer):
            logger = UnoLogger("test_context", settings=settings)

            # Log with context
            await logger.info("User login", user_id=123, role="admin")

        output = buffer.getvalue()

        # Verify context was included
        assert "User login" in output
        # Context values are included as JSON in uno_context
        assert '"user_id": 123' in output or '"user_id":123' in output
        assert '"role": "admin"' in output or '"role":"admin"' in output

    @pytest.mark.asyncio
    async def test_bind_context(self) -> None:
        """Test binding context to a logger."""
        buffer = StringIO()
        settings = LoggingSettings(level=LogLevel.INFO, include_timestamp=False)
        with redirect_stdout(buffer):
            logger = UnoLogger("test_bind", settings=settings)
            user_logger = logger.bind(user_id=123, session_id="abc123")
            await user_logger.info("User action")
            # Add more context at log time
            await user_logger.info("Another action", action="click", component="button")
        output = buffer.getvalue()

        # Verify bound context appears in logs
        assert "User action" in output
        # Check for context values in JSON format
        assert '"user_id": 123' in output or '"user_id":123' in output
        assert '"session_id": "abc123"' in output or '"session_id":"abc123"' in output
        # Check that additional context works
        assert '"action": "click"' in output or '"action":"click"' in output
        assert '"component": "button"' in output or '"component":"button"' in output

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test the context manager for adding context."""
        buffer = StringIO()
        settings = LoggingSettings(level=LogLevel.INFO, include_timestamp=False)
        with redirect_stdout(buffer):
            logger = UnoLogger("test_context_mgr", settings=settings)
            with logger.context(request_id="req123", path="/api/users"):
                await logger.info("Processing request")

                # Nested context
                with logger.context(handler="UserHandler"):
                    await logger.info("In handler")

                # Back to original context
                await logger.info("Request complete")

            # Outside context
            await logger.info("No context")

        output = buffer.getvalue()
        lines = [line for line in output.splitlines() if line.strip()]
        last_line = lines[-1] if lines else ""

        # Verify context in the context manager
        assert "Processing request" in output
        # Context is in JSON format
        assert '"request_id": "req123"' in output or '"request_id":"req123"' in output
        assert '"path": "/api/users"' in output or '"path":"/api/users"' in output
        # Check nested context
        assert (
            '"handler": "UserHandler"' in output or '"handler":"UserHandler"' in output
        )

        # Check last line for absence of context keys by examining the uno_context JSON
        assert "No context" in last_line

        # Extract the JSON context from the last line
        context_start = last_line.find('uno_context="')
        if context_start != -1:
            context_json_str = last_line[context_start + 13 :].rstrip('"')
            # Remove escaped quotes
            context_json_str = context_json_str.replace('\\"', '"')
            context_data = json.loads(context_json_str)

            # Now we can precisely check the context keys
            assert "level" in context_data  # Should only contain level
            assert "request_id" not in context_data
            assert "path" not in context_data
            assert "handler" not in context_data
            assert len(context_data) == 1  # Only level should be present
        else:
            # If we can't find and parse the context, at least make sure context keys aren't there
            assert '"request_id"' not in last_line
            assert '"path": "/api/users"' not in last_line
            assert '"handler": "UserHandler"' not in last_line

    @pytest.mark.asyncio
    async def test_correlation_id(self) -> None:
        """Test creating a logger with a correlation ID."""
        buffer = StringIO()
        settings = LoggingSettings(level=LogLevel.INFO, include_timestamp=False)
        with redirect_stdout(buffer):
            logger = UnoLogger("test_correlation", settings=settings)
            correlated_logger = logger.with_correlation_id("trace-123")
            await correlated_logger.info("Correlated message")

        output = buffer.getvalue()

        # Verify the message appears in the output
        assert "Correlated message" in output
        # Correlation ID should appear in uno_context as JSON
        assert (
            '"correlation_id": "trace-123"' in output
            or '"correlation_id":"trace-123"' in output
        )

    @pytest.mark.asyncio
    async def test_error_logging(self) -> None:
        """Test logging errors with context extraction."""
        buffer = StringIO()
        settings = LoggingSettings(level=LogLevel.INFO, include_timestamp=False)
        # Create the logger inside the redirect_stdout context
        with redirect_stdout(buffer):
            logger = UnoLogger("test_error", settings=settings)

            # Use the appropriate test-specific error subclass
            error = MockDatabaseError(
                message="Failed to connect to database",
                code="DB_CONNECTION_ERROR",  # No change needed here - converted in __init__
                category=ErrorCategory.DB,
                host="db.example.com",
                port=5432,
                retry_count=3,
            )
            await logger.error("Database error occurred", exception=error)
        output = buffer.getvalue()

        # Verify error context was extracted
        assert "Database error occurred" in output
        assert '"category": "DB"' in output
        # Also check for other error attributes that should be present
        assert '"code": "DB_CONNECTION_ERROR"' in output
        assert '"message": "Failed to connect to database"' in output

    @pytest.mark.asyncio
    async def test_json_formatter(self) -> None:
        """Test JSON formatting of log messages."""
        buffer = StringIO()
        settings = LoggingSettings(
            level=LogLevel.INFO, json_format=True, include_timestamp=True
        )
        # Create the logger INSIDE the redirect_stdout context so the handler attaches to the buffer
        with redirect_stdout(buffer):
            logger = UnoLogger("test_json", settings=settings)
            await logger.info(
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
