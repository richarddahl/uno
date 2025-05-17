# Uno Error System – Developer Guide

## Architecture
- All errors derive from `UnoError`, which enforces explicit subclassing and structured context.
- Error categories and severity are enums for type safety.
- No error factories or helpers—instantiation is always direct.

## Extending the Error System
- Subclass `UnoError` for new error types.
- Use descriptive codes and messages.
- Add custom context fields as needed.

## Testing Errors
- Use pytest for all error tests.
- Test context propagation, especially across async/threaded boundaries.
- Use `Fake` or `Mock` prefixes for test error classes.

## Example Test
```python
def test_my_error():
    err = MyDomainError("fail", {"foo": 1})
    assert err.code == "MY_DOMAIN_ERROR"
    assert err.context["foo"] == 1
```

## Internal API
- `UnoError.with_context(context)`: Returns new error with merged context.
- `UnoError.wrap(exception, ...)`: Wraps another exception as UnoError.
- `UnoError.to_dict()`: Serializes error for logging or APIs.
- `get_error_context()`: Utility for capturing call-site info.

## Migration Notes
- No use of error factories or legacy helpers.
- All error creation is explicit and subclass-based.
