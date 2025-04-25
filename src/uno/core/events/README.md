# Uno Event Sourcing & Domain Events

Uno's event sourcing system provides a robust, production-ready foundation for building scalable, maintainable, and auditable applications using Domain-Driven Design (DDD) principles.

## Key Features

- **Event Sourcing**: All state changes are captured as immutable domain events.
- **Aggregate Roots**: Central entry point for all domain state changes, using canonical event emission and replay.
- **Event Stores**: Pluggable in-memory and Postgres event store implementations.
- **Event Bus**: Decoupled, DI-friendly event publication and subscription.
- **Repository Pattern**: Event-sourced repositories for aggregate persistence and rehydration.
- **Modern Python**: Fully typed, Pydantic 2, Python 3.13, DI, monad-based error handling.
- **Comprehensive Testing**: Full suite of unit and integration tests.

## Quickstart

1. **Define a Domain Event**

   ```python
   from uno.core.events.events import DomainEvent
   class UserRegistered(DomainEvent):
       event_type: str = "user_registered"
       user_id: str
       email: str
   ```

2. **Define an Aggregate**

   ```python
   from uno.core.domain.core import AggregateRoot
   class User(AggregateRoot):
       ...
       def register(self, email: str):
           event = UserRegistered(user_id=self.id, email=email)
           self.add_event(event)
       def apply_user_registered(self, event: UserRegistered):
           self.email = event.email
   ```

3. **Use the EventSourcedRepository**

   ```python
   repo = EventSourcedRepository(User, event_store, event_publisher, logger)
   user = User()
   user.register("foo@bar.com")
   await repo.add(user)
   loaded = await repo.get_by_id(user.id)
   ```

## Design Principles

- **Loose Coupling**: All event handling and persistence is DI-based.
- **Testability**: In-memory store for fast tests, Postgres for integration.
- **Extensibility**: Add new event types, stores, and buses with minimal effort.
- **Observability**: Structured, centralized logging throughout.

See [`docs/events/dev.md`](./dev.md) for deep dives and advanced usage.
