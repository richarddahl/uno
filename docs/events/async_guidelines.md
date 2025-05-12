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

## Concurrency Patterns

### Batched Processing

For high-throughput scenarios, use the batched processing pattern:

```python
async def process_events(events: list[DomainEvent], batch_size: int = 10) -> None:
    """Process events in batches for better concurrency control."""
    for i in range(0, len(events), batch_size):
        batch = events[i : i + batch_size]
        tasks = [process_event(event) for event in batch]
        # Process batch concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
```

### Task Management

When creating tasks that will run in the background:

```python
async def start_background_processing() -> None:
    """Start background event processing."""
    # Store the task so it can be cancelled later if needed
    task = asyncio.create_task(process_events_continuously())
    # Optionally add error handling
    task.add_done_callback(handle_task_completion)
    return task
```

### Handling Exceptions in Gathered Tasks

When using `asyncio.gather()` with event handlers:

```python
async def publish_events(events: list[DomainEvent]) -> None:
    """Publish multiple events with proper exception handling."""
    tasks = [self.publish(event) for event in events]
    # Gather with return_exceptions=True to handle errors after all tasks complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process any exceptions after all tasks have completed
    for result in results:
        if isinstance(result, Exception):
            # Log or handle the exception
            await self.logger.error("Error in event handler", error=str(result))
```

## Performance Considerations

### Use Concurrent Processing Wisely

- Use `asyncio.gather()` for independent operations that can run concurrently
- Use batched processing to control resource usage in high-volume scenarios
- Consider implementing backpressure mechanisms for event processing pipelines

### Avoid Blocking Operations

- Never use `time.sleep()` in async code; use `await asyncio.sleep()` instead
- Avoid synchronous I/O operations like file reads/writes in event handlers
- Use asynchronous database drivers and client libraries

### Database Connection Management

- Use connection pooling for database operations
- Release connections back to the pool as soon as possible
- Consider using a per-request or per-context connection pattern

## Testing Async Event Handlers

- Use `asyncio.run()` for simple test cases
- Use pytest's `pytest-asyncio` plugin for more complex testing
- Mock async dependencies with libraries like `asyncmock`
- Test concurrency behavior using controlled scenarios with multiple events
