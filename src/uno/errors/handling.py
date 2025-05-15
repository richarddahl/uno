# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""Asynchronous error handling utilities for the Uno framework.

This module provides utilities for handling errors in asynchronous code,
including async context managers, decorators, and middleware for error handling
in async applications.
"""

from __future__ import annotations

import asyncio
import inspect
import sys
from collections.abc import AsyncIterator, Awaitable, Callable, Generator
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, TypeVar, cast

from typing_extensions import ParamSpec, TypeGuard

from uno.errors.base import UnoError
from uno.errors.context import ErrorContext
from uno.errors.logging import error_logger

T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")


def is_coroutine_function(
    func: Callable[..., Any],
) -> TypeGuard[Callable[..., Awaitable[Any]]]:
    """Check if a function is a coroutine function.

    Args:
        func: The function to check

    Returns:
        True if the function is a coroutine function, False otherwise
    """
    return asyncio.iscoroutinefunction(func) or (
        callable(func) and asyncio.iscoroutinefunction(getattr(func, "__call__", None))
    )


class AsyncErrorContext(ErrorContext):
    """Asynchronous context manager for error handling with context."""

    async def __aenter__(self) -> AsyncErrorContext:
        """Enter the async context manager.

        Returns:
            The context manager instance
        """
        self.__enter__()
        return self

    async def __aexit__(
        self, exc_type: type[Exception], exc_val: Exception, exc_tb: Any
    ) -> None:
        """Exit the async context manager.

        Args:
            exc_type: The exception type, if raised
            exc_val: The exception value, if raised
            exc_tb: The exception traceback, if raised
        """
        self.__exit__(exc_type, exc_val, exc_tb)


def async_error_handler(
    func: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R | None]]:
    """Decorator for handling errors in async functions.

    Args:
        func: The async function to wrap

    Returns:
        A wrapped function that handles errors
    """
    if not is_coroutine_function(func):
        raise TypeError("Function must be a coroutine function")

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_logger.exception(
                f"Error in async function {func.__name__}",
                error=e,
                function=func.__name__,
                module=func.__module__,
            )
            return None

    return wrapper


@asynccontextmanager
async def async_error_context(**context: Any) -> AsyncIterator[None]:
    """Async context manager for error handling with context.

    Args:
        **context: Context to add to any errors

    Yields:
        None
    """
    with ErrorContext(**context):
        try:
            yield
        except Exception as e:
            error_logger.exception("Error in async context", error=e, **context)
            raise


def async_retry(
    max_attempts: int = 3,
    delay: float = 0.1,
    backoff: float = 2.0,
    exceptions: type[Exception] | tuple[type[Exception], ...] = Exception,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R | None]]]:
    """Decorator for retrying async functions on failure.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff: Multiplier for delay between attempts
        exceptions: Exception types to catch and retry on

    Returns:
        A decorator that adds retry behavior to async functions
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R | None]]:
        if not is_coroutine_function(func):
            raise TypeError("Function must be a coroutine function")

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        error_logger.error(
                            f"Max retries ({max_attempts}) exceeded for {func.__name__}",
                            error=e,
                            attempt=attempt,
                            max_attempts=max_attempts,
                        )
                        raise

                    error_logger.warning(
                        f"Retrying {func.__name__} (attempt {attempt}/{max_attempts})",
                        error=e,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay=current_delay,
                    )

                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # This should never be reached due to the raise above
            return None  # pragma: no cover

        return wrapper

    return decorator


class AsyncErrorHandler:
    """Base class for async error handlers."""

    async def handle(self, error: Exception) -> None:
        """Handle an error asynchronously.

        Args:
            error: The error to handle
        """
        raise NotImplementedError

    async def __call__(self, error: Exception) -> None:
        """Handle an error asynchronously.

        Args:
            error: The error to handle
        """
        return await self.handle(error)


class AsyncErrorMiddleware:
    """Middleware for handling errors in async applications."""

    def __init__(self, handlers: list[AsyncErrorHandler] | None = None):
        """Initialize the middleware.

        Args:
            handlers: List of error handlers to use
        """
        self.handlers = handlers or []

    async def handle_error(self, error: Exception) -> None:
        """Handle an error using all registered handlers.

        Args:
            error: The error to handle
        """
        for handler in self.handlers:
            try:
                await handler(error)
            except Exception as e:
                error_logger.exception(
                    f"Error in async error handler {handler.__class__.__name__}",
                    error=e,
                    original_error=str(error),
                )

    def add_handler(self, handler: AsyncErrorHandler) -> None:
        """Add an error handler.

        Args:
            handler: The error handler to add
        """
        self.handlers.append(handler)

    def remove_handler(self, handler: AsyncErrorHandler) -> None:
        """Remove an error handler.

        Args:
            handler: The error handler to remove
        """
        self.handlers = [h for h in self.handlers if h != handler]

    def __call__(self, error: Exception) -> Awaitable[None]:
        """Handle an error using all registered handlers.

        Args:
            error: The error to handle

        Returns:
            An awaitable that resolves when all handlers have completed
        """
        return self.handle_error(error)


async def run_with_timeout(
    coro: Awaitable[T],
    timeout: float,
    timeout_error: type[Exception] = asyncio.TimeoutError,
) -> T:
    """Run a coroutine with a timeout.

    Args:
        coro: The coroutine to run
        timeout: Timeout in seconds
        timeout_error: Exception to raise on timeout

    Returns:
        The result of the coroutine

    Raises:
        timeout_error: If the coroutine does not complete within the timeout
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError as e:
        raise timeout_error(f"Operation timed out after {timeout} seconds") from e


def async_error_boundary(
    error_handler: Callable[[Exception], Awaitable[None]] | None = None,
    **context: Any,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R | None]]]:
    """Decorator for creating an async error boundary.

    Args:
        error_handler: Optional async error handler function
        **context: Context to add to any errors

    Returns:
        A decorator that creates an error boundary
    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R | None]]:
        if not is_coroutine_function(func):
            raise TypeError("Function must be a coroutine function")

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | None:
            try:
                with ErrorContext(**context):
                    return await func(*args, **kwargs)
            except Exception as e:
                if error_handler is not None:
                    try:
                        await error_handler(e)
                    except Exception as handler_error:
                        error_logger.exception(
                            "Error in async error handler",
                            error=handler_error,
                            original_error=str(e),
                        )
                raise

        return wrapper

    return decorator
