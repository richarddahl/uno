# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Error context enrichment utilities for the Uno framework.

This module provides utilities for enriching errors with contextual information
as they propagate through the application. Context enrichment helps with
debugging, tracing, and correlating errors across different components.
"""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import inspect
import threading
from collections.abc import AsyncGenerator, Callable, Generator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from typing import (
    Any,
    TypeVar,
    cast,
)

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError

# =============================================================================
# Context carriers - Global, thread, and async contexts
# =============================================================================

# Global error context (application-wide)
_GLOBAL_ERROR_CONTEXT: dict[str, Any] = {}

# Thread-local error context
_THREAD_LOCAL = threading.local()

# Async context variable for errors
_ASYNC_ERROR_CONTEXT_VAR = contextvars.ContextVar[dict[str, Any]](
    "async_error_context", default={}
)

# =============================================================================
# Context management functions
# =============================================================================


def add_global_context(key: str, value: Any) -> None:
    """Add a key-value pair to the global error context.

    Global context values will be added to all errors.

    Args:
        key: The context key
        value: The context value
    """
    _GLOBAL_ERROR_CONTEXT[key] = value


def remove_global_context(key: str) -> None:
    """Remove a key from the global error context.

    Args:
        key: The context key to remove
    """
    if key in _GLOBAL_ERROR_CONTEXT:
        del _GLOBAL_ERROR_CONTEXT[key]


def get_global_context() -> dict[str, Any]:
    """Get the current global error context dictionary.

    Returns:
        A copy of the global error context
    """
    return _GLOBAL_ERROR_CONTEXT.copy()


def clear_global_context() -> None:
    """Clear all values from the global error context."""
    _GLOBAL_ERROR_CONTEXT.clear()


def add_thread_context(key: str, value: Any) -> None:
    """Add a key-value pair to the thread-local error context.

    Thread context values will be added to all errors raised in the current thread.

    Args:
        key: The context key
        value: The context value
    """
    if not hasattr(_THREAD_LOCAL, "error_context"):
        _THREAD_LOCAL.error_context = {}
    _THREAD_LOCAL.error_context[key] = value


def remove_thread_context(key: str) -> None:
    """Remove a key from the thread-local error context.

    Args:
        key: The context key to remove
    """
    if hasattr(_THREAD_LOCAL, "error_context") and key in _THREAD_LOCAL.error_context:
        del _THREAD_LOCAL.error_context[key]


def get_thread_context() -> dict[str, Any]:
    """Get the current thread-local error context dictionary.

    Returns:
        A copy of the thread-local error context
    """
    if not hasattr(_THREAD_LOCAL, "error_context"):
        _THREAD_LOCAL.error_context = {}
    return _THREAD_LOCAL.error_context.copy()


def clear_thread_context() -> None:
    """Clear all values from the thread-local error context."""
    if hasattr(_THREAD_LOCAL, "error_context"):
        _THREAD_LOCAL.error_context.clear()


def add_async_context(key: str, value: Any) -> contextvars.Token:
    """Add a key-value pair to the async error context.

    Async context values will be added to all errors raised in the current async context.

    Args:
        key: The context key
        value: The context value

    Returns:
        A token that can be used to reset the context
    """
    ctx = _ASYNC_ERROR_CONTEXT_VAR.get().copy()
    ctx[key] = value
    return _ASYNC_ERROR_CONTEXT_VAR.set(ctx)


def reset_async_context(token: contextvars.Token) -> None:
    """Reset the async error context to its previous state.

    Args:
        token: The token returned by add_async_context
    """
    _ASYNC_ERROR_CONTEXT_VAR.reset(token)


def remove_async_context(key: str) -> contextvars.Token:
    """Remove a key from the async error context.

    Args:
        key: The context key to remove

    Returns:
        A token that can be used to reset the context
    """
    ctx = _ASYNC_ERROR_CONTEXT_VAR.get().copy()
    if key in ctx:
        del ctx[key]
    return _ASYNC_ERROR_CONTEXT_VAR.set(ctx)


def get_async_context() -> dict[str, Any]:
    """Get the current async error context dictionary.

    Returns:
        A copy of the async error context
    """
    return _ASYNC_ERROR_CONTEXT_VAR.get().copy()


def clear_async_context() -> contextvars.Token:
    """Clear all values from the async error context.

    Returns:
        A token that can be used to reset the context
    """
    return _ASYNC_ERROR_CONTEXT_VAR.set({})


# =============================================================================
# Context retrieval and enrichment
# =============================================================================


def get_current_context() -> dict[str, Any]:
    """Get the combined context from all sources (global, thread, async).

    Returns:
        A dictionary with the combined context
    """
    # Start with global context
    context = get_global_context()

    # Add thread-local context, overriding global values if there are conflicts
    context.update(get_thread_context())

    # Add async context, overriding previous values if there are conflicts
    context.update(get_async_context())

    return context


def enrich_error(error: UnoError) -> UnoError:
    """Enrich an error with the current context.

    Args:
        error: The error to enrich

    Returns:
        The enriched error
    """
    # Get the current context
    context = get_current_context()

    # Add all context values to the error
    for key, value in context.items():
        # Don't override existing context keys
        if key not in error.context:
            error.add_context(key, value)

    return error


# =============================================================================
# Context managers
# =============================================================================


@dataclass
class ErrorContext:
    """Context manager for adding error context.

    This class provides a context manager that adds context to any errors raised
    within its scope. It supports both synchronous and asynchronous contexts.

    Example:
        ```python
        # Synchronous usage
        with ErrorContext(request_id="123", user_id="456"):
            # Do something that might raise an error

        # Asynchronous usage
        async with ErrorContext(request_id="123", user_id="456"):
            # Do something asynchronously that might raise an error
        ```
    """

    __context_values: dict[str, Any] = field(default_factory=dict)
    __async_tokens: list[contextvars.Token] = field(default_factory=list)

    def __init__(self, **context: Any):
        """Initialize the error context.

        Args:
            **context: Key-value pairs to add to the context
        """
        self.__context_values = context
        self.__async_tokens = []

    def __enter__(self) -> ErrorContext:
        """Enter the context manager.

        Returns:
            The context manager instance
        """
        # Add context to thread local
        for key, value in self.__context_values.items():
            add_thread_context(key, value)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager.

        Args:
            exc_type: The exception type, if raised
            exc_val: The exception value, if raised
            exc_tb: The exception traceback, if raised
        """
        # If an error was raised, enrich it with context
        if exc_val is not None and isinstance(exc_val, UnoError):
            enrich_error(exc_val)

        # Clean up thread context
        for key in self.__context_values:
            remove_thread_context(key)

    async def __aenter__(self) -> ErrorContext:
        """Enter the async context manager.

        Returns:
            The context manager instance
        """
        # Add context to async context
        for key, value in self.__context_values.items():
            token = add_async_context(key, value)
            self.__async_tokens.append(token)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager.

        Args:
            exc_type: The exception type, if raised
            exc_val: The exception value, if raised
            exc_tb: The exception traceback, if raised
        """
        # If an error was raised, enrich it with context
        if exc_val is not None and isinstance(exc_val, UnoError):
            enrich_error(exc_val)

        # Reset async context
        for token in reversed(self.__async_tokens):
            reset_async_context(token)
        self.__async_tokens.clear()


# =============================================================================
# Decorators
# =============================================================================

F = TypeVar("F", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Any])


def with_error_context(**context: Any) -> Callable[[F], F]:
    """Decorator for adding error context to functions.

    This decorator adds context to any errors raised within the decorated function.
    It supports both synchronous and asynchronous functions.

    Example:
        ```python
        @with_error_context(component="user_service")
        def get_user(user_id):
            # Do something that might raise an error

        @with_error_context(component="auth_service")
        async def authenticate_user(username, password):
            # Do something asynchronously that might raise an error
        ```

    Args:
        **context: Key-value pairs to add to the context

    Returns:
        The decorated function
    """

    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                async with ErrorContext(**context):
                    return await func(*args, **kwargs)

            return cast(F, async_wrapper)
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with ErrorContext(**context):
                    return func(*args, **kwargs)

            return cast(F, sync_wrapper)

    return decorator


def with_dynamic_error_context(
    context_factory: Callable[..., dict[str, Any]],
) -> Callable[[F], F]:
    """Decorator for adding dynamic error context to functions.

    This decorator adds context to any errors raised within the decorated function,
    where the context is determined dynamically from the function arguments.

    Example:
        ```python
        def get_user_context(user_id, **kwargs):
            return {"user_id": user_id}

        @with_dynamic_error_context(get_user_context)
        def get_user(user_id):
            # Do something that might raise an error
        ```

    Args:
        context_factory: A function that takes the same arguments as the decorated
            function and returns a dictionary of context values

    Returns:
        The decorated function
    """

    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Get signature of the decorated function
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                # Generate context
                ctx = context_factory(**bound_args.arguments)

                async with ErrorContext(**ctx):
                    return await func(*args, **kwargs)

            return cast(F, async_wrapper)
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Get signature of the decorated function
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                # Generate context
                ctx = context_factory(**bound_args.arguments)

                with ErrorContext(**ctx):
                    return func(*args, **kwargs)

            return cast(F, sync_wrapper)

    return decorator


def capture_error_context(func: F) -> F:
    """Decorator for capturing the current context to any raised errors.

    This decorator adds the current context to any errors raised within the
    decorated function, ensuring that errors have the most up-to-date context.

    Example:
        ```python
        @capture_error_context
        def risky_operation():
            # Do something that might raise an error
        ```

    Args:
        func: The function to decorate

    Returns:
        The decorated function
    """
    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except UnoError as e:
                raise enrich_error(e)
            except Exception:
                # Don't handle non-UnoError exceptions
                raise

        return cast(F, async_wrapper)
    else:

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except UnoError as e:
                raise enrich_error(e)
            except Exception:
                # Don't handle non-UnoError exceptions
                raise

        return cast(F, sync_wrapper)


# =============================================================================
# Context registries for named contexts
# =============================================================================


class ContextRegistry:
    """Registry for named error contexts.

    This class provides a way to register and retrieve named error contexts,
    which can be useful for standardizing context across an application.

    Example:
        ```python
        # Create a registry
        registry = ContextRegistry()

        # Register a context
        registry.register("api_request", user_id=None, request_id=None)

        # Use the context
        with registry.get_context("api_request", user_id="123", request_id="456"):
            # Do something that might raise an error
        ```
    """

    def __init__(self) -> None:
        """Initialize the context registry."""
        self._contexts: dict[str, set[str]] = {}

    def register(self, name: str, **keys_with_defaults: Any) -> None:
        """Register a named context with its keys and default values.

        Args:
            name: The name of the context
            **keys_with_defaults: The keys and their default values
        """
        self._contexts[name] = set(keys_with_defaults.keys())

    def get_context(self, name: str, **values: Any) -> ErrorContext:
        """Get a named context with values.

        Args:
            name: The name of the context
            **values: The values for the context keys

        Returns:
            An ErrorContext instance with the specified values

        Raises:
            ValueError: If the context name is not registered or if there are
                unknown keys in the values
        """
        if name not in self._contexts:
            raise ValueError(f"Context '{name}' is not registered")

        # Check for unknown keys
        unknown_keys = set(values.keys()) - self._contexts[name]
        if unknown_keys:
            raise ValueError(f"Unknown keys for context '{name}': {unknown_keys}")

        return ErrorContext(**values)

    def with_context(self, name: str, **values: Any) -> Callable[[F], F]:
        """Decorator for adding a named context to functions.

        Args:
            name: The name of the context
            **values: The values for the context keys

        Returns:
            A decorator that adds the named context to the decorated function

        Raises:
            ValueError: If the context name is not registered or if there are
                unknown keys in the values
        """
        if name not in self._contexts:
            raise ValueError(f"Context '{name}' is not registered")

        # Check for unknown keys
        unknown_keys = set(values.keys()) - self._contexts[name]
        if unknown_keys:
            raise ValueError(f"Unknown keys for context '{name}': {unknown_keys}")

        return with_error_context(**values)


# Create a default registry for application use
default_registry = ContextRegistry()


# =============================================================================
# Standard contexts
# =============================================================================

# Register standard contexts
default_registry.register(
    "request",
    request_id=None,
    client_ip=None,
    http_method=None,
    path=None,
    user_agent=None,
)

default_registry.register(
    "user",
    user_id=None,
    username=None,
    tenant_id=None,
)

default_registry.register(
    "database",
    database_name=None,
    operation=None,
    table=None,
)

default_registry.register(
    "service",
    service_name=None,
    method_name=None,
)

default_registry.register(
    "job",
    job_id=None,
    job_type=None,
    scheduled_at=None,
)

default_registry.register(
    "transaction",
    transaction_id=None,
    payment_provider=None,
    payment_method=None,
    amount=None,
    currency=None,
)

default_registry.register(
    "performance",
    duration_ms=None,
    resource_usage=None,
)


# =============================================================================
# Automatic context propagation between sync and async code
# =============================================================================


class ErrorContextBridge:
    """Bridge for propagating error context between sync and async code.

    This class provides a way to propagate error context between synchronous and
    asynchronous code, which can be useful when using libraries that mix these
    paradigms.

    Example:
        ```python
        # Create a bridge
        bridge = ErrorContextBridge()

        # Add context in synchronous code
        bridge.add("request_id", "123")

        async def async_function():
            # Apply bridge context in async code
            async with bridge.apply():
                # Context is now available in async code
                # ...
        ```
    """

    def __init__(self) -> None:
        """Initialize the error context bridge."""
        self._context: dict[str, Any] = {}

    def add(self, key: str, value: Any) -> None:
        """Add a key-value pair to the bridge context.

        Args:
            key: The context key
            value: The context value
        """
        self._context[key] = value

    def remove(self, key: str) -> None:
        """Remove a key from the bridge context.

        Args:
            key: The context key to remove
        """
        if key in self._context:
            del self._context[key]

    def clear(self) -> None:
        """Clear all values from the bridge context."""
        self._context.clear()

    def get(self) -> dict[str, Any]:
        """Get the current bridge context dictionary.

        Returns:
            A copy of the bridge context
        """
        return self._context.copy()

    @contextlib.contextmanager
    def apply(self) -> Generator[None, None, None]:
        """Apply the bridge context to the current thread context.

        This context manager applies the bridge context to the current thread
        context, and cleans it up when the context manager exits.

        Yields:
            Nothing
        """
        # Save old values to restore later
        old_values = {}
        for key in self._context:
            if (
                hasattr(_THREAD_LOCAL, "error_context")
                and key in _THREAD_LOCAL.error_context
            ):
                old_values[key] = _THREAD_LOCAL.error_context[key]

        # Apply bridge context to thread context
        for key, value in self._context.items():
            add_thread_context(key, value)

        try:
            yield
        finally:
            # Restore old values
            for key in self._context:
                if key in old_values:
                    add_thread_context(key, old_values[key])
                else:
                    remove_thread_context(key)

    async def apply_async(self) -> AsyncGenerator[None, None]:
        """Apply the bridge context to the current async context.

        This async context manager applies the bridge context to the current
        async context, and cleans it up when the context manager exits.

        Yields:
            Nothing
        """
        tokens = []
        try:
            # Apply bridge context to async context
            for key, value in self._context.items():
                token = add_async_context(key, value)
                tokens.append(token)

            yield
        finally:
            # Reset async context
            for token in reversed(tokens):
                reset_async_context(token)


# Create a default bridge for application use
default_bridge = ErrorContextBridge()


# =============================================================================
# Middleware support
# =============================================================================


class ErrorContextMiddleware:
    """Middleware for adding error context to HTTP requests.

    This class provides middleware that adds standard context values like
    request_id, client_ip, etc. to the error context for the duration of
    an HTTP request.

    This is an abstract class that should be subclassed for specific web
    frameworks like FastAPI, Starlette, etc.
    """

    def __init__(
        self,
        include_headers: bool = True,
        include_body: bool = False,
        include_query_params: bool = True,
        mask_sensitive_fields: bool = True,
        sensitive_fields: set[str] | None = None,
    ):
        """Initialize the error context middleware.

        Args:
            include_headers: Whether to include request headers in the context
            include_body: Whether to include request body in the context
            include_query_params: Whether to include query parameters in the context
            mask_sensitive_fields: Whether to mask sensitive fields
            sensitive_fields: Set of field names to mask
        """
        self.include_headers = include_headers
        self.include_body = include_body
        self.include_query_params = include_query_params
        self.mask_sensitive_fields = mask_sensitive_fields

        # Default sensitive fields to mask
        self.sensitive_fields = sensitive_fields or {
            "password",
            "token",
            "secret",
            "api_key",
            "apikey",
            "key",
            "authorization",
            "auth",
            "credit_card",
            "creditcard",
            "card",
            "ssn",
            "social_security",
            "socialsecurity",
        }

    def mask_value(self, key: str, value: Any) -> Any:
        """Mask a sensitive value.

        Args:
            key: The key for the value
            value: The value to potentially mask

        Returns:
            The masked value if the key is sensitive, otherwise the original value
        """
        key_lower = key.lower()
        if self.mask_sensitive_fields and any(
            sensitive in key_lower for sensitive in self.sensitive_fields
        ):
            if isinstance(value, str):
                if len(value) > 6:
                    # Mask middle of the string
                    return value[:3] + "***" + value[-3:]
                else:
                    # Mask entire string if too short
                    return "******"
            else:
                # Just return a placeholder for non-string values
                return "******"
        return value
