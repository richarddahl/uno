# Event Store Error Handling

Uno's event store implementations provide a consistent error handling system with specific error types for different scenarios.

## Error Types

### EventStoreError

Base class for all event store-related errors. Contains common fields:

- `message`: The error message
- `code`: The error code (e.g., "EVENT_STORE_ERROR")
- `severity`: The error severity level
- `context`: Additional context information about the error

### EventStoreConnectError

Raised when there's an issue connecting to the event store.

Common context fields:

- `url`: The connection URL
- `dsn`: The database connection string
- `db_path`: The database path
- `status`: Connection status (e.g., "disconnected")
- `error`: Detailed error message

Example:

```python
try:
    await store.connect()
except EventStoreConnectError as e:
    print(f"Connection failed: {e}")
    print(f"Context: {e.context}")
```

### EventStoreTransactionError

Raised when there's an issue during a database transaction.

Common context fields:

- `dsn`: The database connection string
- `db_path`: The database path
- `status`: Transaction status
- `error`: Detailed error message

Example:

```python
try:
    async with store._transaction():
        # Transaction operations
        pass
except EventStoreTransactionError as e:
    print(f"Transaction failed: {e}")
    print(f"Context: {e.context}")
```

### EventStoreSearchError

Raised when there's an issue during a search operation.

Common context fields:

- `query`: The search query
- `db_path`: The database path
- `error`: Detailed error message

Example:

```python
try:
    async for event in store.search_events("test query"):
        # Process events
        pass
except EventStoreSearchError as e:
    print(f"Search failed: {e}")
    print(f"Context: {e.context}")
```

## Error Context

All error types include a `context` dictionary that provides additional information about the error. This can be used for logging, debugging, or error reporting.

Example:

```python
try:
    await store.connect()
except EventStoreError as e:
    if "dsn" in e.context:
        print(f"Connection string: {e.context['dsn']}")
    if "error" in e.context:
        print(f"Detailed error: {e.context['error']}")
```

## Best Practices

1. Always handle specific error types when possible:

```python
try:
    # Operation
except EventStoreConnectError:
    # Handle connection error
except EventStoreTransactionError:
    # Handle transaction error
```

1. Use error context for debugging:

```python
try:
    # Operation
except EventStoreError as e:
    logger.error(f"Error occurred: {e}", extra={"context": e.context})
```

1. Provide meaningful error messages:

```python
raise EventStoreConnectError(
    "Failed to connect to database",
    context={
        "dsn": dsn,
        "error": str(e),
        "status": "disconnected",
    }
)
