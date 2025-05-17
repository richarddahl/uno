# Dead Letter Queue

The `DeadLetterQueue` is a critical component for handling failed events in an event-driven architecture. It provides a robust mechanism to capture, manage, and retry events that couldn't be processed successfully.

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Basic Usage](#basic-usage)
- [Retry Policies](#retry-policies)
- [Metrics and Monitoring](#metrics-and-monitoring)
- [Error Handling](#error-handling)
- [API Reference](#api-reference)
- [Best Practices](#best-practices)

## Overview

The `DeadLetterQueue` captures events that fail processing and provides tools to manage them, including:

- Automatic retry of failed events
- Configurable retry policies
- Metrics and monitoring integration
- Event replay capabilities

## Key Features

- **Automatic Dead Letter Capture**: Failed events are automatically captured with detailed error information.
- **Configurable Retry Policies**: Built-in support for various retry strategies, including exponential backoff.
- **Metrics Integration**: Comprehensive metrics for monitoring dead-lettered events.
- **Type Safety**: Full type hints and Pydantic model support.
- **Extensible**: Easy to extend with custom retry policies and handlers.

## Basic Usage

### Creating a DeadLetterQueue

```python
from uno.event_bus.dead_letter import DeadLetterQueue, DeadLetterReason
from uno.metrics import Metrics

# Initialize with metrics
metrics = Metrics.get_instance()
dead_letter_queue = DeadLetterQueue(metrics=metrics)
```

### Adding a Failed Event

```python
from pydantic import BaseModel

class OrderEvent(BaseModel):
    order_id: str
    amount: float

try:
    # Event processing that might fail
    process_event(event)
except Exception as e:
    await dead_letter_queue.add(
        event=event,
        reason=DeadLetterReason.HANDLER_FAILED,
        error=e,
        subscription_id="order_processor",
        attempt_count=1
    )
```

### Processing Dead Letters

```python
async def handle_dead_letter(dead_event):
    print(f"Processing dead letter: {dead_event.id}")
    # Your custom processing logic here

# Add handler
dead_letter_queue.add_handler(handle_dead_letter)

# Process dead letters
await dead_letter_queue.process()
```

## Retry Policies

The `DeadLetterQueue` supports configurable retry policies. By default, it uses an exponential backoff strategy.

### Default Retry Policy

```python
# Default policy: exponential backoff with max 5 attempts
default_policy = dead_letter_queue.get_retry_policy()
```

### Custom Retry Policy

```python
def custom_retry_policy(attempt: int) -> float | None:
    if attempt > 3:  # Max 3 retries
        return None
    return 2 ** attempt  # Exponential backoff in seconds

dead_letter_queue.set_retry_policy(custom_retry_policy, max_attempts=3)
```

## Metrics and Monitoring

The `DeadLetterQueue` integrates with the `unometrics` system to provide detailed metrics:

- `event.dead_lettered`: Counter for dead-lettered events
- `event.dead_letter.retry`: Counter for retry attempts
- `event.dead_letter.processed`: Counter for processed dead letters
- `event.dead_letter.error`: Counter for processing errors

### Example Metrics

```python
# Accessing metrics
metrics = Metrics.get_instance()
metrics.increment("event.dead_lettered", tags={"reason": "handler_failed"})
```

## Error Handling

The `DeadLetterQueue` provides detailed error information through `DeadLetterEvent`:

```python
class DeadLetterEvent(BaseModel):
    id: str
    event_data: dict
    reason: DeadLetterReason
    error: str | None
    timestamp: datetime
    subscription_id: str | None
    attempt_count: int
    metadata: dict
```

## API Reference

### DeadLetterQueue

#### `__init__(self, metrics: Metrics | None = None)`
Initialize a new DeadLetterQueue.

#### `async add(self, event: E | dict, reason: DeadLetterReason, error: Exception | None = None, subscription_id: str | None = None, attempt_count: int = 1, **metadata: Any) -> None`
Add a failed event to the dead letter queue.

#### `add_handler(self, handler: Callable[[DeadLetterEvent[E]], Awaitable[None]]) -> str`
Add a handler for processing dead letters.

#### `remove_handler(self, handler_id: str) -> None`
Remove a handler by its ID.

#### `clear_handlers(self) -> None`
Remove all handlers.

#### `async process(self, max_attempts: int = 5, retry_delay: float = 1.0) -> None`
Process all dead letters in the queue.

#### `set_retry_policy(self, policy: Callable[[int], float | None], max_attempts: int = 5) -> None`
Set a custom retry policy.

### DeadLetterReason

Enum of possible reasons for dead-lettering:
- `HANDLER_FAILED`: Event handler raised an exception
- `TIMEOUT`: Event processing timed out
- `INVALID_EVENT`: Event validation failed
- `UNHANDLED`: No handler was found for the event
- `UNKNOWN`: Unknown error occurred

## Best Practices

1. **Monitor Dead Letters**: Set up alerts for dead-lettered events to detect issues early.
2. **Implement Meaningful Retry Policies**: Use exponential backoff to prevent overwhelming your system.
3. **Log Thoroughly**: Include sufficient context in error messages for debugging.
4. **Clean Up**: Periodically clean up processed dead letters to prevent unbounded growth.
5. **Test Failure Scenarios**: Ensure your system can handle and recover from dead-letter scenarios.

## Example: Complete Workflow

```python
import asyncio
from datetime import datetime, timezone
from pydantic import BaseModel
from uno.event_bus.dead_letter import DeadLetterQueue, DeadLetterReason
from uno.metrics import Metrics

class OrderEvent(BaseModel):
    order_id: str
    amount: float
    timestamp: datetime = datetime.now(timezone.utc)

async def main():
    # Setup
    metrics = Metrics.get_instance()
    dlq = DeadLetterQueue[OrderEvent](metrics=metrics)
    
    # Add a handler
    async def process_dead_letter(event):
        print(f"Processing dead letter: {event.id}")
        print(f"Event data: {event.event_data}")
        print(f"Error: {event.error}")
        print(f"Attempt: {event.attempt_count}")
        
        # Simulate success after 2 attempts
        if event.attempt_count < 2:
            raise ValueError("Simulated processing error")
            
        print("Successfully processed dead letter")
    
    dlq.add_handler(process_dead_letter)
    
    # Simulate a failed event
    event = OrderEvent(order_id="123", amount=100.0)
    
    # Add to dead letter queue
    await dlq.add(
        event=event,
        reason=DeadLetterReason.HANDLER_FAILED,
        error=ValueError("Payment processing failed"),
        subscription_id="payment_processor",
        attempt_count=1
    )
    
    # Process dead letters with retries
    await dlq.process(max_attempts=3, retry_delay=0.5)

if __name__ == "__main__":
    asyncio.run(main())
```

## Troubleshooting

### Common Issues

1. **Events Not Being Processed**
   - Verify handlers are properly registered
   - Check for unhandled exceptions in handlers
   - Ensure the event loop is running when calling `process()`

2. **Memory Issues**
   - The queue is in-memory by default
   - Implement a persistence layer for production use
   - Consider limiting queue size

3. **Metrics Not Showing Up**
   - Verify metrics configuration
   - Check for exceptions in metric collection
   - Ensure proper metric names and tags are used
