# Uno Error System – User Guide

## Creating and Raising Errors
- Subclass `UnoError` for all new error types.
- Provide a unique code, human-readable message, category, and severity.
- Attach context for traceability (e.g., user IDs, operation IDs).

```python
class MyDomainError(UnoError):
    def __init__(self, message: str, context: dict[str, object] | None = None):
        super().__init__(
            code="MY_DOMAIN_ERROR",
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.ERROR,
            context=context,
        )
raise MyDomainError("Invalid input", {"input": "bad_value"})
```

## Enriching and Propagating Context
- Use `with_context` to add/merge context as errors bubble up.
- Use `wrap` to convert third-party exceptions into Uno errors.

```python
try:
    ...
except Exception as exc:
    raise MyDomainError.wrap(exc, "MY_WRAP", "Wrapped error", ErrorCategory.INTERNAL, ErrorSeverity.ERROR)
```

## Handling Errors in Async/Threaded Code
- Context is preserved across async/thread boundaries if you propagate the error object.
- Always test error context in these scenarios.

## Inspecting Errors
- Use `.to_dict()` to serialize errors for logs or APIs.
- All context, category, and severity are included.

## Best Practices
- Never instantiate `UnoError` directly.
- Use enums, not strings, for classification.
- Always enrich error context for observability.
