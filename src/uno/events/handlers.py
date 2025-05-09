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
from typing import Any, ClassVar, Protocol, TypeVar, runtime_checkable

from uno.utiitlies import (
    AsyncEventHandlerAdapter,
    EventHandlerProtocol,
    FunctionHandlerAdapter,
)
from uno.di.container import DIContainer
from uno.events.base_event import DomainEvent
from uno.events.config import EventsConfig
from uno.events.context import EventHandlerContext
from uno.events.errors import EventHandlerError
from uno.logging.protocols import LoggerProtocol

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

    def __init__(self, logger: LoggerProtocol, container: DIContainer = None) -> None:
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

            self.logger.debug(
                "Registered callable handler for event type",
                event_type=event_type,
                handler_type="AsyncEventHandlerAdapter",
            )
        else:
            # Handler is already an EventHandler instance
            self._handlers[event_type].append(handler)

            self.logger.debug(
                "Registered handler for event type",
                event_type=event_type,
                handler_name=handler.__class__.__name__,
            )

    def register_middleware(self, middleware: EventHandlerMiddleware) -> None:
        """
        Register middleware.

        Args:
            middleware: The middleware to register
        """
        self._middleware.append(middleware)

        self.logger.debug(
            "Registered middleware", middleware_name=middleware.__class__.__name__
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

        self.logger.debug(
            "Registered middleware for event type",
            event_type=event_type,
            middleware_name=middleware.__class__.__name__,
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
                        self.register_middleware_for_event_type(event_type, middleware)
            else:
                # Register middleware globally
                for middleware in middleware_stack:
                    self.register_middleware(middleware)

            self.logger.info(
                "Registered middleware from factory",
                component_count=len(middleware_stack),
            )
        else:
            self.logger.warning(
                "Factory does not have create_default_middleware_stack method",
                factory_name=factory.__class__.__name__,
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

        self.logger.debug("Cleared all handlers and middleware")

    async def resolve_handler_dependencies(self, handler: Any) -> None:
        """
        Resolve handler dependencies using the DI container.

        Args:
            handler: The handler to resolve dependencies for

        Raises:
            ValueError: If no container is available
        """
        if not self.container:
            raise ValueError("No DI container available for dependency resolution")

        # Check if handler has dependencies to be injected
        if hasattr(handler, "__dependencies__") and handler.__dependencies__:
            for dep_name, dep_type in handler.__dependencies__.items():
                try:
                    # Resolve the dependency from the container
                    dependency = await self.container.resolve(dep_type)

                    # Set the dependency on the handler
                    setattr(handler, dep_name, dependency)

                    self.logger.debug(
                        "Resolved dependency for handler",
                        handler=handler.__class__.__name__,
                        dependency=dep_name,
                        dependency_type=dep_type.__name__,
                    )
                except Exception as e:
                    self.logger.error(
                        "Failed to resolve dependency for handler",
                        handler=handler.__class__.__name__,
                        dependency=dep_name,
                        dependency_type=dep_type.__name__,
                        error=str(e),
                    )
                    raise


class MiddlewareChainBuilder:
    """Builds a middleware chain for an event handler."""

    def __init__(self, handler: EventHandler, logger: LoggerProtocol):
        """
        Initialize the middleware chain builder.

        Args:
            handler: The event handler to wrap with middleware
            logger: Logger for structured logging
        """
        self.handler = handler
        self.logger = logger

    def build_chain(
        self, middleware: list[EventHandlerMiddleware]
    ) -> Callable[[DomainEvent], None]:
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
        async def final_middleware_fn(event: DomainEvent) -> None:
            await self._execute_handler(self.handler, event)

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
        next_middleware: Callable[[DomainEvent], None],
    ) -> Callable[[DomainEvent], None]:
        """
        Create a function that executes a middleware component.

        Args:
            middleware: The middleware to execute
            next_middleware: The next middleware in the chain

        Returns:
            Function that processes an event through this middleware
        """

        async def execute_middleware(event: DomainEvent) -> None:
            await middleware.process(event, next_middleware)

        return execute_middleware

    def _create_handler_executor(
        self, handler: EventHandler
    ) -> Callable[[DomainEvent], None]:
        """
        Create a function that executes a handler.

        Args:
            handler: The handler to execute

        Returns:
            Function that processes an event through this handler
        """

        async def execute_handler(event: DomainEvent) -> None:
            await self._execute_handler(handler, event)

        return execute_handler

    async def _execute_handler(self, handler: EventHandler, event: DomainEvent) -> None:
        """
        Execute a handler and handle exceptions.

        Args:
            handler: The handler to execute
            event: The domain event

        Raises:
            EventHandlerError: If the handler fails
        """
        try:
            await handler.handle(event)
        except Exception as e:
            handler_name = getattr(handler, "__class__", type(handler)).__name__
            self.logger.error(
                "Handler execution failed",
                handler=handler_name,
                event_type=event.event_type,
                event_id=getattr(event, "event_id", None),
                error=str(e),
                exc_info=e,
            )

            if isinstance(e, EventHandlerError):
                raise

            raise EventHandlerError(
                event_type=event.event_type, handler_name=handler_name, reason=str(e)
            ) from e


class EventHandlerDecorator:
    """Decorator for event handlers."""

    _registry: ClassVar[EventHandlerRegistry | None] = None
    _container: ClassVar[DIContainer | None] = None

    @classmethod
    def set_registry(cls, registry: EventHandlerRegistry) -> None:
        """
        Set the registry to use for decorators.

        Args:
            registry: The registry to use
        """
        cls._registry = registry

    @classmethod
    def set_container(cls, container: DIContainer) -> None:
        """
        Set the DI container to use for handler dependencies.

        Args:
            container: The DI container to use
        """
        cls._container = container

    @classmethod
    def get_registry(cls, logger: LoggerProtocol) -> EventHandlerRegistry:
        """
        Get the registry, creating it if needed.

        Args:
            logger: Logger for structured logging

        Returns:
            The registry
        """
        if cls._registry is None:
            cls._registry = EventHandlerRegistry(logger, cls._container)
        return cls._registry

    @classmethod
    def handles(cls, event_type: str) -> Callable[[type[Any]], type[Any]]:
        """
        Decorator to register a handler for an event type.

        Args:
            event_type: The event type to handle

        Returns:
            Decorator function
        """

        def decorator(handler_class: type[Any]) -> type[Any]:
            # Set the event type on the class
            handler_class._event_type = event_type
            handler_class._is_event_handler = True

            # Mark that this class needs to be registered (will be done at runtime)
            return handler_class

        return decorator


# Export the decorator function
handles = EventHandlerDecorator.handles


class EventBus:
    """Event bus for dispatching events to handlers."""

    def __init__(
        self,
        logger: LoggerProtocol,
        config: EventsConfig,
        registry: EventHandlerRegistry | None = None,
    ):
        """
        Initialize the event bus.

        Args:
            logger: Logger for structured logging
            config: Event system configuration
            registry: Optional registry to use
        """
        self.logger = logger
        self.config = config
        self.registry = registry or EventHandlerRegistry(logger)

    async def publish(
        self, event: DomainEvent, metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Publish an event to all registered handlers.

        Args:
            event: The event to publish
            metadata: Optional metadata for the event

        Raises:
            EventHandlerError: If any handler fails
        """
        event_type = event.event_type

        # Add some default metadata if none provided
        metadata = metadata or {}
        metadata.setdefault("published_at", time.time())

        # Get handlers for this event type from the registry
        handlers = self.registry.get_handlers(event_type)

        if not handlers:
            self.logger.debug(
                "No handlers registered for event",
                event_type=event_type,
                event_id=getattr(event, "event_id", None),
            )
            return

        # Build middleware chain for this event type
        middleware_chain = self.registry.build_middleware_chain(event_type)
        handler_count = len(handlers)
        success_count = 0

        self.logger.debug(
            "Publishing event to handlers",
            event_type=event_type,
            event_id=getattr(event, "event_id", None),
            handler_count=handler_count,
        )

        # Execute handlers with middleware
        for handler in handlers:
            try:
                start_time = time.time()

                # Before executing, resolve any dependencies
                if self.registry.container:
                    await self.registry.resolve_handler_dependencies(handler)

                # Build and execute the middleware chain
                chain_builder = MiddlewareChainBuilder(handler, self.logger)
                chain = chain_builder.build_chain(middleware_chain)
                await chain(event)

                end_time = time.time()
                elapsed_ms = (end_time - start_time) * 1000

                handler_name = handler.__class__.__name__
                success_count += 1

                self.logger.debug(
                    "Handler successfully processed event",
                    handler=handler_name,
                    event_id=getattr(event, "event_id", None),
                    event_type=event_type,
                    elapsed_ms=elapsed_ms,
                )

            except Exception as e:
                handler_name = getattr(handler, "__class__", type(handler)).__name__

                self.logger.error(
                    "Handler failed to process event",
                    handler=handler_name,
                    event_id=getattr(event, "event_id", None),
                    event_type=event_type,
                    error=str(e),
                    exc_info=e,
                )

                # Only retry if configured and not already an EventHandlerError
                if self.config.retry_attempts > 0 and not isinstance(
                    e, EventHandlerError
                ):
                    await self._retry_handler(handler, event, metadata)
                elif not isinstance(e, EventHandlerError):
                    # Wrap in EventHandlerError if it's not already one
                    raise EventHandlerError(
                        event_type=event_type, handler_name=handler_name, reason=str(e)
                    ) from e
                else:
                    # Re-raise if it's already an EventHandlerError
                    raise

        self.logger.info(
            "Published event to handlers",
            event_type=event_type,
            event_id=getattr(event, "event_id", None),
            handler_count=handler_count,
            success_count=success_count,
        )

    async def _retry_handler(
        self, handler: EventHandler, event: DomainEvent, metadata: dict[str, Any]
    ) -> None:
        """
        Retry a failed handler based on configuration settings.

        Args:
            handler: The event handler to retry
            event: The event to handle
            metadata: Event metadata

        Raises:
            EventHandlerError: If all retry attempts fail
        """
        import asyncio

        retry_count = 0
        last_error = None
        handler_name = getattr(handler, "__class__", type(handler)).__name__

        while retry_count < self.config.retry_attempts:
            retry_count += 1

            # Wait before retrying
            await asyncio.sleep(self.config.retry_delay_ms / 1000.0)

            try:
                self.logger.info(
                    "Retrying event handler",
                    event_id=getattr(event, "event_id", None),
                    event_type=getattr(event, "event_type", None),
                    handler=handler_name,
                    retry_count=retry_count,
                    max_retries=self.config.retry_attempts,
                )

                await handler.handle(event)

                self.logger.info(
                    "Retry succeeded",
                    event_id=getattr(event, "event_id", None),
                    event_type=getattr(event, "event_type", None),
                    handler=handler_name,
                    retry_count=retry_count,
                )

                return
            except Exception as exc:
                last_error = exc
                self.logger.warning(
                    "Retry failed",
                    event_id=getattr(event, "event_id", None),
                    event_type=event.event_type,
                    handler=handler_name,
                    retry_count=retry_count,
                    max_retries=self.config.retry_attempts,
                    error=str(exc),
                )

        # All retries failed
        self.logger.error(
            "All retry attempts failed",
            event_id=getattr(event, "event_id", None),
            event_type=event.event_type,
            handler=handler_name,
            retry_count=retry_count,
            max_retries=self.config.retry_attempts,
        )

        if last_error:
            if isinstance(last_error, EventHandlerError):
                raise last_error

            raise EventHandlerError(
                event_type=event.event_type,
                handler_name=handler_name,
                reason=f"Failed after {retry_count} retry attempts: {last_error}",
            ) from last_error

    async def publish_many(
        self, events: list[DomainEvent], metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Publish multiple events to all registered handlers.

        Args:
            events: The events to publish
            metadata: Optional metadata for the events

        Raises:
            EventHandlerError: If any handler fails
        """
        if not events:
            self.logger.debug("No events to publish")
            return

        self.logger.info("Publishing multiple events", event_count=len(events))

        for event in events:
            await self.publish(event, metadata)

        self.logger.debug("All events published successfully", event_count=len(events))


class LoggingMiddleware(EventHandlerMiddleware):
    """Middleware for logging event handling."""

    def __init__(self, logger: LoggerProtocol):
        """
        Initialize the middleware.

        Args:
            logger: Logger for structured logging
        """
        self.logger = logger

    async def process(
        self,
        event: DomainEvent,
        next_middleware: Callable[[DomainEvent], None],
    ) -> None:
        """
        Log event handling and pass to next middleware.

        Args:
            event: The domain event to process
            next_middleware: The next middleware to call

        Raises:
            EventHandlerError: If the handler fails
        """
        self.logger.debug(
            "Processing event",
            event_type=event.event_type,
            event_id=getattr(event, "event_id", None),
            aggregate_id=getattr(event, "aggregate_id", None),
        )

        try:
            await next_middleware(event)

            self.logger.debug(
                "Event handled successfully",
                event_type=event.event_type,
                event_id=getattr(event, "event_id", None),
                aggregate_id=getattr(event, "aggregate_id", None),
            )
        except Exception as e:
            self.logger.error(
                "Error handling event",
                event_type=event.event_type,
                event_id=getattr(event, "event_id", None),
                aggregate_id=getattr(event, "aggregate_id", None),
                error=str(e),
                exc_info=e,
            )
            raise


class TimingMiddleware(EventHandlerMiddleware):
    """Middleware for timing event handling."""

    def __init__(self, logger: LoggerProtocol):
        """
        Initialize the middleware.

        Args:
            logger: Logger for structured logging
        """
        self.logger = logger

    async def process(
        self,
        event: DomainEvent,
        next_middleware: Callable[[DomainEvent], None],
    ) -> None:
        """
        Time event handling and pass to next middleware.

        Args:
            event: The domain event to process
            next_middleware: The next middleware to call

        Raises:
            EventHandlerError: If the handler fails
        """
        import time

        start_time = time.time()

        try:
            await next_middleware(event)

            end_time = time.time()
            elapsed_ms = (end_time - start_time) * 1000

            self.logger.debug(
                "Event handled",
                event_type=event.event_type,
                event_id=getattr(event, "event_id", None),
                aggregate_id=getattr(event, "aggregate_id", None),
                elapsed_ms=f"{elapsed_ms:.2f}",
            )
        except Exception as e:
            end_time = time.time()
            elapsed_ms = (end_time - start_time) * 1000

            self.logger.error(
                "Error handling event",
                event_type=event.event_type,
                event_id=getattr(event, "event_id", None),
                aggregate_id=getattr(event, "aggregate_id", None),
                elapsed_ms=f"{elapsed_ms:.2f}",
                error=str(e),
            )
            raise


# Automatic event handler discovery
async def discover_handlers(
    package: str | ModuleType,
    logger: LoggerProtocol,
    container: DIContainer = None,
    registry: EventHandlerRegistry | None = None,
) -> EventHandlerRegistry:
    """
    Discover event handlers in a package.

    This function scans a package and its subpackages for event handlers,
    automatically registering them with the registry. Handlers can be:

    1. Classes that implement the EventHandler protocol
    2. Classes decorated with @handles(event_type)
    3. Functions decorated with @function_handler(event_type)
    4. Any object with an _is_event_handler attribute set to True

    Args:
        package: The package/module to scan
        logger: Logger for structured logging
        container: Optional DI container for dependency injection
        registry: Optional registry to use

    Returns:
        The registry with discovered handlers
    """
    registry = registry or EventHandlerRegistry(logger, container)

    # Set the registry for the decorator
    EventHandlerDecorator.set_registry(registry)
    if container:
        EventHandlerDecorator.set_container(container)

    # Get the package as a module
    if isinstance(package, str):
        try:
            package_module = importlib.import_module(package)
        except ImportError as e:
            logger.error(
                "Error importing package", package=package, error=str(e), exc_info=e
            )
            return registry
    else:
        package_module = package

    # Get the package directory
    package_path = getattr(package_module, "__path__", None)
    if not package_path:
        logger.error(
            "Package has no __path__ attribute", package=package_module.__name__
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
                            # Check for EventHandler implementers
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
                                        logger.debug(
                                            "Registered handler class",
                                            handler=item.__name__,
                                            event_type=event_type,
                                        )
                                except Exception as e:
                                    # Couldn't instantiate, probably needs constructor arguments
                                    logger.debug(
                                        "Couldn't auto-instantiate handler class",
                                        handler=item.__name__,
                                        error=str(e),
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
                                    logger.debug(
                                        "Registered decorated handler",
                                        handler=item.__name__,
                                        event_type=event_type,
                                    )

                    except (AttributeError, TypeError) as e:
                        # Skip items that can't be accessed or aren't handlers
                        pass

                if is_pkg:
                    import_recursive(module)

            except ImportError as e:
                logger.error("Error importing module", module=full_name, error=str(e))

    # Start the recursive import process
    import_recursive(package_module)

    # Calculate number of new handlers discovered
    final_handler_count = sum(len(handlers) for handlers in registry._handlers.values())
    new_handlers = final_handler_count - initial_handler_count

    logger.info(
        "Discovered event handlers",
        new_handlers=new_handlers,
        total_handlers=final_handler_count,
    )

    return registry
