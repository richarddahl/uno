from __future__ import annotations

import pytest
from uno.event_store.errors import (
    EventStoreError,
    EventStoreConnectError,
    EventStoreTransactionError,
    EventStoreSearchError,
    ErrorSeverity,
    EVENT_STORE_ERROR,
    EVENT_STORE_CONNECT_ERROR,
    EVENT_STORE_TRANSACTION_ERROR,
    EVENT_STORE_SEARCH_ERROR,
)


def test_event_store_error() -> None:
    """Test EventStoreError creation."""
    error = EventStoreError(
        "Test error",
        code=EVENT_STORE_ERROR,
        severity=ErrorSeverity.ERROR,
        context={"key": "value"},
    )
    assert error.message == "Test error"
    assert error.code == EVENT_STORE_ERROR
    assert error.severity == ErrorSeverity.ERROR
    assert error.context == {"key": "value"}


def test_event_store_connect_error() -> None:
    """Test EventStoreConnectError creation."""
    error = EventStoreConnectError(
        "Connection failed",
        code=EVENT_STORE_CONNECT_ERROR,
        severity=ErrorSeverity.ERROR,
        context={"url": "redis://localhost:6379"},
    )
    assert error.message == "Connection failed"
    assert error.code == EVENT_STORE_CONNECT_ERROR
    assert error.severity == ErrorSeverity.ERROR
    assert error.context == {"url": "redis://localhost:6379"}


def test_event_store_transaction_error() -> None:
    """Test EventStoreTransactionError creation."""
    error = EventStoreTransactionError(
        "Transaction failed",
        code=EVENT_STORE_TRANSACTION_ERROR,
        severity=ErrorSeverity.ERROR,
        context={"status": "FAILED"},
    )
    assert error.message == "Transaction failed"
    assert error.code == EVENT_STORE_TRANSACTION_ERROR
    assert error.severity == ErrorSeverity.ERROR
    assert error.context == {"status": "FAILED"}


def test_event_store_search_error() -> None:
    """Test EventStoreSearchError creation."""
    error = EventStoreSearchError(
        "Search failed",
        code=EVENT_STORE_SEARCH_ERROR,
        severity=ErrorSeverity.ERROR,
        context={"query": "test"},
    )
    assert error.message == "Search failed"
    assert error.code == EVENT_STORE_SEARCH_ERROR
    assert error.severity == ErrorSeverity.ERROR
    assert error.context == {"query": "test"}


def test_event_store_error_context() -> None:
    """Test EventStoreError with empty context."""
    error = EventStoreError(
        "Test error", code=EVENT_STORE_ERROR, severity=ErrorSeverity.ERROR
    )
    assert error.context == {}


def test_event_store_error_str() -> None:
    """Test EventStoreError string representation."""
    error = EventStoreError(
        "Test error",
        code=EVENT_STORE_ERROR,
        severity=ErrorSeverity.ERROR,
        context={"key": "value"},
    )
    assert error.code.code == "EVENT_STORE_ERROR"
    assert error.severity == ErrorSeverity.ERROR
    assert error.message == "Test error"


def test_event_store_error_str_no_context() -> None:
    """Test EventStoreError string representation with no context."""
    error = EventStoreError(
        "Test error", code=EVENT_STORE_ERROR, severity=ErrorSeverity.ERROR
    )
    assert error.code.code == "EVENT_STORE_ERROR"
    assert error.severity == ErrorSeverity.ERROR
    assert error.message == "Test error"


def test_event_store_error_severity() -> None:
    """Test EventStoreError severity."""
    error = EventStoreError("Test error", severity=ErrorSeverity.WARNING)
    assert error.severity == ErrorSeverity.WARNING
