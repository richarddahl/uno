# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework

import pytest
import asyncio
import threading
from typing import Any
from uno.errors.base import (
    UnoError,
    ErrorCategory,
    ErrorSeverity,
    get_error_context,
)

from uno.errors.codes import ErrorCode


class FakeAppError(UnoError):
    """Fake application error for testing error handling functionality."""

    def __init__(
        self,
        code: str,
        message: str,
        category: ErrorCategory = ErrorCategory.APPLICATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the fake application error.

        Args:
            code: Error code identifier
            message: Human-readable error message
            category: Category of the error
            severity: Severity level
            context: Additional contextual information
        """
        super().__init__(code, message, category, severity, context)

    @classmethod
    def wrap(
        cls,
        exception: Exception,
        code: str = "FAKE_APP_ERROR",
        message: str | None = None,
        category: ErrorCategory = ErrorCategory.APPLICATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
    ) -> "FakeAppError":
        """Wrap an exception in a FakeAppError.

        Args:
            exception: The exception to wrap
            code: Error code identifier
            message: Human-readable error message (defaults to exception message)
            category: Error category
            severity: Error severity
            context: Additional context information

        Returns:
            A new FakeAppError instance
        """
        # Create a context with information about the original exception
        merged_context = {
            "original_exception": exception.__class__.__name__,
            "original_message": str(exception),
        }

        # Merge with provided context
        if context:
            merged_context.update(context)

        # Use default message if none provided
        if message is None:
            message = f"Wrapped exception: {exception}"

        # Create the error instance
        result = cls(code, message, category, severity, merged_context)

        # Set the __cause__ to maintain the exception chain
        result.__cause__ = exception

        return result

    @classmethod
    async def async_wrap(
        cls,
        exception: Exception,
        code: str = "FAKE_APP_ERROR",
        message: str | None = None,
        category: ErrorCategory = ErrorCategory.APPLICATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
    ) -> "FakeAppError":
        """Asynchronously wrap an exception in a FakeAppError.

        Args:
            exception: The exception to wrap
            code: Error code identifier
            message: Human-readable error message (defaults to exception message)
            category: Error category
            severity: Error severity
            context: Additional context information

        Returns:
            A new FakeAppError instance
        """
        return cls.wrap(exception, code, message, category, severity, context)


class FakeValidationError(UnoError):
    def __init__(self, message: str, context: dict[str, object] | None = None):
        super().__init__(
            code="FAKE_VALIDATION_ERROR",
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            context=context,
        )


# --- Tests ---
def test_unoerror_cannot_be_instantiated():
    with pytest.raises(TypeError):
        UnoError("CODE", "msg", ErrorCategory.INTERNAL, ErrorSeverity.ERROR)


def test_fake_error_subclass_instantiation():
    err = FakeAppError(ErrorCode.INTERNAL_ERROR, "something went wrong")
    assert err.code == "FAKE_APP_ERROR"
    assert err.message == "something went wrong"
    assert err.category == ErrorCategory.INTERNAL
    assert err.severity == ErrorSeverity.ERROR
    assert isinstance(err.context, dict)
    assert err.timestamp is not None


def test_with_context_merges_context():
    err = FakeAppError(
        ErrorCode.UNKNOWN_ERROR,
        "fail",
        ErrorCategory.APPLICATION,
        ErrorSeverity.ERROR,
        context={"a": 1},
    )
    err2 = err.with_context(
        context={"b": 2},
    )
    assert err2.context["a"] == 1
    assert err2.context["b"] == 2
    assert err is not err2


def test_wrap_preserves_original_exception():
    try:
        raise ValueError("bad value")
    except ValueError as e:
        wrapped = FakeAppError.wrap(
            e, "FAKE_WRAP", "wrapped", ErrorCategory.API, ErrorSeverity.ERROR
        )
    assert wrapped.code == "FAKE_WRAP"
    assert wrapped.category == ErrorCategory.API
    assert wrapped.severity == ErrorSeverity.ERROR
    assert wrapped.context["original_exception"] == "ValueError"
    assert wrapped.__cause__.__class__ is ValueError


def test_to_dict_and_str():
    err = FakeValidationError("invalid", {"foo": "bar"})
    d = err.to_dict()
    assert d["code"] == "FAKE_VALIDATION_ERROR"
    assert d["message"] == "invalid"
    assert d["category"] == "VALIDATION"
    assert d["severity"] == "WARNING"
    assert d["context"]["foo"] == "bar"
    assert "timestamp" in d
    s = str(err)
    assert s.startswith("FAKE_VALIDATION_ERROR")


def test_get_error_context():
    ctx = get_error_context()
    assert "file_name" in ctx
    assert "line_number" in ctx
    assert "function_name" in ctx
    assert "timestamp" in ctx


@pytest.mark.asyncio
async def test_async_error_context_propagation():
    async def raise_and_catch():
        try:
            raise FakeAppError(
                ErrorCode.UNKNOWN_ERROR,
                "async fail",
                ErrorCategory.APPLICATION,
                ErrorSeverity.ERROR,
                context={"async": True},
            )
        except FakeAppError as e:
            return e

    err = await raise_and_catch()
    assert err.message == "async fail"
    assert err.context["async"] is True


@pytest.mark.asyncio
async def test_async_wrap_error():
    async def inner():
        raise ValueError("bad async")

    async def outer():
        try:
            await inner()
        except Exception as e:
            return FakeAppError.wrap(
                e,
                "ASYNC_WRAP",
                "wrapped async",
                ErrorCategory.EVENT,
                ErrorSeverity.ERROR,
            )

    err = await outer()
    assert err.code == "ASYNC_WRAP"
    assert err.context["original_exception"] == "ValueError"


def test_threaded_error_context_propagation():
    result = {}

    def thread_func():
        try:
            raise FakeValidationError("thread fail", {"thread": True})
        except FakeValidationError as e:
            result["err"] = e

    t = threading.Thread(target=thread_func)
    t.start()
    t.join()
    err = result["err"]
    assert err.message == "thread fail"
    assert err.context["thread"] is True


def test_error_context_merging_async_thread():
    # Simulate error context merging across async and thread
    result = {}

    async def async_func():
        return FakeAppError(
            ErrorCode.UNKNOWN_ERROR,
            "async",
            ErrorCategory.APPLICATION,
            ErrorSeverity.ERROR,
            context={"a": 1},
        )

    def thread_func():
        try:
            err = asyncio.run(async_func())
            result["err"] = FakeAppError(
                ErrorCode.UNKNOWN_ERROR,
                "thread fail",
                ErrorCategory.APPLICATION,
                ErrorSeverity.ERROR,
                context={"thread": 2},
            ).with_context(err.context)
        except Exception as e:
            result["exception"] = e

    t = threading.Thread(target=thread_func)
    t.start()
    t.join()
    if "exception" in result:
        raise result["exception"]
    assert "err" in result, f"Thread did not set 'err', got: {result}"
    err = result["err"]
    assert err.context["a"] == 1
    assert err.context["thread"] == 2
