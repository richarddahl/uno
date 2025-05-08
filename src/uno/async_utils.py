"""
Asynchronous utilities for working with async code in the event system.

This module provides utility functions and adapter classes for working with
async code in a consistent way across the event system. It handles both
synchronous and asynchronous event handlers and provides a unified interface.
"""

import inspect
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypeVar

from uno.errors.result import Failure, Result
from uno.events.context import EventHandlerContext
from uno.infrastructure.logging.logger import LoggerService

# Type variables for generic function signatures
T = TypeVar("T")
HandlerFunc = TypeVar(
    "HandlerFunc",
    bound=Callable[
        [EventHandlerContext],
        Result[Any, Exception] | Awaitable[Result[Any, Exception]],
    ],
)


def is_async_callable(obj: Any) -> bool:
    """Determine if an object is an async callable.

    Args:
        obj: The object to check

    Returns:
        True if the object is an async callable, False otherwise
    """
    # Direct check for coroutine functions
    if inspect.iscoroutinefunction(obj):
        return True

    # Check methods
    if inspect.ismethod(obj):
        return inspect.iscoroutinefunction(obj.__func__)

    # Check if it's a callable object with an async __call__ method
    if callable(obj):
        if hasattr(obj.__call__, "__func__"):
            # For bound methods
            return inspect.iscoroutinefunction(obj.__call__.__func__)
        return inspect.iscoroutinefunction(obj.__call__)

    return False


async def to_async(
    func: Callable[..., T | Awaitable[T]], *args: Any, **kwargs: Any
) -> T:
    """
    Convert a callable to an async callable.

    This allows both sync and async callables to be used consistently in async code.

    Args:
        func: The callable to convert
        *args: Arguments to pass to the callable
        **kwargs: Keyword arguments to pass to the callable

    Returns:
        The result of the callable
    """
    if is_async_callable(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


async def to_async_result(
    func: Callable[..., Result[T, Exception] | Awaitable[Result[T, Exception]]],
    *args: Any,
    **kwargs: Any,
) -> Result[T, Exception]:
    """
    Convert a callable that returns a Result to an async callable.

    This allows both sync and async Result-returning callables to be used consistently.

    Args:
        func: The callable to convert
        *args: Arguments to pass to the callable
        **kwargs: Keyword arguments to pass to the callable

    Returns:
        The Result from the callable
    """
    try:
        if is_async_callable(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    except Exception as e:
        return Failure(e)


class EventHandlerProtocol(Protocol):
    """Protocol defining the interface for event handlers."""

    async def handle(self, context: EventHandlerContext) -> Result[Any, Exception]:
        """Handle an event."""
        ...


class FunctionHandlerAdapter:
    """Adapter that wraps a function to make it compatible with the EventHandler interface."""

    def __init__(
        self,
        func: Callable[
            [EventHandlerContext],
            Result[Any, Exception] | Awaitable[Result[Any, Exception]],
        ],
        event_type: str,
    ):
        """Initialize the adapter with the function to wrap.

        Args:
            func: The function to adapt (sync or async)
            event_type: The type of event this handler processes
        """
        self.func = func
        self._event_type = event_type
        self._is_event_handler = True

    async def handle(self, context: EventHandlerContext) -> Result[Any, Exception]:
        """Delegate to the wrapped function, handling both sync and async functions.

        Args:
            context: The event context to pass to the function

        Returns:
            The result of handling the event
        """
        try:
            if is_async_callable(self.func):
                # Async function
                return await self.func(context)
            else:
                # Sync function
                return self.func(context)
        except Exception as e:
            return Failure(e)


class AsyncEventHandlerAdapter:
    """Adapter that ensures all event handlers present an async interface.

    This adapter wraps both sync and async handlers to ensure a consistent
    async interface is presented to the event bus.
    """

    def __init__(self, handler: Any, logger: LoggerService | None = None):
        """
        Initialize the adapter.

        Args:
            handler: The handler to adapt
            logger: Optional logger
        """
        self.handler = handler
        self.logger = logger

        # Determine if the handler is async
        self._is_async = False

        if hasattr(handler, "handle"):
            self._is_async = is_async_callable(handler.handle)
        else:
            self._is_async = is_async_callable(handler)

    async def handle(self, context: EventHandlerContext) -> Result[Any, Exception]:
        """
        Handle an event.

        Args:
            context: The event handler context

        Returns:
            Result with a value on success, or an error
        """
        try:
            if hasattr(self.handler, "handle"):
                # Object with handle method
                return await to_async_result(self.handler.handle, context)
            else:
                # Function handler
                return await to_async_result(self.handler, context)
        except Exception as e:
            if self.logger:
                self.logger.structured_log(
                    "ERROR",
                    f"Error handling event: {e}",
                    name="uno.events.async_adapter",
                    error=e,
                    event_id=context.event.event_id,
                    event_type=context.event.event_type,
                )
            return Failure(e)

    async def __call__(self, event: Any) -> Result[Any, Exception]:
        """Allow the adapter to be directly awaitable by the event bus, passing event as context."""
        context = (
            event
            if isinstance(event, EventHandlerContext)
            else EventHandlerContext(event=event)
        )
        return await self.handle(context)
