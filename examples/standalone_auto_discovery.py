"""Standalone example demonstrating automatic event handler discovery and registration.

This example demonstrates the key concepts of event handler discovery and automatic
registration without requiring the full uno framework import chain.
"""

import asyncio
import inspect
from uno.core.logging.logger import LoggerService, LoggingConfig

# Uno strict DI logging: inject a LoggerService for all handlers
logger = LoggerService(LoggingConfig())
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol, cast


# Configure basic logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("auto-discovery-example")


# ---- Minimal Result implementation ----
class Result(Protocol):
    """A protocol representing a result that may be successful or a failure."""
    
    @property
    def is_success(self) -> bool:
        """Return True if this is a success result."""
        ...
    
    @property
    def is_failure(self) -> bool:
        """Return True if this is a failure result."""
        ...

class Success:
    """A successful result with a value."""
    
    def __init__(self, value: Any):
        self.value = value
    
    @property
    def is_success(self) -> bool:
        return True
    
    @property
    def is_failure(self) -> bool:
        return False

class Failure:
    """A failure result with an exception."""
    
    def __init__(self, error: Exception):
        self.error = error
    
    @property
    def is_success(self) -> bool:
        return False
    
    @property
    def is_failure(self) -> bool:
        return True


# ---- Event system classes ----
class DomainEvent:
    """Base class for all domain events."""
    
    event_type: str = "domain_event"
    
    def __init__(self):
        self.timestamp = asyncio.get_event_loop().time()


@dataclass
class EventHandlerContext:
    """Context for event handlers with metadata and utilities."""
    
    event: DomainEvent
    metadata: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


class EventHandler(ABC):
    """Base class for event handlers."""
    
    @abstractmethod
    async def handle(self, context: EventHandlerContext) -> Result:
        """Handle an event."""
        pass


class EventHandlerRegistry:
    """Registry for event handlers and middleware."""
    
    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = {}
    
    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        # Avoid duplicate registrations
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.info(f"Registered handler {handler.__class__.__name__} for {event_type}")
    
    def get_handlers(self, event_type: str) -> list[EventHandler]:
        """Get all handlers for an event type."""
        return self._handlers.get(event_type, [])


# ---- Event discovery and decorator functionality ----
class EventHandlerDecorator:
    """Base class for decorator-based handler registration."""
    
    _registry: EventHandlerRegistry | None = None
    
    @classmethod
    def set_registry(cls, registry: EventHandlerRegistry) -> None:
        """Set the registry for all decorators."""
        cls._registry = registry
    
    @classmethod
    def handles(cls, event_type: Any) -> Any:
        """Decorator to mark a class as handling a specific event type."""
        
        def decorator(handler: Any) -> Any:
            event_type_str = cls._get_event_type_str(event_type)
            
            # Store the event type on the handler for later discovery
            handler._event_type = event_type_str
            handler._is_event_handler = True
            
            # If we have a registry, register the handler right away
            if cls._registry is not None:
                # For classes, we need to instantiate them
                if inspect.isclass(handler) and issubclass(handler, EventHandler):
                    cls._registry.register_handler(event_type_str, handler())
                else:
                    cls._registry.register_handler(event_type_str, handler)
            
            return handler
        
        return decorator
    
    @staticmethod
    def _get_event_type_str(event_type: Any) -> str:
        """Convert an event type to its string representation."""
        if isinstance(event_type, str):
            return event_type
        
        if hasattr(event_type, "event_type"):
            return cast('str', event_type.event_type)
        
        return event_type.__name__.lower()


# Create decorator functions
handles = EventHandlerDecorator.handles


class FunctionHandlerAdapter(EventHandler):
    """Adapter that wraps a function to make it compatible with the EventHandler interface."""
    
    def __init__(self, func: Any, event_type: str):
        self.func = func
        self._event_type = event_type
        self._is_event_handler = True
    
    async def handle(self, context: EventHandlerContext) -> Result:
        """Delegate to the wrapped function."""
        return await self.func(context)


def function_handler(event_type: Any) -> Any:
    """
    Decorator for function-based event handlers.
    
    This decorator wraps a function in an adapter that makes it compatible
    with the EventHandler interface.
    
    Args:
        event_type: The event type this handler processes
        
    Returns:
        The decorated function
    """
    def decorator(func: Any) -> Any:
        event_type_str = EventHandlerDecorator._get_event_type_str(event_type)
        
        # Mark the function for discovery
        func._event_type = event_type_str
        func._is_event_handler = True
        
        # If we have a registry, register an adapter right away
        if EventHandlerDecorator._registry is not None:
            adapter = FunctionHandlerAdapter(func, event_type_str)
            EventHandlerDecorator._registry.register_handler(event_type_str, adapter)
        
        return func
    
    return decorator


def discover_handlers(modules: list[dict[str, Any]], registry: EventHandlerRegistry | None = None) -> list[Any]:
    """Discover event handlers in the given modules."""
    handlers = []
    
    for module_dict in modules:
        for name, obj in module_dict.items():
            # Skip non-relevant items
            if name.startswith('_'):
                continue
                
            # Check if the object is marked as an event handler
            if hasattr(obj, '_is_event_handler') and getattr(obj, '_is_event_handler', False):
                logger.info(f"Found handler: {name}")
                handlers.append(obj)
                continue
                
            # Check if it's a class that inherits from EventHandler
            if (inspect.isclass(obj) and issubclass(obj, EventHandler) and obj != EventHandler and 
                hasattr(obj, '_is_event_handler') and getattr(obj, '_is_event_handler', False)):
                logger.info(f"Found handler class: {name}")
                handlers.append(obj)
    
    return handlers


# ---- Event bus implementation ----
class SimpleEventBus:
    """A simple event bus implementation."""
    
    def __init__(self, registry: EventHandlerRegistry):
        self.registry = registry
        self.logger = logging.getLogger("SimpleEventBus")
    
    async def publish(self, event: DomainEvent, metadata: dict[str, Any] | None = None) -> list[Result]:
        """Publish an event to all registered handlers."""
        event_type = event.event_type
        self.logger.info(f"Publishing event {event_type}")
        
        handlers = self.registry.get_handlers(event_type)
        if not handlers:
            self.logger.warning(f"No handlers found for event {event_type}")
            return []
        
        results = []
        for handler in handlers:
            context = EventHandlerContext(event=event, metadata=metadata or {})
            try:
                result = await handler.handle(context)
                results.append(result)
                self.logger.info(f"Handler {handler.__class__.__name__} processed event {event_type}")
            except Exception as e:
                self.logger.error(f"Error in handler {handler.__class__.__name__}: {e}")
                results.append(Failure(e))
        
        return results


# ---- Example implementation ----
# Define our domain events
class UserCreatedEvent(DomainEvent):
    """Event emitted when a user is created."""
    event_type = "user_created"
    
    def __init__(self, user_id: str, username: str):
        self.user_id = user_id
        self.username = username
        super().__init__()


class UserUpdatedEvent(DomainEvent):
    """Event emitted when a user is updated."""
    event_type = "user_updated"
    
    def __init__(self, user_id: str, new_username: str):
        self.user_id = user_id
        self.new_username = new_username
        super().__init__()


# Class-based handler using the handles decorator
from uno.core.logging.logger import LoggerService, LoggingConfig

# Uno strict DI logging: inject a LoggerService into @handles
logger = LoggerService(LoggingConfig())

@handles(UserCreatedEvent, logger)
class UserCreatedHandler(EventHandler):
    """Handler for user created events."""
    
    def __init__(self):
        self.logger = logger
    
    async def handle(self, context: EventHandlerContext) -> Result:
        event = cast('UserCreatedEvent', context.event)
        
        self.logger.structured_log(
            "INFO",
            f"User created: {event.user_id} with username {event.username}",
            name="UserCreatedHandler"
        )
        return Success(None)


# Standard handler class registered manually
class UserUpdatedHandler(EventHandler):
    """Handler for user updated events."""
    
    def __init__(self):
        self.logger = logger
    
    async def handle(self, context: EventHandlerContext) -> Result:
        event = cast('UserUpdatedEvent', context.event)
        
        self.logger.structured_log(
            "INFO",
            f"User updated: {event.user_id} with new username {event.new_username}",
            name="UserUpdatedHandler"
        )
        return Success(None)


# Function handler using decorator
@function_handler(UserCreatedEvent)
async def log_user_created(context: EventHandlerContext) -> Result:
    """Log when a user is created."""
    event = cast('UserCreatedEvent', context.event)
    
    logger.structured_log(
        "INFO",
        f"[FUNC] User created: {event.user_id} with username {event.username}",
        name="log_user_created"
    )
    return Success(None)


# Simple module object with handler method
class UserModule:
    """Module that handles user events."""
    
    def __init__(self):
        self._is_event_handler = True
        self._event_type = "user_updated"
        self.logger = logger
    
    async def handle(self, context: EventHandlerContext) -> Result:
        event = cast('UserUpdatedEvent', context.event)
        
        self.logger.structured_log(
            "INFO",
            f"[MODULE] User updated: {event.user_id} with new username {event.new_username}",
            name="UserModule"
        )
        return Success(None)


async def main():
    """Run the example."""
    # Create registry and register handlers
    registry = EventHandlerRegistry(logger)
    
    # Set up the decorator registry
    EventHandlerDecorator.set_registry(registry)
    # All decorators and handler registration now use DI logger
    
    # Manually register the UserUpdatedHandler
    registry.register_handler("user_updated", UserUpdatedHandler())
    
    # Register the module handler
    user_module = UserModule()
    registry.register_handler(user_module._event_type, user_module)
    
    # Create simple event bus
    event_bus = SimpleEventBus(registry)
    
    # Discover and register handlers from the current module
    print("\nDiscovering handlers...")
    discovered_handlers = discover_handlers([globals()], registry)
    print(f"Found {len(discovered_handlers)} handlers through discovery")
    
    for handler in discovered_handlers:
        if hasattr(handler, "_event_type") and hasattr(handler, "_is_event_handler"):
            handler_name = handler.__name__ if hasattr(handler, '__name__') else handler.__class__.__name__
            print(f"  - {handler_name} handles {handler._event_type}")
            # For class-based handlers that need initialization
            if inspect.isclass(handler) and issubclass(handler, EventHandler):
                registry.register_handler(handler._event_type, handler())
            elif callable(handler) and not isinstance(handler, EventHandler):
                # For function handlers, wrap them in an adapter
                adapter = FunctionHandlerAdapter(handler, handler._event_type)
                registry.register_handler(handler._event_type, adapter)
            else:  # Already initialized objects
                registry.register_handler(handler._event_type, handler)
    
    # Get all registered handlers
    user_created_handlers = registry.get_handlers("user_created")
    user_updated_handlers = registry.get_handlers("user_updated")
    
    print(f"\nRegistered 'user_created' handlers: {len(user_created_handlers)}")
    for handler in user_created_handlers:
        print(f"  - {handler.__class__.__name__}")
    
    print(f"\nRegistered 'user_updated' handlers: {len(user_updated_handlers)}")
    for handler in user_updated_handlers:
        print(f"  - {handler.__class__.__name__}")
    
    # Publish events
    print("\nPublishing events...")
    await event_bus.publish(UserCreatedEvent("123", "johndoe"))
    await event_bus.publish(UserUpdatedEvent("123", "john.doe"))


if __name__ == "__main__":
    asyncio.run(main())
