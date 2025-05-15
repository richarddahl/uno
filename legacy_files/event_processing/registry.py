# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Registry implementation for event handlers.

This module provides a registry for managing event handlers with
an async-first approach and without DI container dependencies.
"""

from __future__ import annotations
import asyncio
import inspect
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, TypeVar, Type, cast, get_type_hints, Optional
from typing_extensions import TypeAlias, runtime_checkable

from uno.domain.protocols import DomainEventProtocol
from uno.events.protocols import (
    EventHandlerProtocol,
    EventRegistryProtocol,
)
from uno.logging.protocols import LoggerProtocol
from uno.events.errors import EventHandlerError

# Type variables for generic handlers
TEvent = TypeVar("TEvent", bound=DomainEventProtocol, contravariant=True)
TResult = TypeVar("TResult", covariant=True)

# Type alias for handler functions that can be either sync or async
HandlerFunc: TypeAlias = Callable[..., Any] | Callable[..., Awaitable[Any]]
HandlerType: TypeAlias = (
    HandlerFunc
    | Type[EventHandlerProtocol[Any, Any]]
    | EventHandlerProtocol[Any, Any]
    | type[object]
    | object
)

# Type alias for async event callbacks
EventCallback: TypeAlias = Callable[
    [DomainEventProtocol, dict[str, Any] | None], Awaitable[None]
]

# Type alias for handler registration
HandlerType: TypeAlias = (
    EventHandlerProtocol[DomainEventProtocol, Any]
    | Callable[[DomainEventProtocol, dict[str, Any] | None], Awaitable[None] | None]
    | type[EventHandlerProtocol[DomainEventProtocol, Any]]
)


@runtime_checkable
class EventHandlerRegistry:
    """
    Registry for event handlers that maps event types to their handlers.

    This class implements the EventRegistryProtocol through structural subtyping.
    It provides a thread-safe way to register and retrieve event handlers.
    """

    def __init__(self, logger: LoggerProtocol) -> None:
        """Initialize the registry.

        Args:
            logger: Logger for structured logging

        Raises:
            TypeError: If logger is not a valid LoggerProtocol implementation
        """
        if not isinstance(logger, LoggerProtocol):
            raise TypeError(
                f"logger must implement LoggerProtocol, got {type(logger).__name__}"
            )

        self._handlers: dict[
            type[DomainEventProtocol], list[EventHandlerProtocol[Any, Any]]
        ] = {}
        self._lock = asyncio.Lock()
        self.logger = logger

    async def register(self, event_type: str, handler: HandlerType) -> None:
        """
        Register a handler for an event type.

        Args:
            event_type: The event type name to register the handler for
            handler: The handler to register (can be callable, class, or EventHandlerProtocol)

        Raises:
            TypeError: If the handler is not a valid event handler
            ValueError: If the handler is already registered or event_type is invalid
            EventHandlerError: If registration fails for any other reason

        Note:
            For class-based handlers, the class must implement EventHandlerProtocol.
            For function handlers, they will be wrapped in an AsyncEventHandlerAdapter.
        """
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("event_type must be a non-empty string")

        handler_name = getattr(handler, "__name__", str(handler))

        try:
            async with self._lock:
                # Handle class-based handlers
                if isinstance(handler, type):
                    if not (hasattr(handler, "handle") and callable(handler.handle)):
                        raise TypeError(
                            f"Handler class {handler_name} must implement "
                            "EventHandlerProtocol with a 'handle' method"
                        )
                    # Create an instance of the handler if it's a class
                    handler_instance = handler()
                    await self._register_handler_instance(handler_instance)
                # Handle function-based handlers or protocol instances
                elif callable(handler):
                    if hasattr(handler, "handle") and callable(handler.handle):
                        await self._register_handler_instance(handler)
                    else:
                        await self._register_function_handler(handler, event_type)
                else:
                    raise TypeError(
                        f"Handler must be a class, callable, or implement EventHandlerProtocol, got {type(handler).__name__}"
                    )
        except (TypeError, ValueError) as e:
            # Re-raise validation errors directly
            raise
        except Exception as e:
            error_msg = f"Failed to register event handler: {e}"
            await self.logger.error(
                error_msg,
                handler=handler_name,
                event_type=event_type,
                error=str(e),
                exc_info=True,
            )
            raise EventHandlerError(
                handler_name=handler_name, reason=error_msg, event_type=event_type
            ) from e

    async def _register_handler_instance(
        self, handler: EventHandlerProtocol[DomainEventProtocol, Any] | object
    ) -> None:
        if not hasattr(handler, "handle") or not callable(handler.handle):
            raise TypeError("Handler must implement the handle() method")
        """Register a handler instance with the registry.

        Args:
            handler: The handler instance to register
            
        Raises:
            TypeError: If the handler is invalid or event type is incorrect
            ValueError: If the handler is already registered or invalid
            
        Note:
            This method is not thread-safe and should be called within a lock.
        """
        if not isinstance(handler, EventHandlerProtocol):
            raise TypeError(
                f"Handler must implement EventHandlerProtocol, got {type(handler).__name__}"
            )

        # Get the event type from the handler
        if not hasattr(handler, "event_type"):
            raise TypeError(
                f"Handler {type(handler).__name__} must have an 'event_type' attribute"
            )

        event_type = handler.event_type

        # Validate event_type
        if not isinstance(event_type, type):
            raise TypeError(
                f"Handler {type(handler).__name__} event_type must be a type, got {type(event_type).__name__}"
            )

        if not issubclass(event_type, DomainEventProtocol):
            raise TypeError(
                f"Handler {type(handler).__name__} event_type must be a "
                f"subclass of DomainEventProtocol, got {event_type.__name__}"
            )

        # Initialize the handlers list if needed
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        # Check for duplicate handlers
        if handler in self._handlers[event_type]:
            raise ValueError(
                f"Handler {type(handler).__name__} is already registered "
                f"for event type {event_type.__name__}"
            )

        self._handlers[event_type].append(handler)

    async def _register_function_handler(
        self, handler: Callable[..., Any], event_type_name: str
    ) -> None:
        if not callable(handler):
            raise TypeError("Handler must be callable")

        # Register the handler using the adapter
        adapter = AsyncEventHandlerAdapter(handler, self.logger, event_type_name)
        await self._register_handler_instance(adapter)
        """Register a function as an event handler.

        Args:
            handler: The function to register as a handler
            event_type_name: The event type name to register the handler for

        Raises:
            TypeError: If the function signature is invalid or event type cannot be determined
        """
        # Create an adapter for the function
        adapter = AsyncEventHandlerAdapter(handler, self.logger, event_type_name)

        try:
            # Get the event type from the handler's signature
            event_type = adapter.event_type

            # Register the adapter for the event type
            if event_type not in self._handlers:
                self._handlers[event_type] = []

            # Check for duplicate handlers
            if adapter in self._handlers[event_type]:
                raise ValueError(
                    f"Handler {adapter.handler_name} is already registered "
                    f"for event type {event_type.__name__}"
                )

            self._handlers[event_type].append(adapter)

        except Exception as e:
            await self.logger.error(
                "Failed to register function handler",
                handler=adapter.handler_name,
                event_type=event_type_name,
                error=str(e),
                exc_info=e,
            )
            raise

    async def get_handlers_for_event(
        self, event: DomainEventProtocol
    ) -> list[EventHandlerProtocol[Any, Any]]:
        if not isinstance(event, DomainEventProtocol):
            raise TypeError(f"Expected DomainEventProtocol, got {type(event).__name__}")
        """
        Get all handlers registered for the given event.

        Args:
            event: The domain event to get handlers for

        Returns:
            A list of handlers that can handle the event, ordered by specificity
            (most specific handlers first)
            
        Note:
            This method is thread-safe and returns a new list of handlers.
        """
        if not isinstance(event, DomainEventProtocol):
            raise TypeError(
                f"event must implement DomainEventProtocol, got {type(event).__name__}"
            )

        event_type = type(event)
        handlers: list[EventHandlerProtocol[DomainEventProtocol, Any]] = []

        async with self._lock:
            # Get exact matches first (most specific)
            if event_type in self._handlers:
                handlers.extend(self._handlers[event_type])

            # Check for superclass matches
            for handler_type, handler_list in self._handlers.items():
                if (
                    isinstance(handler_type, type)
                    and event_type is not handler_type
                    and issubclass(event_type, handler_type)
                ):
                    handlers.extend(handler_list)

        return handlers

    async def clear(self) -> None:
        """
        Clear all registered handlers.

        Note:
            This operation is thread-safe and will block until all current operations complete.
        """
        async with self._lock:
            self._handlers.clear()


class AsyncEventHandlerAdapter(EventHandlerProtocol[DomainEventProtocol, None]):
    """
    Adapter for converting callables into async event handlers.

    This adapter automatically detects whether the provided function is synchronous
    or asynchronous and wraps it appropriately to ensure all handlers present a
    consistent async interface to the event system.
    """

    def __init__(
        self,
        handler_func: Callable[..., Any],
        logger: LoggerProtocol,
        event_type_name: str | None = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            handler_func: The function to adapt (can be sync or async)
            logger: Logger for structured logging
            event_type_name: Optional event type name for logging
        """
        self.handler_func = handler_func
        self.logger = logger
        self.is_async = inspect.iscoroutinefunction(handler_func)
        self._event_type_name = event_type_name
        self._event_type: type[DomainEventProtocol] | None = None

        # Store the handler name for logging
        self.handler_name = getattr(
            handler_func,
            "__qualname__",
            getattr(handler_func, "__name__", str(handler_func)),
        )

    @property
    def event_type(self) -> type[DomainEventProtocol]:
        """Get the event type this handler is registered for."""
        if self._event_type is None:
            # First try to get from function signature
            try:
                sig = inspect.signature(self.handler_func)
                params = list(sig.parameters.values())

                if len(params) >= 1:
                    param = params[0]
                    param_type = param.annotation

                    # Handle string annotations
                    if isinstance(param_type, str):
                        module = inspect.getmodule(self.handler_func)
                        if module is not None and hasattr(module, param_type):
                            param_type = getattr(module, param_type)

                    if (
                        inspect.isclass(param_type)
                        and param_type is not inspect.Parameter.empty
                        and issubclass(param_type, DomainEventProtocol)
                    ):
                        self._event_type = param_type
                        return self._event_type
            except Exception:
                pass

            # If not found in signature, try to get by name
            if self._event_type_name:
                try:
                    module = inspect.getmodule(self.handler_func)
                    if module and hasattr(module, self._event_type_name):
                        potential_type = getattr(module, self._event_type_name)
                        if inspect.isclass(potential_type) and issubclass(
                            potential_type, DomainEventProtocol
                        ):
                            self._event_type = potential_type
                            return self._event_type
                except Exception:
                    pass

            # If still not found, try to infer from handler name
            if self._event_type is None and hasattr(self.handler_func, "__name__"):
                handler_name = self.handler_func.__name__.lower()
                if handler_name.endswith("handler") and len(handler_name) > 7:
                    event_name = handler_name[:-7]  # Remove 'handler' suffix
                    try:
                        module = inspect.getmodule(self.handler_func)
                        if module and hasattr(module, event_name):
                            potential_type = getattr(module, event_name)
                            if inspect.isclass(potential_type) and issubclass(
                                potential_type, DomainEventProtocol
                            ):
                                self._event_type = potential_type
                                return self._event_type
                    except Exception:
                        pass

            raise RuntimeError(
                f"Could not determine event type for handler {self.handler_name}. "
                f"Please specify the event type explicitly or ensure the handler's "
                f"first parameter is annotated with the event type."
            )

        return self._event_type

    async def handle(
        self, event: DomainEventProtocol, metadata: dict[str, Any] | None = None
    ) -> None:
        if not isinstance(event, DomainEventProtocol):
            raise TypeError(f"Expected DomainEventProtocol, got {type(event).__name__}")
        """
        Handle the event by calling the wrapped function.

        Args:
            event: The domain event to handle
            metadata: Optional metadata for the event

        Raises:
            EventHandlerError: If the handler fails
        """
        try:
            if self.is_async:
                if metadata is not None:
                    await self.handler_func(event, metadata)
                else:
                    await self.handler_func(event)
            else:
                # Run sync function in a thread pool
                loop = asyncio.get_running_loop()
                if metadata is not None:
                    await loop.run_in_executor(None, self.handler_func, event, metadata)
                else:
                    await loop.run_in_executor(None, self.handler_func, event)
        except Exception as e:
            error_msg = f"Error in event handler {self.handler_name}: {e}"
            await self.logger.error(
                error_msg,
                handler=self.handler_name,
                event_type=type(event).__name__,
                error=str(e),
                exc_info=True,
            )
            raise EventHandlerError(
                message=f"Error in handler {self.handler_name} for event {event.__class__.__name__}",
                event_type=event.__class__.__name__,
            ) from e


async def register_event_handler(
    event_type: str,
    handler: HandlerType,
    registry: EventRegistryProtocol,
) -> None:
    """Register an event handler with the registry.

    Args:
        event_type: The event type to handle
        handler: The handler to register (can be a callable or EventHandlerProtocol)
        registry: The registry to register the handler with

    Raises:
        TypeError: If the handler is not a valid event handler
        ValueError: If the handler is already registered
    """
    await registry.register(event_type, handler)
