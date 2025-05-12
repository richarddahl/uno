# Event Package Migration Guide

This document provides guidance for migrating from the previous event package structure to the new, refactored structure.

## Breaking Changes (Latest)

1. **Deprecated Modules**
   - `uno.events.bus` - Use `uno.events.implementations.bus` or `uno.persistence.event_sourcing.implementations.memory.bus` instead
   - `uno.events.implementations.command` - Use `uno.commands.implementations.memory_bus` instead
   - Several other modules are being considered for deprecation (see below)

2. **Package Structure Changes**
   - Technology-specific implementations have been moved to appropriate packages
   - Protocols have been moved to their respective packages
   - All implementations now use structural typing rather than inheritance

2. **Import Path Changes**
   - `EventStoreProtocol` has moved from `uno.events.protocols` to `uno.persistence.event_sourcing.protocols`
   - Command-related classes have moved to the `uno.commands` package
   - PostgreSQL implementations have moved to `uno.persistence.event_sourcing.implementations.postgres`

3. **Type Hints**
   - All type hints now use Python 3.13 style (e.g., `X | Y` instead of `Union[X, Y]`)
   - Protocol-based structural typing is used instead of inheritance

## Migration Examples

### Before

```python
from uno.events.protocols import EventBusProtocol, EventStoreProtocol
from uno.events.bus import InMemoryEventBus
from uno.events.command import CommandHandler
from typing import Union, Optional

class MyHandler(CommandHandler):
    def __init__(self, event_bus: Optional[EventBusProtocol] = None):
        self.event_bus = event_bus
```

### After

```python
from uno.events.protocols import EventBusProtocol
from uno.persistence.event_sourcing.protocols import EventStoreProtocol
from uno.events.implementations.bus import InMemoryEventBus
from uno.commands.protocols import CommandHandlerProtocol

class MyHandler:
    def __init__(self, event_bus: EventBusProtocol | None = None):
        self.event_bus = event_bus
```

## Migration Guide for Deprecated Modules

### Event Bus Migration

**From:**
```python
from uno.events.bus import InMemoryEventBus

bus = InMemoryEventBus(logger, config)
```

**To:**
```python
# Option 1: Direct from implementations package
from uno.events.implementations.bus import InMemoryEventBus

# Option 2: From persistence package (recommended)
from uno.persistence.event_sourcing.implementations.memory.bus import InMemoryEventBus

bus = InMemoryEventBus(logger, config)
```

### Command Implementation Migration

**From:**
```python
from uno.events.implementations.command import InMemoryCommandBus

command_bus = InMemoryCommandBus(logger)
```

**To:**
```python
from uno.commands.implementations.memory_bus import InMemoryCommandBus

command_bus = InMemoryCommandBus(logger)
```

### Event Store Migration

**From:**
```python
from uno.events.implementations.store import InMemoryEventStore

store = InMemoryEventStore(logger)
```

**To:**
```python
from uno.persistence.event_sourcing.implementations.memory.event_store import InMemoryEventStore

store = InMemoryEventStore(logger)
```

## Deprecation Timeline

* **May 2025**: Deprecation warnings added to legacy modules
* **December 2025**: Legacy modules scheduled for removal in the next major version
* **Q2 2026**: Complete removal of deprecated modules

## Dependency Injection Changes

Previously, DI container registrations looked like:

```python
await container.register_singleton(EventBusProtocol, InMemoryEventBus)
```

Now, they should use the provided registration methods:

```python
# Register events package
from uno.events import register_event_services
await register_event_services(container)

# Register commands package
from uno.commands import register_command_services
await register_command_services(container)
```

## In-Memory vs. Postgres Implementations

### Event Bus

- In-memory: `uno.events.implementations.bus.InMemoryEventBus`
- Postgres: `uno.persistence.event_sourcing.implementations.postgres.bus.PostgresEventBus`

### Event Store

- In-memory: `uno.events.implementations.store.InMemoryEventStore`
- Postgres: `uno.persistence.event_sourcing.implementations.postgres.event_store.PostgresEventStore`

### Command Bus

- In-memory: `uno.commands.implementations.structural_bus.StructuralCommandBus`
- Legacy in-memory: `uno.commands.implementations.memory_bus.InMemoryCommandBus`
- Postgres: `uno.persistence.event_sourcing.implementations.postgres.bus.PostgresCommandBus`

## Backward Compatibility

For backward compatibility, the following imports are still supported but deprecated:

- `uno.events.protocols.CommandHandlerProtocol` (use `uno.commands.protocols.CommandHandlerProtocol` instead)
- `uno.events.protocols.EventStoreProtocol` (use `uno.persistence.event_sourcing.protocols.EventStoreProtocol` instead)

Aliases are also provided in the persistence package for in-memory implementations:

```python
# These imports point to the same implementations
from uno.events.implementations.bus import InMemoryEventBus
from uno.persistence.event_sourcing.implementations.memory import InMemoryEventBus
```

## Async-First Event Processing

The event system has been refactored to be async-first, with improved concurrency and error handling.

### Batched Event Publishing

The event bus now supports batched publishing for high-throughput scenarios:

```python
# Before
for event in events:
    await event_bus.publish(event)

# After - more efficient
await event_bus.publish_many(events, batch_size=10)
```

This implementation uses `asyncio.gather` to process events concurrently within each batch, significantly improving throughput while maintaining control over resource usage.

### Correlation ID Handling

Events now automatically generate correlation IDs if not provided:

```python
# Events will have correlation IDs automatically generated
event = OrderCreated(
    aggregate_id="order-123",
    # No need to manually set correlation_id
)

# You can still provide explicit correlation IDs when needed
event = OrderCreated(
    aggregate_id="order-123",
    metadata=EventMetadata(correlation_id="corr-123")
)
```

### Improved Error Handling

The event system now uses structured exception handling with detailed error information:

```python
try:
    await event_bus.publish(event)
except EventPublishError as e:
    # Access structured error information
    print(f"Error code: {e.code}")
    print(f"Error message: {e.message}")
    print(f"Event type: {e.event_type}")
    print(f"Context: {e.context}")
```

## Event Protocol Compliance

All domain events now implement the `DomainEventProtocol` for improved type safety and interoperability:

```python
# Check protocol compliance
from uno.domain.protocols import DomainEventProtocol

# Runtime protocol checking
assert isinstance(my_event, DomainEventProtocol)

# Or use type hints
def process_event(event: DomainEventProtocol) -> None:
    # Process any event that conforms to the protocol
    print(f"Processing event {event.event_type} for {event.aggregate_id}")
```

For more information on event replay and upcasting patterns, see [Event Upcasting Guide](./events_upcasting.md).

## Testing Strategy

When testing with the new structure, prefer using the in-memory implementations:

```python
from uno.events.implementations.bus import InMemoryEventBus
from uno.events.implementations.store import InMemoryEventStore
from uno.commands.implementations.structural_bus import StructuralCommandBus

# Create test instances
event_bus = InMemoryEventBus(logger=mock_logger, config=mock_config)
event_store = InMemoryEventStore(logger=mock_logger)
command_bus = StructuralCommandBus(logger=mock_logger)
```

## Configuration Updates

The events configuration now supports proper type hints:

```python
from uno.events.config import EventsConfig

# Create a configuration with explicit settings
config = EventsConfig(
    event_bus_type="postgres",
    event_store_type="postgres",
    db_connection_string="postgresql://user:pass@localhost:5432/mydb"
)
```

## Next Steps

1. Update imports in your codebase following this guide
2. Replace inheritance with structural typing where applicable
3. Update DI container registrations
4. Test your application with both in-memory and Postgres implementations
5. Follow the Uno idioms for modern Python type hints
