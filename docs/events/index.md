# Uno Event Sourcing: Developer Guide

## Architectural Overview

Uno's event sourcing module is built on modern DDD and Python best practices:

- **DomainEvent**: Canonical, Pydantic-based event model.
- **AggregateRoot**: All state changes via events; supports `add_event`, `apply_event`, and `from_events`.
- **EventSourcedRepository**: Generic, DI-ready repository for event-sourced aggregates.
- **EventBus/EventPublisher**: Decoupled, DI-friendly event publication/subscription.
- **EventStore**: Pluggable, async event stores (in-memory, Postgres).

## AggregateRoot Pattern

- **State changes only via events:**
  - Use `add_event(event)` in aggregate methods (never mutate state directly).
  - Implement `apply_<event_type>` for each event type.
  - Use `from_events(events)` to rehydrate aggregate state.

### AggregateRoot Example

```python
class User(AggregateRoot):
    email: str | None = None
    def register(self, email: str):
        self.add_event(UserRegistered(user_id=self.id, email=email))
    def apply_user_registered(self, event: UserRegistered):
        self.email = event.email
```

## EventSourcedRepository Pattern

- **add(entity)**: Persists and publishes new events from an aggregate (calls `clear_events()` after).
- **get_by_id(id)**: Loads all events for aggregate, rehydrates via `from_events`.
- **list()**: Loads all events of type, groups by aggregate ID, rehydrates all.
- **remove(id)**: (Soft delete pattern—emit a `Deleted` event, not physical delete.)

### EventSourcedRepository Example

```python
repo = EventSourcedRepository(User, event_store, event_publisher, logger)
user = User()
user.register("foo@bar.com")
await repo.add(user)
loaded = await repo.get_by_id(user.id)
```

## Event Store Implementations

- **InMemoryEventStore**: Fast, for testing/dev.
- **PostgresEventStore**: Production-ready, asyncpg+SQLAlchemy, robust integration tests.

## Event Bus & Publisher

- **EventBus**: DI-friendly, supports priorities, topic patterns, async handlers.
- **EventPublisher**: Collects and publishes events in batches.

## Testing

- 100% coverage for all event sourcing logic.
- Integration tests for Postgres store (requires `TEST_DB_URL`).

## Advanced Topics

- **Snapshots**: (Planned) For large aggregates, implement periodic snapshots.
- **Versioning**: Event/aggregate version support for concurrency.
- **Error Handling**: Monad-based errors, structured logging.
- **[Event Upcasting](./events_upcasting.md)**: Strategies for event schema evolution.
- **[Async Guidelines](./async_guidelines.md)**: Best practices for async event handling.

## Migration Guide

- Remove all legacy event code.
- Refactor aggregates to use only `add_event` and `apply_*`.
- Use DI for all event stores, buses, and loggers.
- See the detailed [Migration Guide](./migration_guide.md) for step-by-step instructions.

## Reference

- **[Event Handler Discovery](./EVENT_HANDLER_DISCOVERY.md)**: Automatic event handler registration.
- **[Event Files Inventory](../../EVENT_FILES.md)**: Detailed inventory of all event system files.
- **[Event Symbols Inventory](../../EVENT_SYMBOLS.md)**: Complete catalog of event system symbols.

See the main [README.md](./README.md) for a quickstart and high-level overview.
