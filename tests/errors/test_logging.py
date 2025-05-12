"""Tests for the logging middleware functionality."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, AsyncMock, call

import pytest
from structlog.testing import capture_logs

from uno.errors.base import ErrorCategory, ErrorSeverity
from uno.events.errors import EventError
from uno.errors.context import add_global_context, clear_global_context
from uno.errors.logging import ErrorLogger, LoggingMiddleware
from uno.errors.metrics import ErrorMetrics

if TYPE_CHECKING:
    from uno.types import LoggerProtocol

# Type aliases
MockMetrics = MagicMock
MockLogger = AsyncMock

# Test data
TEST_CORRELATION_ID = "test-correlation-id"
TEST_ERROR_MSG = "Test error message"
TEST_ERROR = ValueError(TEST_ERROR_MSG)
TEST_UNO_ERROR = EventError(
    code="TEST_ERROR",
    message=TEST_ERROR_MSG,
    category=ErrorCategory.INTERNAL,
    severity=ErrorSeverity.ERROR,
    context={"test": "details"},
)

# HTTP Status Codes
HTTP_BAD_REQUEST = 400


class TestErrorLogger:
    """Tests for the ErrorLogger class."""

    @pytest.fixture
    def mock_logger(self) -> MockLogger:
        """Create a mock logger for testing."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_error_logging(self, mock_logger: MockLogger) -> None:
        """Test that error logging works correctly."""
        logger = ErrorLogger()
        logger.logger = mock_logger
        
        await logger.error("Test error", error=TEST_ERROR, extra={"key": "value"})
        
        mock_logger.error.assert_awaited_once()
        args, kwargs = mock_logger.error.await_args
        assert args[0] == "Test error"
        assert "error" in kwargs
        assert "extra" in kwargs

    @pytest.mark.asyncio
    async def test_error_logging_with_uno_error(self, mock_logger: MockLogger) -> None:
        """Test that UnoError is logged with all its details."""
        logger = ErrorLogger()
        logger.logger = mock_logger
        
        await logger.error("Test UnoError", error=TEST_UNO_ERROR)
        
        mock_logger.error.assert_awaited_once()
        args, kwargs = mock_logger.error.await_args
        assert args[0] == "Test UnoError"
        assert kwargs["error"] == TEST_UNO_ERROR


class TestLoggingMiddleware:
    """Tests for the LoggingMiddleware class."""

    @pytest.fixture
    def mock_metrics(self) -> MockMetrics:
        """Create a mock ErrorMetrics instance."""
        return MagicMock(spec=ErrorMetrics)

    @pytest.fixture
    def mock_logger(self) -> MockLogger:
        """Create a mock logger instance with async methods."""
        mock = AsyncMock()
        # Create async methods
        mock.error = AsyncMock()
        mock.warning = AsyncMock()
        mock.critical = AsyncMock()
        mock.exception = AsyncMock()
        return mock

    @pytest.fixture
    def error_logger(self, mock_logger: MockLogger) -> ErrorLogger:
        """Create an ErrorLogger with a mock logger."""
        logger = ErrorLogger()
        logger.logger = mock_logger
        return logger

    @pytest.fixture
    def logging_middleware(
        self, mock_metrics: MockMetrics, error_logger: ErrorLogger
    ) -> LoggingMiddleware:
        """Create a LoggingMiddleware instance for testing."""
        return LoggingMiddleware(metrics=mock_metrics, logger=error_logger)

    @pytest.fixture(autouse=True)
    def reset_context(self) -> AsyncGenerator[None, None]:
        """Reset the context before each test."""
        clear_global_context()
        add_global_context("correlation_id", TEST_CORRELATION_ID)
        yield
        clear_global_context()

    @pytest.mark.asyncio
    async def test_logs_error_with_context(
        self, 
        logging_middleware: LoggingMiddleware, 
        mock_metrics: MockMetrics,
        mock_logger: MockLogger
    ) -> None:
        """Test that errors are logged with context information."""
        await logging_middleware(TEST_ERROR)

        # Verify the error was logged
        mock_logger.error.assert_awaited_once()
        
        # Get the call arguments
        args, kwargs = mock_logger.error.await_args
        
        # Check the message format - should be in format "<uuid>: <message>"
        assert ": " in args[0]  # Should contain a colon separator
        assert TEST_ERROR_MSG in args[0]
        
        # Check the context
        assert kwargs["event"] == "Error processed"
        assert kwargs["error"] == TEST_ERROR  # Should be the error object, not its string representation
        assert kwargs["correlation_id"] == TEST_CORRELATION_ID
        assert kwargs["error_type"] == "ValueError"
        assert "timestamp" in kwargs
        
        # Verify metrics were recorded
        mock_metrics.record_error.assert_called_once_with(TEST_ERROR)

    @pytest.mark.asyncio
    async def test_logs_uno_error_with_details(
        self, 
        logging_middleware: LoggingMiddleware, 
        mock_metrics: MockMetrics,
        mock_logger: MockLogger
    ) -> None:
        """Test that UnoError details are included in the log."""
        await logging_middleware(TEST_UNO_ERROR)

        # Verify the error was logged
        mock_logger.error.assert_awaited_once()
        
        # Get the call arguments
        args, kwargs = mock_logger.error.await_args
        
        # Check the message format - should be in format "<uuid>: <message>"
        assert ": " in args[0]  # Should contain a colon separator
        assert TEST_ERROR_MSG in args[0]
        
        # Check the context
        assert kwargs["error_code"] == "TEST_ERROR"
        assert kwargs["category"] == ErrorCategory.INTERNAL  # Check the enum value
        assert kwargs["severity"] == ErrorSeverity.ERROR  # Check the enum value
        # Check that context contains the correlation_id
        assert "context" in kwargs
        assert "correlation_id" in kwargs["context"]
        assert kwargs["context"]["correlation_id"] == TEST_CORRELATION_ID
        # Check that the error's context is in the root of the kwargs
        assert kwargs["error"] == TEST_UNO_ERROR
        
        # Verify metrics were recorded
        mock_metrics.record_error.assert_called_once_with(TEST_UNO_ERROR)

    @pytest.mark.asyncio
    async def test_handles_missing_context(
        self, 
        logging_middleware: LoggingMiddleware, 
        mock_metrics: MockMetrics,
        mock_logger: MockLogger
    ) -> None:
        """Test that logging works even without context."""
        clear_global_context()  # Clear context
        
        await logging_middleware(TEST_ERROR)

        # Verify the error was logged
        mock_logger.error.assert_awaited_once()
        
        # Get the call arguments
        args, kwargs = mock_logger.error.await_args
        
        # Should still have a correlation_id from get_correlation_id()
        assert "correlation_id" in kwargs
        assert kwargs["correlation_id"] is not None
        
        # Verify metrics were recorded
        mock_metrics.record_error.assert_called_once_with(TEST_ERROR)

    @pytest.mark.asyncio
    async def test_handles_metrics_error(
        self, 
        logging_middleware: LoggingMiddleware, 
        mock_metrics: MockMetrics,
        mock_logger: MockLogger
    ) -> None:
        """Test that logging continues if metrics recording fails."""
        mock_metrics.record_error.side_effect = Exception("Metrics error")
        
        await logging_middleware(TEST_ERROR)

        # Verify the metrics error was logged
        error_calls = mock_logger.error.await_args_list
        assert len(error_calls) == 2  # One for metrics error, one for the actual error
        
        # Check the metrics error log
        metrics_error_call = error_calls[0]
        assert metrics_error_call.args[0] == "Failed to record error metrics"
        assert isinstance(metrics_error_call.kwargs["error"], Exception)
        assert str(metrics_error_call.kwargs["error"]) == "Metrics error"
        
        # Check the actual error log
        error_call = error_calls[1]
        assert ": " in error_call.args[0]  # Should be in format "<uuid>: <message>"
        assert TEST_ERROR_MSG in error_call.args[0]
        assert error_call.kwargs["event"] == "Error processed"
        assert error_call.kwargs["error"] == TEST_ERROR  # Should be the error object, not its string representation
        
        # Verify metrics were attempted to be recorded
        mock_metrics.record_error.assert_called_once_with(TEST_ERROR)
