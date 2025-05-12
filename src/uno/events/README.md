# Event Handler System

The Uno Event Handler System provides a way to define, discover, and invoke handlers for domain events with full async support and proper cancellation handling.

## Key Components

### Protocols

The `protocols.py` file defines the core interfaces for the event handling system:

- `EventHandlerProtocol`: Interface for event handlers
- `EventRegistryProtocol`: Interface for registering and retrieving event handlers
- `EventProcessorProtocol`: Interface for processing events with handlers
- `EventDiscoveryProtocol`: Interface for discovering event handlers in packages
- `EventMiddlewareProtocol`: Interface for middleware that can intercept events
- `EventBusProtocol`: Interface for publishing events to handlers

### Registry

The `registry.py` file provides an implementation of the event registry that:

- Uses an async-first approach for all operations
- Has no dependencies on DI containers
- Supports both class-based and function-based handlers
- Includes a decorator for marking functions as handlers

### Processor

The `processor.py` file provides an implementation of the event processor that:

- Processes events with all registered handlers
- Provides proper cancellation support via cancellation tokens
- Handles exceptions gracefully with structured error reporting

### Discovery

The `discovery.py` file provides a way to discover event handlers in packages:

- Scans packages recursively for handlers
- Supports both class-based and decorated function handlers
- Works fully asynchronously

### Context

The `context.py` and `correlation.py` files provide context objects for event processing:

- Support for correlation IDs for tracing event flows
- Cancellation support via context objects
- Async context managers for proper resource management

## Usage

```python
# Register a handler function using decorator
from uno.events.registry import subscribe

@subscribe("user.created")
async def handle_user_created(event, context=None):
    # Handle the event
    pass

# Or implement a handler class
from uno.events.protocols import EventHandlerProtocol

class UserCreatedHandler(EventHandlerProtocol):
    async def handle(self, event, context=None):
        # Handle the event
        pass
        
# Process an event with the processor
from uno.events.processor import EventProcessor
from uno.events.registry import EventHandlerRegistry
from uno.logging.logger import get_logger

# Setup
logger = get_logger()
registry = EventHandlerRegistry(logger)
processor = EventProcessor(registry, logger)

# Register handler
await registry.register("user.created", UserCreatedHandler())

# Process event
from uno.domain.event import DomainEvent

event = DomainEvent(event_type="user.created", aggregate_id="user-123")
await processor.process(event)
```

## Features

- **Async First**: All components are designed with async/await patterns
- **Cancellation Support**: Full support for cancellation via tokens
- **Error Handling**: Comprehensive error handling and reporting
- **No DI Dependencies**: No dependencies on DI containers
- **Strongly Typed**: Proper type hints using Python 3.13 style
- **Discoverable**: Automatic discovery of handlers in packages
