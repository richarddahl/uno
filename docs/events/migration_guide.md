# Event Package Migration Guide

This document provides guidance for migrating from the previous event package structure to the new, refactored structure.

## Breaking Changes

1. **Package Structure Changes**
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
