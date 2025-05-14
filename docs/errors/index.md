# Uno Error System

Uno's error system provides robust, explicit, and testable error handling for modern Python applications.

- All errors derive from `UnoError` (never instantiate directly).
- Errors use structured context for diagnostics.
- Classification and severity use enums, not strings.
- Designed for async/thread safety and observability.

## Quickstart

```python
from uno.errors.base import UnoError, ErrorCategory, ErrorSeverity

class CustomError(UnoError):
    def __init__(self, message: str, context: dict[str, object] | None = None):
        super().__init__(
            code="CUSTOM_ERROR",
            message=message,
            category=ErrorCategory.API,
            severity=ErrorSeverity.ERROR,
            context=context,
        )

try:
    raise CustomError("Oops!", {"foo": "bar"})
except CustomError as err:
    print(err.to_dict())
```

- See [User Guide](user_guide.md) for practical usage.
- See [Developer Guide](developer_guide.md) for extending/testing the system.
