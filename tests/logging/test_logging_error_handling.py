"""
Unit tests for logger error handling and serialization of error objects.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from uno.errors import UnoError
from uno.logging.logger import LoggerProtocol, get_logger


class MockError(UnoError):
    """Test error class with additional attributes."""

    TEST_PORT = 8080
    TEST_RETRY_COUNT = 3

    def __init__(
        self, 
        message: str, 
        code: str, 
        category: str = "test", 
        severity: str = "ERROR",
        **kwargs: Any
    ) -> None:
        super().__init__(message=message, code=code, severity=severity, **kwargs)
        self.category = category  # type: ignore[assignment]
        self.host = "example.com"
        self.port = self.TEST_PORT
        self.retry_count = self.TEST_RETRY_COUNT


@pytest.fixture
def mock_settings() -> dict[str, str | None]:
    """Create mock settings for testing.

    Returns:
        dict[str, str | None]: Mock settings dictionary
    """
    return {
        "json_format": True,
        "include_timestamp": False,
        "log_to_file": False,
        "log_file_path": None,
        "log_level": "DEBUG",
    }


@pytest.fixture
def logger(mock_settings: dict[str, str | None]) -> LoggerProtocol:
    """Create a test logger with mock handler.

    Args:
        mock_settings: Dictionary with logger settings

    Returns:
        LoggerProtocol: Configured logger instance with mock handler
    """
    with patch("uno.logging.config.LoggingSettings") as mock_settings_cls:
        mock_settings_cls.return_value = MagicMock(**mock_settings)
        test_logger = get_logger("test_logger")
        handler = AsyncMock()
        handler.return_value = None  # Make the mock return None when awaited
        test_logger._handler = handler  # type: ignore[attr-defined]

        # Patch with_correlation_id to always attach the same handler
        orig_with_correlation_id = test_logger.with_correlation_id
        def patched_with_correlation_id(correlation_id: str):
            correlated = orig_with_correlation_id(correlation_id)
            correlated._handler = handler  # type: ignore[attr-defined]
            return correlated
        test_logger.with_correlation_id = patched_with_correlation_id  # type: ignore
        return test_logger


@pytest.mark.asyncio
async def test_logger_handles_uno_error_with_category(
    logger: LoggerProtocol, capsys: Any
) -> None:
    """Test that UnoError with category is properly serialized."""
    error = MockError("Test error", "TEST_ERROR", category="validation")

    await logger.error("Test error occurred", exception=error)

    # Verify the handler was called with the right arguments
    logger._handler.assert_awaited_once()  # type: ignore[attr-defined]
    call_args = logger._handler.await_args[1]  # type: ignore[attr-defined]

    # Check that error details were extracted correctly
    assert call_args["error_type"] == "MockError"
    assert call_args["message"] == "Test error"
    assert call_args["code"] == "TEST_ERROR"
    assert call_args["category"] == "validation"
    assert call_args["host"] == "example.com"
    assert (
        call_args["port"] == MockError.TEST_PORT
    )  # noqa: PLR2004  # Magic number in test
    assert (
        call_args["retry_count"] == MockError.TEST_RETRY_COUNT
    )  # noqa: PLR2004  # Magic number in test


@pytest.mark.asyncio
async def test_logger_handles_uno_error_without_category(
    logger: LoggerProtocol, capsys: Any
) -> None:
    """Test that UnoError without category works correctly."""
    error = UnoError("Test error", "TEST_ERROR", severity="ERROR")

    await logger.error("Test error occurred", exception=error)

    # Verify the handler was called with the right arguments
    logger._handler.assert_awaited_once()
    call_args = logger._handler.await_args[1]

    # Check that error details were extracted correctly
    assert call_args["error_type"] == "UnoError"
    assert call_args["message"] == "Test error"
    assert call_args["code"] == "TEST_ERROR"
    assert "category" not in call_args


@pytest.mark.asyncio
async def test_logger_handles_regular_exception(
    logger: LoggerProtocol, capsys: Any
) -> None:
    """Test that regular exceptions are handled correctly."""
    try:
        raise ValueError("Test value error")
    except Exception as e:
        await logger.error("Test error occurred", exception=e)

    # Verify the handler was called with the right arguments
    logger._handler.assert_awaited_once()
    call_args = logger._handler.await_args[1]

    # Check that exception details were passed through
    assert call_args["exception"] is not None
    assert "ValueError" in str(call_args["exception"])


@pytest.mark.asyncio
async def test_logger_handles_error_in_context(
    logger: LoggerProtocol, capsys: Any
) -> None:
    """Test that errors in context are handled correctly."""
    error = MockError("Test error", "TEST_ERROR", category="validation")

    await logger.error(
        "Test error occurred",
        context={
            "operation": "test_operation",
            "error": error,
        },
    )

    # Verify the handler was called with the right arguments
    logger._handler.assert_awaited_once()
    call_args = logger._handler.await_args[1]

    # Check that error in context was serialized
    assert call_args["context.operation"] == "test_operation"
    assert call_args["context.error.type"] == "MockError"
    assert call_args["context.error.message"] == "Test error"
    assert call_args["context.error.code"] == "TEST_ERROR"
    assert call_args["context.error.category"] == "validation"


@pytest.mark.asyncio
async def test_logger_handles_nested_errors(
    logger: LoggerProtocol, capsys: Any
) -> None:
    """Test that nested error structures are handled correctly."""
    inner_error = MockError("Inner error", "INNER_ERROR", category="inner")
    outer_error = MockError(
        "Outer error", "OUTER_ERROR", cause=inner_error, category="outer"
    )

    await logger.error("Nested error occurred", exception=outer_error)

    # Verify the handler was called with the right arguments
    logger._handler.assert_awaited_once()
    call_args = logger._handler.await_args[1]

    # Check that nested error was serialized
    assert call_args["error_type"] == "MockError"
    assert call_args["message"] == "Outer error"
    assert call_args["code"] == "OUTER_ERROR"
    assert call_args["category"] == "outer"
    assert "cause" in call_args
    assert call_args["cause.type"] == "MockError"
    assert call_args["cause.message"] == "Inner error"
    assert call_args["cause.code"] == "INNER_ERROR"
    assert call_args["cause.category"] == "inner"


@pytest.mark.asyncio
async def test_logger_handles_missing_attributes(
    logger: LoggerProtocol, capsys: Any
) -> None:
    """Test that missing attributes on error objects are handled gracefully."""

    # Create an error with minimal attributes
    class MinimalError(
        Exception
    ):  # noqa: B903  # Intentionally simple class for testing
        """Minimal error class for testing."""

        def __init__(self, message: str) -> None:
            super().__init__(message)
            self.message = message

    error = MinimalError("Minimal error")

    await logger.error("Test error occurred", exception=error)

    # Verify the handler was called with the right arguments
    logger._handler.assert_awaited_once()
    call_args = logger._handler.await_args[1]

    # Check that basic exception info is present
    assert call_args["exception"] is not None
    assert "MinimalError" in str(call_args["exception"])
    # Should not have raised trying to access missing attributes
    assert "error_type" not in call_args
    assert "message" not in call_args
    assert "code" not in call_args


@pytest.mark.asyncio
async def test_logger_handles_category_formatting(
    logger: LoggerProtocol, capsys: Any
) -> None:
    """Test that error category is properly formatted in logs."""
    # Create an error with a specific category
    error = UnoError(
        message="Failed to connect to database",
        code="DB_CONNECTION_ERROR",
        category="DB",
        severity="ERROR",
    )

    await logger.error("Database error occurred", exception=error)

    # Verify the handler was called with the right arguments
    logger._handler.assert_awaited_once()  # type: ignore[attr-defined]
    call_args = logger._handler.await_args[1]  # type: ignore[attr-defined]

    # Check that error category was extracted and formatted correctly
    assert call_args["error_type"] == "UnoError"
    assert call_args["message"] == "Failed to connect to database"
    assert call_args["code"] == "DB_CONNECTION_ERROR"
    assert call_args["category"] == "DB"


@pytest.mark.asyncio
async def test_logger_includes_correlation_id(
    logger: LoggerProtocol, capsys: Any
) -> None:
    """Test that correlation IDs are properly included in logs."""
    correlated_logger = logger.with_correlation_id("trace-123")
    await correlated_logger.info("Correlated message")
    # Check the handler on the correlated logger, not the original logger
    correlated_logger._handler.assert_awaited_once()  # type: ignore[attr-defined]
    call_args = correlated_logger._handler.await_args[1]  # type: ignore[attr-defined]
    # Check that correlation ID was included in the log
    assert call_args.get("correlation_id") == "trace-123"
