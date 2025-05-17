# Unit of Work Pattern

This module provides an implementation of the Unit of Work pattern for managing transactions and atomic operations in a domain-driven design.

## Features

- **Transaction Management**: Support for atomic operations across multiple aggregates and repositories.
- **Nested Transactions**: Support for nested transactions using savepoints.
- **Optimistic Concurrency Control**: Version-based concurrency control to prevent conflicts.
- **Redis Integration**: Built-in support for Redis as a backend store.
- **Dependency Injection**: Seamless integration with the Uno dependency injection system.

## Components

### UnitOfWork

The base `UnitOfWork` class provides the core functionality for managing transactions and tracking changes to aggregates.

```python
class UnitOfWork(Generic[A, E], ABC):
    """Base class for Unit of Work implementations."""
    
    async def begin(self) -> None:
        """Begin a new transaction."""
        ...
    
    async def commit(self) -> None:
        """Commit the current transaction."""
        ...
    
    async def rollback(self) -> None:
        """Roll back the current transaction."""
        ...
    
    def get_repository(self, aggregate_type: Type[A]) -> RepositoryProtocol[A]:
        """Get a repository for the given aggregate type."""
        ...
```

### RedisUnitOfWork

A Redis-based implementation of the `UnitOfWork` interface.

```python
class RedisUnitOfWork(UnitOfWork[A, E], Generic[A, E]):
    """Redis implementation of the Unit of Work pattern."""
    
    def __init__(
        self,
        container: ContainerProtocol,
        redis: Redis[bytes] | RedisCluster[bytes],
        isolation_level: str = "read_committed",
        logger: LoggerProtocol | None = None,
    ) -> None:
        ...
```

### RedisRepository

A Redis-based implementation of the `RepositoryProtocol` interface.

```python
class RedisRepository(RepositoryProtocol[A], Generic[A]):
    """Redis implementation of the repository pattern."""
    
    def __init__(
        self,
        aggregate_type: Type[A],
        redis: Redis[bytes] | RedisCluster[bytes],
        logger: LoggerProtocol | None = None,
    ) -> None:
        ...
```

## Usage

### Basic Usage

```python
import asyncio
from uuid import uuid4

from redis.asyncio import Redis

from uno.uow import RedisUnitOfWork
from uno.domain.aggregate import AggregateRoot
from uno.domain.events import DomainEvent

# Define your aggregate and event types
class MyEvent(DomainEvent):
    value: str

class MyAggregate(AggregateRoot[MyEvent]):
    def __init__(self, id: UUID):
        super().__init__(id)
        self.value = ""
    
    def apply_event(self, event: MyEvent) -> None:
        self.value = event.value

async def main():
    # Create a Redis client
    redis = Redis.from_url("redis://localhost:6379/0")
    
    # Create a unit of work
    uow = RedisUnitOfWork[MyAggregate, MyEvent](
        container=container,  # Your DI container
        redis=redis,
    )
    
    # Use the unit of work
    async with uow:
        # Get a repository for MyAggregate
        repo = uow.get_repository(MyAggregate)
        
        # Create and save an aggregate
        aggregate = MyAggregate(uuid4())
        event = MyEvent(aggregate_id=str(aggregate.id), version=1, value="test")
        aggregate._apply_event(event)
        
        await repo.add(aggregate)
        
        # The transaction will be committed when the context exits
    
    # Close the Redis connection
    await redis.close()

asyncio.run(main())
```

### Nested Transactions

```python
async def process_order(uow: UnitOfWork[Order, OrderEvent]):
    async with uow:
        # Outer transaction
        order = await uow.get_repository(Order).get(order_id)
        
        # Nested transaction
        async with uow.transaction():
            # This is a savepoint
            order.add_item(item_id, quantity)
            
            # If something fails here, only the nested transaction is rolled back
            await process_payment(order)
        
        # Continue with the outer transaction
        await send_confirmation(order)
        # The outer transaction is committed when the outer context exits
```

## Error Handling

The following exceptions may be raised by the Unit of Work:

- `ConcurrencyError`: Raised when a concurrency conflict is detected.
- `OptimisticConcurrencyError`: Raised when an optimistic concurrency check fails.
- `UnitOfWorkError`: Base class for all Unit of Work related errors.
- `RepositoryError`: Raised when a repository operation fails.
- `TransactionError`: Raised when a transaction operation fails.

## Configuration

The following configuration options are available for the Redis Unit of Work:

- `isolation_level`: The isolation level for transactions. Defaults to "read_committed".
- `logger`: A logger instance. If not provided, a default logger will be used.

## Testing

Unit tests for the Redis Unit of Work can be found in `tests/unit/uow/test_redis_unit_of_work.py`.

## License

This module is part of the Uno framework and is licensed under the MIT License.
