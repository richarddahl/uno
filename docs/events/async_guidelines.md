# Async Guidelines for Event Handling

This document provides guidelines for when methods should be asynchronous versus synchronous in the Uno event system.

## General Principles

1. **Event Handlers Are Always Async**: All event handlers should use async patterns to allow for potentially long-running operations, database access, or network calls.

2. **Event Publishing Is Always Async**: Any method that publishes events should be async to allow for properly awaiting the completion of all handler executions.

3. **Middleware Processing Is Always Async**: All middleware components should use async patterns for consistent integration with the event handling pipeline.

4. **Read Operations Can Be Sync or Async**: Methods that only read data (e.g., getting registered handlers) can be synchronous if they don't perform I/O operations.

5. **Registration Operations Are Typically Sync**: Methods for registering handlers or middleware are typically synchronous as they usually only modify in-memory state.

## Specific Guidelines

### Always Async

- Event handler `handle()` methods
- Middleware `process()` methods
- `EventBus.publish()` and `EventBus.publish_many()`
- `EventPublisher.publish()` and `EventPublisher.publish_many()`
- Event store read/write operations that involve database access
- Any method that may perform I/O, network calls, or long-running operations

### Typically Sync

- Registration methods like `register_handler()`, `register_middleware()`
- Configuration methods
- Builder pattern methods that return configuration objects
- Methods that only read in-memory data structures

## Adapter Pattern

When integrating with external code that may provide sync handlers:

1. Use the `AsyncEventHandlerAdapter` to wrap both sync and async handlers
2. The adapter handles the appropriate execution strategy based on the handler type
3. All handlers appear async to the event system, maintaining consistency

## Error Handling

- Always use the Result monad for both sync and async methods
- Async methods return `Awaitable[Result[T, Exception]]`
- Sync methods return `Result[T, Exception]`
