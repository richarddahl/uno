"""
Event handler interfaces and registry for Uno's event sourcing system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Protocol, TypeVar, runtime_checkable
from collections.abc import Callable, Awaitable
from typing import TYPE_CHECKING

from uno.events.errors import EventHandlerError

if TYPE_CHECKING:
    from uno.events.config import EventsConfig
    from uno.events.context import EventHandlerContext
    from uno.logging.protocols import LoggerProtocol
    from uno.di.container import Container
    from uno.events.base_event import DomainEvent

T = TypeVar("T")


@runtime_checkable
class EventHandler(Protocol):
    """Protocol for event handlers."""

    async def handle(self, event: DomainEvent) -> None:
        """
        Handle the event.

        Args:
            event: The domain event to handle

        Raises:
            EventHandlerError: If the handler encounters an error
        """
        ...


class EventHandlerMiddleware(ABC):
    """Base class for event handler middleware."""

    @abstractmethod
    async def process(
        self,
        event: DomainEvent,
        next_middleware: Callable[[DomainEvent], None],
    ) -> None:
        """
        Process the event and pass it to the next middleware.

        Args:
            event: The domain event to process
            next_middleware: The next middleware to call

        Raises:
            EventHandlerError: If an error occurs during processing
        """
        ...


class EventHandlerRegistry:
    """Registry for event handlers and middleware."""

    def __init__(self, logger: LoggerProtocol, container: Container = None) -> None:
        """
        Initialize the registry.

        Args:
            logger: Logger for structured logging
            container: Optional DI container for resolving dependencies
        """
        self.logger = logger
        self.container = container
        self._handlers: dict[str, list[EventHandler]] = {}
        self._middleware: list[EventHandlerMiddleware] = []
        self._middleware_by_event_type: dict[str, list[EventHandlerMiddleware]] = {}

    def register_handler(
        self, event_type: str, handler: EventHandler | Callable
    ) -> None:
        """
        Register a handler for an event type.

        Args:
            event_type: The event type to handle
            handler: The handler to register (can be an EventHandler or a callable)
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        # Create an async adapter if the handler isn't already an EventHandler
        if not isinstance(handler, EventHandler):
            # Create an adapter that handles both sync and async callables
            handler_adapter = AsyncEventHandlerAdapter(handler, self.logger)
            self._handlers[event_type].append(handler_adapter)

    def register_middleware(self, middleware: EventHandlerMiddleware) -> None:
        """
        Register middleware.

        Args:
            middleware: The middleware to register
        """
        self._middleware.append(middleware)

    def register_middleware_for_event_type(
        self, event_type: str, middleware: EventHandlerMiddleware
    ) -> None:
        """
        Register middleware for a specific event type.

        Args:
            event_type: The event type to register middleware for
            middleware: The middleware to register
        """
        if event_type not in self._middleware_by_event_type:
            self._middleware_by_event_type[event_type] = []
        self._middleware_by_event_type[event_type].append(middleware)

    def register_middleware_from_factory(
        self, factory: Any, event_types: list[str] | None = None
    ) -> None:
        """
        Register middleware from a factory.

        Args:
            factory: The middleware factory to register middleware from
            event_types: Optional list of event types to register middleware for.
                         If None, middleware will be registered globally.
        """
        middleware = factory.create_middleware()
        if event_types:
            for event_type in event_types:
                self.register_middleware_for_event_type(event_type, middleware)
        else:
            self.register_middleware(middleware)

    def get_handlers(self, event_type: str) -> list[EventHandler]:
        """
        Get all handlers for an event type.

        Args:
            event_type: The event type to get handlers for

        Returns:
            List of handlers for the event type
        """
        return self._handlers.get(event_type, [])

    def get_middleware(self) -> list[EventHandlerMiddleware]:
        """
        Get all global middleware.

        Returns:
            List of middleware
        """
        return self._middleware

    def get_middleware_for_event_type(
        self, event_type: str
    ) -> list[EventHandlerMiddleware]:
        """
        Get middleware for a specific event type.

        Args:
            event_type: The event type to get middleware for

        Returns:
            List of middleware for the event type
        """
        return self._middleware_by_event_type.get(event_type, [])

    def build_middleware_chain(self, event_type: str) -> list[EventHandlerMiddleware]:
        """
        Build a middleware chain for an event type.

        This combines global middleware with event-specific middleware.

        Args:
            event_type: The event type to build a middleware chain for

        Returns:
            List of middleware in the chain
        """
        global_middleware = self.get_middleware()
        event_specific_middleware = self.get_middleware_for_event_type(event_type)
        return global_middleware + event_specific_middleware

    def clear(self) -> None:
        """Clear all handlers and middleware."""
        self._handlers.clear()
        self._middleware.clear()
        self._middleware_by_event_type.clear()

    def resolve_handler_dependencies(self, handler: Any) -> None:
        """
        Resolve handler dependencies using the DI container.

        Args:
            handler: The handler to resolve dependencies for

        Raises:
            ValueError: If no container is available
        """
        if not self.container:
            raise ValueError("No DI container available")
        self.container.resolve(handler)


class AsyncEventHandlerAdapter:
    """Adapter for converting sync/async callables into async event handlers."""

    def __init__(self, handler: Callable, logger: LoggerProtocol) -> None:
        self.handler = handler
        self.logger = logger

    async def handle(self, event: DomainEvent) -> None:
        """
        Handle the event by calling the wrapped handler.

        Args:
            event: The domain event to handle

        Raises:
            EventHandlerError: If the handler fails
        """
        try:
            result = self.handler(event)
            if isinstance(result, Awaitable):
                await result
        except Exception as e:
            self.logger.error(
                f"Handler failed for event {event.event_type}: {str(e)}",
                exc_info=True,
            )
            raise EventHandlerError(
                handler_name=self.handler.__name__,
                reason=f"Handler failed: {str(e)}",
            ) from e


class EventHandlerDecorator:
    """Decorator for event handlers."""

    def __init__(self, logger: LoggerProtocol) -> None:
        """
        Initialize the event handler decorator.

        Args:
            logger: The logger to use
        """
        self.logger = logger

    def __call__(self, handler: Callable[[DomainEvent], None | Awaitable[None]]) -> EventHandler:
        """
        Decorate the handler function.

        Args:
            handler: The handler function

        Returns:
            The decorated handler
        """
        return EventHandler(handler, self.logger)

    @classmethod
    def get_registry(cls, logger: LoggerProtocol) -> EventHandlerRegistry:
        """
        Get the registry for decorators.

        Args:
            logger: The logger to use

        Returns:
            The registry

        Raises:
            ValueError: If no registry has been set
        """
        if cls._registry is None:
            logger.error("No registry set for event handlers")
            raise ValueError("No registry set for event handlers")
        return cls._registry

    @classmethod
    def handles(cls, event_type: str) -> Callable:
        """
        Decorator to register a handler for an event type.

        Args:
            event_type: The event type to handle

        Returns:
            Decorator function
        """

        def decorator(handler_class: type[Any]) -> type[Any]:
            registry = cls.get_registry(logging.getLogger(__name__))
            registry.register_handler(event_type, handler_class)
            return handler_class

        return decorator

# Export the decorator function
handles = EventHandlerDecorator.handles
