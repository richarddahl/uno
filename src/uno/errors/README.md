# Uno Error Handling System

Uno provides a modern, robust, and idiomatic error handling system designed for scalable, maintainable applications. It enforces explicit error types, structured context, and clear error categories, with strong typing and testability.

## Philosophy
- **Explicit, typed errors:** All errors are subclasses of `UnoError`, never generic exceptions.
- **Structured context:** Errors carry rich, structured context for diagnostics and observability.
- **No factories:** Errors are instantiated directly from subclasses, not via factories or helpers.
- **Enum-based classification:** Error category and severity are always enums (`ErrorCategory`, `ErrorSeverity`).

## Key Concepts
- `UnoError`: Abstract base error, never instantiated directly. Subclass for all concrete errors.
- `ErrorCategory`: Enum for error classification (INTERNAL, CONFIG, DB, API, etc).
- `ErrorSeverity`: Enum for severity (INFO, WARNING, ERROR, CRITICAL, FATAL).
- Context: Arbitrary metadata attached to errors for traceability.

## Usage Example
```python
from uno.errors.base import UnoError, ErrorCategory, ErrorSeverity

class MyAppError(UnoError):
    def __init__(self, message: str, context: dict[str, object] | None = None):
        super().__init__(
            code="MY_APP_ERROR",
            message=message,
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.ERROR,
            context=context,
        )

# Raising with context
def do_something():
    raise MyAppError("Something failed", {"user_id": 42})
```

## Best Practices
- Always subclass `UnoError` for new error types.
- Use `with_context` to enrich errors as they propagate.
- Use enums for category/severity, never magic strings.
- Use `wrap` to convert exceptions from other libraries.
- Test error propagation, especially across async/thread boundaries.

See the [docs/errors](../../../docs/errors) for user and developer guides.
