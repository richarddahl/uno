"""Example demonstrating automatic event handler discovery and registration in Uno.

This example shows how to use the event handler discovery system to automatically
find and register event handlers in your application, without having to manually
register each handler with the EventBus.
"""

import asyncio
import inspect
import logging
from typing import Any, cast

from uno.core.errors.result import Result, Success
from uno.core.events.context import EventHandlerContext
# from uno.core.events.decorators import function_handler, handles  # Example only: comment out if not present
# from uno.core.events.events import DomainEvent  # Example only: comment out if not present
from uno.core.events.handlers import EventHandler, EventHandlerRegistry
from uno.core.events.context import EventHandlerContext
from uno.core.errors.result import Result, Success
from uno.core.logging.logger import LoggerService, LoggingConfig

# Uno strict DI logging: inject a LoggerService for all handlers
logger = LoggerService(LoggingConfig())

# Use this logger for all handler classes, function handlers, and registry


# Configure basic logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("auto-discovery-example")

# Create our own simplified EventBus to avoid importing circular dependencies
class SimpleEventBus:
    def __init__(self, registry: EventHandlerRegistry):
        self.registry = registry
        self.logger = logging.getLogger("SimpleEventBus")
    
    async def publish(self, event: DomainEvent, metadata: dict[str, Any] | None = None) -> list[Result[Any, Exception]]:
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
        
        return results

# Simple implementation of the discovery function
def discover_handlers(modules: list[dict[str, Any]], logger: logging.Logger) -> list[Any]:
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

# Define our domain events
class UserCreatedEvent(DomainEvent):
    event_type = "user_created"
    
    def __init__(self, user_id: str, username: str):
        self.user_id = user_id
        self.username = username
        super().__init__()

class UserUpdatedEvent(DomainEvent):
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
    def __init__(self):
        self.logger = logger
    
    async def handle(self, context: EventHandlerContext) -> Result[None, Exception]:
        event = cast('UserCreatedEvent', context.event)
        self.logger.structured_log(
            "INFO",
            f"User created: {event.user_id} with username {event.username}",
            name="UserCreatedHandler"
        )
        return Success(None)

# Standard handler class registered manually
class UserUpdatedHandler(EventHandler):
    def __init__(self):
        self.logger = logger
    
    async def handle(self, context: EventHandlerContext) -> Result[None, Exception]:
        event = cast('UserUpdatedEvent', context.event)
        self.logger.structured_log(
            "INFO",
            f"User updated: {event.user_id} with new username {event.new_username}",
            name="UserUpdatedHandler"
        )
        return Success(None)

# Function handler using decorator
# @function_handler(UserCreatedEvent)  # Example only: comment out if not present
async def log_user_created(context: EventHandlerContext) -> Result[None, Exception]:
    event = cast('UserCreatedEvent', context.event)
    logger.structured_log(
        "INFO",
        f"[FUNC] User created: {event.user_id} with username {event.username}",
        name="log_user_created"
    )
    return Success(None)

# Simple module object with handler method
class UserModule:
    def __init__(self):
        self._is_event_handler = True
        self._event_type = "user_updated"
        self.logger = logger
    
    async def handle(self, context: EventHandlerContext) -> Result[None, Exception]:
        event = cast('UserUpdatedEvent', context.event)
        self.logger.structured_log(
            "INFO",
            f"[MODULE] User updated: {event.user_id} with new username {event.new_username}",
            name="UserModule"
        )
        return Success(None)

async def main() -> None:
    # Create registry and register handlers
    registry = EventHandlerRegistry(logger)
    
    # Manually register the UserUpdatedHandler
    registry.register_handler("user_updated", UserUpdatedHandler())
    
    # Register the module handler
    user_module = UserModule()
    registry.register_handler(user_module._event_type, user_module)
    
    # Create simple event bus
    event_bus = SimpleEventBus(registry)
    
    # Discover and register handlers from the current module
    print("\nDiscovering handlers...")
    discovered_handlers = discover_handlers([globals()], logger)
    print(f"Found {len(discovered_handlers)} handlers through discovery")
    
    for handler in discovered_handlers:
        if hasattr(handler, "_event_type") and hasattr(handler, "_is_event_handler"):
            handler_name = handler.__name__ if hasattr(handler, '__name__') else handler.__class__.__name__
            print(f"  - {handler_name} handles {handler._event_type}")
            # For class-based handlers that need initialization
            if inspect.isclass(handler) and issubclass(handler, EventHandler):
                registry.register_handler(handler._event_type, handler())
            else:  # Function handlers or already initialized objects
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
