import sys
from typing import Any, cast
from unittest.mock import MagicMock, Mock

import pytest

# Mock the injectable decorator at the module level
sys.modules['uno.di.injectable'] = MagicMock()

# Apply the mock to the metrics module before importing it
from uno.errors import metrics as error_metrics
if not hasattr(error_metrics, 'injectable'):
    error_metrics.injectable = lambda x: x

# Type ignore for the mock injection
metrics = cast('Any', error_metrics)

from uno.errors.base import UnoError, ErrorCategory, ErrorSeverity
from uno.events.error_handling import standard_event_error_handler
from uno.logging.errors import ErrorLogger

@pytest.fixture
def fake_logger() -> Mock:
    """Fixture providing a mock logger for testing."""
    return Mock()

@pytest.fixture
def fake_metrics() -> Mock:
    """Fixture providing a mock metrics collector for testing."""
    return Mock()

@pytest.mark.asyncio
async def test_unoerror_with_context_and_handler(fake_logger: Mock, fake_metrics: Mock) -> None:
    """Test that UnoError correctly stores and exposes context."""
    context = {"user_id": "abc123", "operation": "test"}
    error = UnoError(
        message="Something went wrong",
        code="E123",
        category=ErrorCategory.API,
        severity=ErrorSeverity.ERROR,
    ).with_context(context)
    
    assert error.context["user_id"] == "abc123"
    assert error.context["operation"] == "test"
    
    # Test error handler integration
    standard_event_error_handler(
        event="FakeEvent",
        exc=error,
        logger=fake_logger,
        metrics=fake_metrics,
        context=context,
    )
    
    fake_logger.error.assert_called()
    fake_metrics.record_error.assert_called_with(error)

@pytest.mark.asyncio
async def test_error_logger_logs_context(fake_logger: Mock) -> None:
    """Test that ErrorLogger includes context in log output."""
    logger = ErrorLogger(fake_logger)
    context = {"trace_id": "T-999"}
    error = UnoError(
        message="Log error",
        code="ELOG",
        category=ErrorCategory.INTERNAL,
        severity=ErrorSeverity.ERROR,
    ).with_context(context)
    
    await logger.log_error(error)
    
    fake_logger.log.assert_called()
    log_args = fake_logger.log.call_args[0]
    assert any("T-999" in str(arg) for arg in log_args)
    assert any("ELOG" in str(arg) for arg in log_args)

@pytest.mark.asyncio
async def test_standard_handler_wraps_non_uno_error(fake_logger: Mock, fake_metrics: Mock) -> None:
    """Test that standard handler wraps non-UnoError exceptions."""
    context = {"request_id": "REQ-1"}
    exc = ValueError("bad value")
    
    standard_event_error_handler(
        event="AnotherEvent",
        exc=exc,
        logger=fake_logger,
        metrics=fake_metrics,
        context=context,
    )
    
    fake_logger.error.assert_called()
    error_arg = fake_logger.error.call_args[0][0]
    assert "AnotherEvent" in error_arg
    assert "bad value" in error_arg
    fake_metrics.record_error.assert_called()
