# Uno Framework - Code Duplication Checklist

## 1. In-Memory Store Implementations

### 1.1 Dictionary Storage Pattern
- [ ] `InMemoryEventStore` (persistence/event_sourcing/implementations/memory/event_store.py)
  - `self._events: dict[str, list[E]] = {}`
- [ ] `InMemorySagaStore` (sagas/memory.py)
  - `self._store: dict[str, SagaState] = {}`
- [ ] `InMemoryProjectionStore` (projections/memory.py)
  - `self._store: Dict[str, T] = {}`
- [ ] `InMemorySnapshotStore` (snapshots/implementations/memory/snapshot.py)
  - `_snapshots: ClassVar[Dict[str, List[Snapshot]]] = {}`

### 1.2 CRUD Operations
- [ ] `get`/`load` methods across all in-memory stores
- [ ] `save`/`store` methods across all in-memory stores
- [ ] `delete`/`remove` methods across all in-memory stores
- [ ] `clear` methods where implemented

## 2. PostgreSQL Store Implementations

### 2.1 Connection Management
- [ ] `PostgresEventStore` (persistence/event_sourcing/implementations/postgres/event_store.py)
  - Connection handling in each method
- [ ] `PostgresSagaStore` (persistence/event_sourcing/implementations/postgres/saga_store.py)
  - Connection handling in each method
- [ ] `PostgresSnapshotStore` (snapshots/implementations/postgres/snapshot.py)
  - Connection pool handling

### 2.2 Table Initialization
- [ ] Table creation SQL in each Postgres store
- [ ] Index creation patterns
- [ ] Schema migration logic

## 3. Event/Command Buses

### 3.1 Initialization
- [ ] `InMemoryEventBus` (persistence/event_sourcing/implementations/memory/bus.py)
  - Logger setup
  - Handler registration
- [ ] `InMemoryCommandBus` (commands/implementations/memory_bus.py)
  - Logger setup
  - Handler registration

### 3.2 Message Handling
- [ ] Publish/subscribe patterns
- [ ] Error handling in message dispatch
- [ ] Middleware application

## 4. Middleware Implementations

### 4.1 Logging Middleware
- [ ] `LoggingMiddleware` in events/implementations/handlers/middleware.py
- [ ] Similar logging in command handlers

### 4.2 Timing Middleware
- [ ] `TimingMiddleware` in events/implementations/handlers/middleware.py
- [ ] Similar timing logic in other middleware

## 5. Protocol Definitions

### 5.1 Store Protocols
- [ ] `EventStoreProtocol`
- [ ] `SagaStoreProtocol`
- [ ] `SnapshotStoreProtocol`
- [ ] Common CRUD operations

### 5.2 Handler Protocols
- [ ] `EventHandlerProtocol`
- [ ] `CommandHandlerProtocol`
- [ ] Common handler patterns

## 6. Error Handling

### 6.1 Custom Exceptions
- [ ] Duplicate error types across packages
- [ ] Similar error handling patterns

### 6.2 Error Context
- [ ] Error context propagation
- [ ] Error logging patterns

## 7. Configuration

### 7.1 Store Configuration
- [ ] Connection configuration
- [ ] Retry policies
- [ ] Timeout settings

### 7.2 Bus Configuration
- [ ] Handler registration
- [ ] Middleware configuration

## 8. Testing Utilities

### 8.1 Test Fixtures
- [ ] Common test setup/teardown
- [ ] Test data generation

### 8.2 Assertion Helpers
- [ ] Common assertion patterns
- [ ] Verification utilities

## 9. Serialization/Deserialization

### 9.1 Event Serialization
- [ ] JSON serialization/deserialization
- [ ] Type conversion

### 9.2 Snapshot Serialization
- [ ] State serialization
- [ ] Version handling

## 10. Common Utilities

### 10.1 ID Generation
- [ ] UUID generation
- [ ] ID validation

### 10.2 Date/Time Handling
- [ ] Timestamp generation
- [ ] Timezone handling
