"""
Event handlers and middleware for the event sourcing system.

This module provides a framework for handling domain events, including
automatic handler discovery and middleware for cross-cutting concerns.
"""

import importlib
import inspect
import pkgutil
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from types import ModuleType
from typing import Any, ClassVar, TypeVar, cast

from uno.errors.result import Failure, Result, Success
from uno.events.context import EventHandlerContext
from uno.events.base_event import DomainEvent
from uno.infrastructure.logging.logger import LoggerService
from uno.infrastructure.logging.logger import LoggingConfig

# Import AsyncEventHandlerAdapter - import here to avoid circular imports
from uno.async_utils import (
    AsyncEventHandlerAdapter,
    FunctionHandlerAdapter,
    EventHandlerProtocol,
)


T = TypeVar("T")


# EventHandlerContext is now defined in context.py


class EventHandler(ABC):
    """Base class for event handlers."""

    @abstractmethod
    async def handle(self, context: EventHandlerContext) -> Result[Any, Exception]:
        """
        Handle the event.

        Args:
            context: The event handler context

        Returns:
            Result with a value on success, or an error
        """
        pass


class EventHandlerMiddleware(ABC):
    """Base class for event handler middleware."""

    @abstractmethod
    async def process(
        self,
        context: EventHandlerContext,
        next_middleware: Callable[[EventHandlerContext], Result[Any, Exception]],
    ) -> Result[Any, Exception]:
        """
        Process the event and pass it to the next middleware.

        Args:
            context: The event handler context
            next_middleware: The next middleware to call

        Returns:
            Result with a value on success, or an error
        """
        pass


class EventHandlerRegistry:
    """Registry for event handlers and middleware. Requires DI-injected LoggerService."""

    def __init__(self, logger: LoggerService) -> None:
        """
        Initialize the registry.

        Args:
            logger: DI-injected LoggerService instance
        """
        self.logger = logger
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

            self.logger.structured_log(
                "DEBUG",
                f"Registered callable handler for event type {event_type} (wrapped with AsyncEventHandlerAdapter)",
                name="uno.events.handlers",
            )
        else:
            # Handler is already an EventHandler instance
            self._handlers[event_type].append(handler)

            self.logger.structured_log(
                "DEBUG",
                f"Registered handler {handler.__class__.__name__} for event type {event_type}",
                name="uno.events.handlers",
            )

    def register_middleware(self, middleware: EventHandlerMiddleware) -> None:
        """
        Register middleware.

        Args:
            middleware: The middleware to register
        """
        self._middleware.append(middleware)

        self.logger.structured_log(
            "DEBUG",
            f"Registered middleware {middleware.__class__.__name__}",
            name="uno.events.handlers",
        )

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

        self.logger.structured_log(
            "DEBUG",
            f"Registered middleware {middleware.__class__.__name__} for event type {event_type}",
            name="uno.events.handlers",
        )

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
        # Check if the factory has the create_default_middleware_stack method
        if hasattr(factory, "create_default_middleware_stack"):
            middleware_stack = factory.create_default_middleware_stack()

            if event_types:
                # Register middleware for specific event types
                for event_type in event_types:
                    for middleware in middleware_stack:
                        if (
                            event_type in self._middleware
                            and self._middleware[event_type]
                        ):
                            self.register_middleware_for_event_type(
                                event_type, middleware
                            )
            else:
                # Register middleware globally
                for middleware in middleware_stack:
                    self.register_middleware(middleware)

            self.logger.structured_log(
                "INFO",
                f"Registered {len(middleware_stack)} middleware components from factory",
                name="uno.events.handlers",
            )
        else:
            self.logger.structured_log(
                "WARN",
                "Factory does not have create_default_middleware_stack method",
                name="uno.events.handlers",
            )

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
        # Start with global middleware
        chain = self.get_middleware().copy()

        # Add event-specific middleware
        chain.extend(self.get_middleware_for_event_type(event_type))

        return chain.copy()

    def clear(self) -> None:
        """Clear all handlers and middleware."""
        self._handlers.clear()
        self._middleware.clear()
        self._middleware_by_event_type.clear()

        self.logger.structured_log(
            "DEBUG",
            "Cleared all handlers and middleware",
            name="uno.events.handlers.registry",
        )


class MiddlewareChainBuilder:
    """Builds a middleware chain for an event handler."""

    def __init__(self, handler: EventHandler):
        """
        Initialize the middleware chain builder.

        Args:
            handler: The event handler to wrap with middleware
        """
        self.handler = handler

    def build_chain(
        self, middleware: list[EventHandlerMiddleware]
    ) -> Callable[[EventHandlerContext], Result[Any, Exception]]:
        """
        Build a middleware chain for the handler.

        Args:
            middleware: List of middleware to chain (from outermost to innermost)

        Returns:
            Function that processes an event through the middleware chain
        """
        # If no middleware, just return the handler directly
        if not middleware:
            return self._create_handler_executor(self.handler)

        # The innermost function in the chain calls the handler
        def final_middleware_fn(context: EventHandlerContext) -> Result[Any, Exception]:
            return self._execute_handler(self.handler, context)

        # Build the chain from innermost to outermost
        middleware_fn = final_middleware_fn

        # Apply middleware in reverse order since the execution
        # order is outermost -> innermost
        for m in reversed(middleware):
            middleware_fn = self._create_middleware_executor(m, middleware_fn)

        return middleware_fn

    def _create_middleware_executor(
        self,
        middleware: EventHandlerMiddleware,
        next_middleware: Callable[[EventHandlerContext], Result[Any, Exception]],
    ) -> Callable[[EventHandlerContext], Result[Any, Exception]]:
        """
        Create a function that executes a middleware component.

        Args:
            middleware: The middleware to execute
            next_middleware: The next middleware in the chain

        Returns:
            Function that processes an event through this middleware
        """

        async def execute_middleware(
            context: EventHandlerContext,
        ) -> Result[Any, Exception]:
            try:
                return await middleware.process(context, next_middleware)
            except Exception as e:
                return Failure(e)

        return execute_middleware

    def _create_handler_executor(
        self, handler: EventHandler
    ) -> Callable[[EventHandlerContext], Result[Any, Exception]]:
        """
        Create a function that executes a handler.

        Args:
            handler: The handler to execute

        Returns:
            Function that processes an event through this handler
        """

        async def execute_handler(
            context: EventHandlerContext,
        ) -> Result[Any, Exception]:
            return await self._execute_handler(handler, context)

        return execute_handler

    async def _execute_handler(
        self, handler: EventHandler, context: EventHandlerContext
    ) -> Result[Any, Exception]:
        """
        Execute a handler and handle exceptions.

        Args:
            handler: The handler to execute
            context: The event handler context

        Returns:
            Result with the handler's return value or an error
        """
        try:
            return await handler.handle(context)
        except Exception as e:
            return Failure(e)


class EventHandlerDecorator:
    """Decorator for event handlers."""

    _registry: ClassVar[EventHandlerRegistry | None] = None

    @classmethod
    def set_registry(cls, registry: EventHandlerRegistry) -> None:
        """
        Set the registry to use for decorators.

        Args:
            registry: The registry to use
        """
        cls._registry = registry

    @classmethod
    def get_registry(cls, logger: LoggerService) -> EventHandlerRegistry:
        """
        Get the registry, creating it if needed with a DI-injected logger.

        Args:
            logger: DI-injected LoggerService
        Returns:
            The registry
        """
        if cls._registry is None:
            cls._registry = EventHandlerRegistry(logger)
        return cls._registry

    @classmethod
    def handles(
        cls, event_type: str, logger: LoggerService
    ) -> Callable[[type[EventHandler]], type[EventHandler]]:
        """
        Decorator to register a handler for an event type, with DI-injected logger.

        Args:
            event_type: The event type to handle
            logger: DI-injected LoggerService
        Returns:
            Decorator function
        """

        def decorator(handler_class: type[EventHandler]) -> type[EventHandler]:
            registry = cls.get_registry(logger)
            handler = handler_class()
            registry.register_handler(event_type, handler)
            return handler_class

        return decorator


handles = EventHandlerDecorator.handles


class EventBus:
    """Event bus for dispatching events to handlers."""

    def __init__(
        self, logger: LoggerService, registry: EventHandlerRegistry | None = None
    ):
        """
        Initialize the event bus.

        Args:
            logger: DI-injected LoggerService
            registry: Optional registry to use
        """
        self.logger = logger
        self.registry = registry or EventHandlerRegistry(logger)

    async def publish(
        self, event: DomainEvent, metadata: dict[str, Any] | None = None
    ) -> Result[list[Result[Any, Exception]], Exception]:
        """Publish an event to all registered handlers."""
        event_type = event.event_type

        # Add some default metadata if none provided
        metadata = metadata or {}
        metadata.setdefault("published_at", time.time())

        # Create context
        context = EventHandlerContext(event=event, metadata=metadata)

        # Get handlers for this event type from the registry
        handlers = self.registry.get_handlers(event_type)

        if not handlers:
            self.logger.structured_log(
                "DEBUG",
                f"No handlers registered for event {event_type}",
                name="events.bus",
                event_id=event.event_id,
            )
            return Success([])

        # Build middleware chain for this event type
        middleware_chain = self.registry.build_middleware_chain(event_type)

        # Execute handlers with middleware
        results: list[Result[Any, Exception]] = []

        for handler in handlers:
            try:
                start_time = time.time()

                # Execute handler with middleware chain
                if middleware_chain:
                    # Use a class-based approach to completely avoid closure binding issues
                    class HandlerExecutor:
                        def __init__(self, handler_instance):
                            self.handler = handler_instance

                        async def execute(
                            self, ctx: EventHandlerContext
                        ) -> Result[Any, Exception]:
                            return await self.handler.handle(ctx)

                    class MiddlewareProcessor:
                        def __init__(self, middleware_instance, next_processor):
                            self.middleware = middleware_instance
                            self.next_processor = next_processor

                        async def process(
                            self, ctx: EventHandlerContext
                        ) -> Result[Any, Exception]:
                            return await self.middleware.process(
                                ctx, self.next_processor
                            )

                    # Create the handler executor
                    executor = HandlerExecutor(handler)

                    # Start with the handler's execute method
                    processor = executor.execute

                    # Build the chain from inside out
                    for middleware in reversed(middleware_chain):
                        middleware_processor = MiddlewareProcessor(
                            middleware, processor
                        )
                        processor = middleware_processor.process

                    # Execute the chain
                    result = await processor(context)
                else:
                    # No middleware, execute the handler directly
                    result = await handler.handle(context)

                end_time = time.time()
                elapsed_ms = (end_time - start_time) * 1000

                results.append(result)

                handler_name = handler.__class__.__name__
                if result.is_success:
                    self.logger.structured_log(
                        "DEBUG",
                        f"Handler {handler_name} successfully processed {event_type} in {elapsed_ms:.2f}ms",
                        name="events.bus",
                        handler=handler_name,
                        event_id=event.event_id,
                        event_type=event_type,
                        elapsed_ms=elapsed_ms,
                    )
                else:
                    self.logger.structured_log(
                        "WARNING",
                        f"Handler {handler_name} failed to process {event_type}: {result.error}",
                        name="events.bus",
                        handler=handler_name,
                        event_id=event.event_id,
                        event_type=event_type,
                        error=result.error,
                        elapsed_ms=elapsed_ms,
                    )

            except Exception as e:
                handler_name = getattr(handler, "__class__", type(handler)).__name__
                self.logger.structured_log(
                    "ERROR",
                    f"Error executing handler {handler_name} for event {event_type}: {e}",
                    name="events.bus",
                    handler=handler_name,
                    event_id=event.event_id,
                    event_type=event_type,
                    error=e,
                )
                results.append(Failure(e))

        self.logger.structured_log(
            "INFO",
            f"Published event {event_type} to {len(handlers)} handlers",
            name="events.bus",
            event_id=event.event_id,
            handler_count=len(handlers),
            success_count=sum(1 for r in results if r.is_success),
            failure_count=sum(1 for r in results if not r.is_success),
        )

        return Success(results)

    async def publish_many(
        self, events: list[DomainEvent], metadata: dict[str, Any] | None = None
    ) -> Result[list[Result[list[Result[Any, Exception]], Exception]], Exception]:
        """Publish multiple events to all registered handlers."""
        results: list[Result[list[Result[Any, Exception]], Exception]] = []

        for event in events:
            result = await self.publish(event, metadata)
            results.append(result)

        return Success(results)


from uno.events.middleware.retry import RetryMiddleware
from uno.events.middleware.metrics import MetricsMiddleware
from uno.events.middleware.circuit_breaker import CircuitBreakerMiddleware

# Common middleware implementations


class LoggingMiddleware(EventHandlerMiddleware):
    """Middleware for logging event handling."""

    def __init__(self, logger_factory: Callable[..., LoggerService] | None = None):
        """
        Initialize the middleware.

        Args:
            logger_factory: Optional factory for creating loggers
        """
        # Use provided logger factory or create a default logger
        if logger_factory:
            self.logger = logger_factory("logging_middleware")
        else:
            self.logger = LoggerService(LoggingConfig())

    async def process(
        self,
        context: EventHandlerContext,
        next_middleware: Callable[[EventHandlerContext], Result[Any, Exception]],
    ) -> Result[Any, Exception]:
        """
        Log event handling and pass to next middleware.

        Args:
            context: The event handler context
            next_middleware: The next middleware to call

        Returns:
            Result from the next middleware
        """
        event = context.event

        self.logger.structured_log(
            "DEBUG",
            f"Processing event {event.event_type}",
            name="uno.events.handlers.middleware",
            event_id=event.event_id,
            aggregate_id=event.aggregate_id,
        )

        try:
            result = await next_middleware(context)

            if result.is_failure:
                self.logger.structured_log(
                    "ERROR",
                    f"Event handling failed for {event.event_type}: {result.error}",
                    name="uno.events.handlers.middleware",
                    error=result.error,
                    event_id=event.event_id,
                    aggregate_id=event.aggregate_id,
                )
            else:
                self.logger.structured_log(
                    "DEBUG",
                    f"Event handling succeeded for {event.event_type}",
                    name="uno.events.handlers.middleware",
                    event_id=event.event_id,
                    aggregate_id=event.aggregate_id,
                )

            return result

        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Unexpected error handling event {event.event_type}: {e}",
                name="uno.events.handlers.middleware",
                error=e,
                event_id=event.event_id,
                aggregate_id=event.aggregate_id,
            )
            return Failure(e)


class TimingMiddleware(EventHandlerMiddleware):
    """Middleware for timing event handling."""

    def __init__(self, logger_factory: Callable[..., LoggerService] | None = None):
        """
        Initialize the middleware.

        Args:
            logger_factory: Optional factory for creating loggers
        """
        # Use provided logger factory or create a default logger
        if logger_factory:
            self.logger = logger_factory("timing_middleware")
        else:
            self.logger = LoggerService(LoggingConfig())

    async def process(
        self,
        context: EventHandlerContext,
        next_middleware: Callable[[EventHandlerContext], Result[Any, Exception]],
    ) -> Result[Any, Exception]:
        """
        Time event handling and pass to next middleware.

        Args:
            context: The event handler context
            next_middleware: The next middleware to call

        Returns:
            Result from the next middleware
        """
        import time

        event = context.event
        start_time = time.time()

        try:
            result = await next_middleware(context)

            end_time = time.time()
            elapsed_ms = (end_time - start_time) * 1000

            self.logger.structured_log(
                "DEBUG",
                f"Event {event.event_type} handled in {elapsed_ms:.2f}ms",
                name="uno.events.handlers.middleware",
                event_id=event.event_id,
                aggregate_id=event.aggregate_id,
                elapsed_ms=elapsed_ms,
            )

            return result

        except Exception as e:
            end_time = time.time()
            elapsed_ms = (end_time - start_time) * 1000

            self.logger.structured_log(
                "ERROR",
                f"Error handling event {event.event_type} after {elapsed_ms:.2f}ms: {e}",
                name="uno.events.handlers.middleware",
                error=e,
                event_id=event.event_id,
                aggregate_id=event.aggregate_id,
                elapsed_ms=elapsed_ms,
            )

            return Failure(e)


# Automatic event handler discovery


def discover_handlers(
    package: str | ModuleType,
    logger: LoggerService,
    registry: EventHandlerRegistry | None = None,
) -> EventHandlerRegistry:
    """
    Discover event handlers in a package.

    This function scans a package and its subpackages for event handlers,
    automatically registering them with the registry. Handlers can be:

    1. Classes that inherit from EventHandler
    2. Classes decorated with @handles(event_type)
    3. Functions decorated with @function_handler(event_type)
    4. Any object with an _is_event_handler attribute set to True

    Args:
        package: The package/module to scan
        logger: DI-injected LoggerService
        registry: Optional registry to use
    """
    registry = registry or EventHandlerRegistry(logger)

    # Import the decorator module
    from uno.events.decorators import EventHandlerDecorator

    # Use provided registry or create a new one
    registry = registry or EventHandlerRegistry()

    # Use provided logger factory or create a default logger
    if logger_factory:
        logger = logger_factory("handler_discovery")
    else:
        logger = LoggerService(LoggingConfig())

    # Set the logger and registry for the decorator
    EventHandlerDecorator.set_logger(logger)
    EventHandlerDecorator.set_registry(registry)

    # Get the package as a module
    if isinstance(package, str):
        try:
            package_module = importlib.import_module(package)
        except ImportError as e:
            logger.structured_log(
                "ERROR",
                f"Error importing package {package}: {e}",
                name="uno.events.handlers.discovery",
                error=e,
            )
            return registry
    else:
        package_module = package

    # Get the package directory
    package_path = getattr(package_module, "__path__", None)
    if not package_path:
        logger.structured_log(
            "ERROR",
            f"Package {package_module.__name__} has no __path__ attribute",
            name="uno.events.handlers.discovery",
        )
        return registry

    # Store discovered handler count before scanning
    initial_handler_count = sum(
        len(handlers) for handlers in registry._handlers.values()
    )

    # Recursively import all modules in the package
    def import_recursive(pkg: ModuleType) -> None:
        pkg_path = getattr(pkg, "__path__", None)
        if not pkg_path:
            return

        for _, name, is_pkg in pkgutil.iter_modules(pkg_path):
            full_name = f"{pkg.__name__}.{name}"

            try:
                module = importlib.import_module(full_name)

                # Check if the module contains event handlers
                for item_name in dir(module):
                    try:
                        item = getattr(module, item_name)

                        # Check for handlers that aren't already registered
                        if inspect.isclass(item):
                            # Check for EventHandler subclasses
                            if (
                                issubclass(item, EventHandler)
                                and item != EventHandler
                                and not getattr(
                                    item, "_registered_with_discovery", False
                                )
                            ):
                                # Instantiate and register the handler if it has a default constructor
                                try:
                                    handler_instance = item()
                                    event_type = getattr(item, "_event_type", None)
                                    if event_type is None and hasattr(
                                        handler_instance, "event_type"
                                    ):
                                        event_type = handler_instance.event_type

                                    if event_type:
                                        registry.register_handler(
                                            event_type, handler_instance
                                        )
                                        setattr(
                                            item, "_registered_with_discovery", True
                                        )
                                        logger.structured_log(
                                            "DEBUG",
                                            f"Registered handler class {item.__name__} for event {event_type}",
                                            name="uno.events.handlers.discovery",
                                        )
                                except Exception as e:
                                    # Couldn't instantiate, probably needs constructor arguments
                                    logger.structured_log(
                                        "DEBUG",
                                        f"Couldn't auto-instantiate handler class {item.__name__}: {e}",
                                        name="uno.events.handlers.discovery",
                                    )

                        # Check for handlers marked with the decorator
                        elif hasattr(item, "_is_event_handler") and getattr(
                            item, "_is_event_handler", False
                        ):
                            if not getattr(item, "_registered_with_discovery", False):
                                event_type = getattr(item, "_event_type", None)
                                if event_type:
                                    registry.register_handler(event_type, item)
                                    setattr(item, "_registered_with_discovery", True)
                                    logger.structured_log(
                                        "DEBUG",
                                        f"Registered decorated handler {item.__name__} for event {event_type}",
                                        name="uno.events.handlers.discovery",
                                    )

                    except (AttributeError, TypeError) as e:
                        # Skip items that can't be accessed or aren't handlers
                        pass

                if is_pkg:
                    import_recursive(module)

            except ImportError as e:
                logger.structured_log(
                    "ERROR",
                    f"Error importing module {full_name}: {e}",
                    name="uno.events.handlers.discovery",
                    error=e,
                )

    # Start the recursive import process
    import_recursive(package_module)

    # Calculate number of new handlers discovered
    final_handler_count = sum(len(handlers) for handlers in registry._handlers.values())
    new_handlers = final_handler_count - initial_handler_count

    logger.structured_log(
        "INFO",
        f"Discovered {new_handlers} new event handlers (total: {final_handler_count})",
        name="uno.events.handlers.discovery",
        new_handlers=new_handlers,
        total_handlers=final_handler_count,
    )

    return registry
