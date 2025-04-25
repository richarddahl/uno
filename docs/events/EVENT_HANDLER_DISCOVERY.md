# Event Handler Discovery in Uno

This document describes the enhanced event handler discovery system in Uno, which allows for automatic registration of event handlers through decorators and other mechanisms.

## Overview

The event handler discovery system allows you to define event handlers in your application and have them automatically discovered and registered with the event bus. This simplifies the process of adding new event handlers and reduces the amount of boilerplate code needed.

## Handler Types

There are three main ways to define event handlers:

### 1. Class-Based Handlers with Decorator

```python
from uno.core.errors.result import Success
from uno.core.events.context import EventHandlerContext
from uno.core.events.decorators import handles
from uno.core.events.events import DomainEvent
from uno.core.events.handlers import EventHandler

class UserCreatedEvent(DomainEvent):
    event_type = "user_created"
    
    def __init__(self, user_id: str, username: str):
        self.user_id = user_id
        self.username = username
        super().__init__()

@handles(UserCreatedEvent)
class UserCreatedHandler(EventHandler):
    async def handle(self, context: EventHandlerContext) -> Result[None, Exception]:
        # Get typed event with automatic type checking
        event = context.get_typed_event(UserCreatedEvent)
        
        # Handle event
        print(f"User created: {event.user_id} with username {event.username}")
        return Success(None)
```

### 2. Function-Based Handlers with Decorator

```python
from uno.core.errors.result import Success
from uno.core.events.decorators import function_handler

@function_handler(UserCreatedEvent)
async def log_user_created(context: EventHandlerContext) -> Result[None, Exception]:
    event = context.get_typed_event(UserCreatedEvent)
    
    # Handle event
    print(f"[FUNC] User created: {event.user_id} with username {event.username}")
    return Success(None)
```

### 3. Custom Objects with Event Handler Properties

```python
class UserModule:
    def __init__(self):
        # Mark this object as an event handler
        self._is_event_handler = True
        self._event_type = "user_updated"
    
    async def handle(self, context: EventHandlerContext) -> Result[None, Exception]:
        # Handle event
        event = context.get_typed_event(UserUpdatedEvent)
        print(f"User updated: {event.user_id} with new username {event.new_username}")
        return Success(None)
```

## Automatic Discovery

The discovery system can automatically find and register handlers from modules or packages:

```python
from uno.core.events.discovery import discover_handlers, register_handlers_from_modules
from uno.core.events.handlers import EventHandlerRegistry

# Create a registry
registry = EventHandlerRegistry()

# Discover handlers in a module
handlers = discover_handlers("my_app.event_handlers", registry)

# Or register handlers from multiple modules
count = register_handlers_from_modules(
    ["my_app.user_handlers", "my_app.order_handlers"],
    registry
)
```

## Integration with EventBus

The discovered handlers are automatically registered with the event bus:

```python
from uno.core.events.handlers import EventBus
from uno.core.events.decorators import EventHandlerDecorator

# Create an event bus with a registry
registry = EventHandlerRegistry()
event_bus = EventBus(registry=registry)

# Set the registry for automatic registration of future handlers
EventHandlerDecorator.set_registry(registry)

# Now any handler decorated with @handles or @function_handler
# will be automatically registered with this registry
```

## Context Object Enhancements

The `EventHandlerContext` object has been enhanced with utility methods:

```python
# Type-safe event access
event = context.get_typed_event(UserCreatedEvent)

# Add data without mutating the original context
new_context = context.with_extra("correlation_id", "12345")
```

## Async Patterns

The event system handles both synchronous and asynchronous event handlers seamlessly through adapter classes:

- `AsyncEventHandlerAdapter`: Ensures all event handlers present a consistent async interface
- `FunctionHandlerAdapter`: Adapts functions to the `EventHandler` interface

Function handlers are automatically wrapped in a `FunctionHandlerAdapter` when discovered, which handles both synchronous and asynchronous functions.

## Benefits

This enhanced event handler discovery system provides several benefits:

1. **Reduced Boilerplate**: No need to manually register every handler
2. **Declarative Style**: Handlers are defined close to where they're used
3. **Type Safety**: Strong typing with helper methods for type checking
4. **Consistent Async Patterns**: Both sync and async handlers work seamlessly
5. **Modularity**: Handlers can be organized into different modules and discovered automatically

## Best Practices

1. **Use Decorators**: The decorator-based approach is the clearest way to define handlers
2. **Organize by Domain**: Group handlers by domain concept or feature
3. **Consistent Naming**: Use consistent naming for event types
4. **Handle Errors**: Always return a proper Result object from handlers
5. **Document Events**: Document the purpose and structure of events
