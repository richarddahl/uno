# Uno Framework - Detailed Code Duplication Report

| Symbol Name | Duplicate Locations | Canonical Location | Fixed (✓/✗) |
|------------|-------------------|-------------------|------------|
| `InMemoryEventStore._events` | `persistence.event_sourcing.implementations.memory.event_store.InMemoryEventStore` | `persistence.base.InMemoryStore` | ✓ |
| `InMemorySagaStore._store` | `sagas.memory.InMemorySagaStore` | `persistence.base.InMemoryStore` | ✗ |
| `InMemoryProjectionStore._store` | `projections.memory.InMemoryProjectionStore` | `persistence.base.InMemoryStore` | ✗ |
| `InMemorySnapshotStore._snapshots` | `snapshots.implementations.memory.snapshot.InMemorySnapshotStore` | `persistence.base.InMemoryStore` | ✗ |
| `get`/`load` method | - `projections.memory.InMemoryProjectionStore.get`<br>- `sagas.memory.InMemorySagaStore.load_state` | `persistence.base.InMemoryStore` | ✗ |
| `save`/`store` method | - `projections.memory.InMemoryProjectionStore.save`<br>- `sagas.memory.InMemorySagaStore.save_state` | `persistence.base.InMemoryStore` | ✗ |
| `delete`/`remove` method | - `projections.memory.InMemoryProjectionStore.delete`<br>- `sagas.memory.InMemorySagaStore.delete_state` | `persistence.base.InMemoryStore` | ✗ |
| `PostgresEventStore` connection handling | `persistence.event_sourcing.implementations.postgres.event_store.PostgresEventStore` | `persistence.base.PostgresStore` | ✗ |
| `PostgresSagaStore` connection handling | `persistence.event_sourcing.implementations.postgres.saga_store.PostgresSagaStore` | `persistence.base.PostgresStore` | ✗ |
| `PostgresSnapshotStore` connection handling | `snapshots.implementations.postgres.snapshot.PostgresSnapshotStore` | `persistence.base.PostgresStore` | ✗ |
| Table creation SQL | - `PostgresEventStore._create_event_table()`<br>- `PostgresSagaStore.initialize()`<br>- `PostgresSnapshotStore.initialize()` | `persistence.base.PostgresStore` | ✗ |
| `InMemoryEventBus.__init__` | `persistence.event_sourcing.implementations.memory.bus.InMemoryEventBus` | `messaging.base.MessageBus` | ✗ |
| `InMemoryCommandBus.__init__` | `commands.implementations.memory_bus.InMemoryCommandBus` | `messaging.base.MessageBus` | ✗ |
| `LoggingMiddleware` | `events.implementations.handlers.middleware.LoggingMiddleware` | `middleware.base.LoggingMiddleware` | ✗ |
| `TimingMiddleware` | `events.implementations.handlers.middleware.TimingMiddleware` | `middleware.base.TimingMiddleware` | ✗ |
| `EventStoreProtocol` methods | - `save_events`<br>- `get_events` | `persistence.protocols.StoreProtocol` | ✗ |
| `SagaStoreProtocol` methods | - `save_state`<br>- `load_state` | `persistence.protocols.StoreProtocol` | ✗ |
| `SnapshotStoreProtocol` methods | - `save_snapshot`<br>- `get_latest_snapshot` | `persistence.protocols.StoreProtocol` | ✗ |
| Error handling patterns | - `EventPublishError`<br>- `CommandDispatchError` | `errors.base` | ✗ |
| Logger initialization | - `InMemoryEventBus`<br>- `InMemoryCommandBus`<br>- `PostgresEventStore` | `core.logging.with_logger` | ✗ |
| UUID generation | - `events.base`<br>- `sagas.base` | `core.utils.ids` | ✗ |
| Timestamp generation | - `events.base`<br>- `sagas.base` | `core.utils.time` | ✗ |
