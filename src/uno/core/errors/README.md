# uno.core.errors

Comprehensive error handling framework for the Uno application.

## Modules

- **__init__.py**: Package entrypoint; re-exports public API and registers core errors on import.
- **base.py**: Defines `FrameworkError`, error-context utilities (`get_error_context`, `add_error_context`), context managers/decorators (`with_error_context`, `with_async_error_context`), and core enums/types (`ErrorCode`, `ErrorCategory`, `ErrorSeverity`, `ErrorInfo`).
- **catalog.py**: Central registry for error metadata; provides `ErrorCatalog`, `register_error()`, and lookup helpers (`get_error_code_info()`, `get_all_error_codes()`).
- **core_errors.py**: Core framework error definitions:
  - `CoreErrorCode` constants (config, init, dependency, object, serialization, protocol, general).
  - `FrameworkError` subclasses (e.g. `ConfigNotFoundError`, `InitializationError`, `DependencyCycleError`, etc.)
  - Automatic registration of each code via the catalog.
- **security.py**: Security-related errors: `AuthenticationError` and `AuthorizationError`.
- **validation.py**: Validation utilities:
  - `FieldValidationError` for single-field errors.
  - `ValidationContext` to collect nested validation errors.
  - `ValidationError` exception and top-level `validate_fields()` helper.
- **result.py**: Result/Either monad implementation:
  - `Result[T]`, `Success[T]`, `Failure[T]`.
  - Helpers: `of()`, `failure()`, `from_exception()`, `from_awaitable()`, `combine()`, `combine_dict()`.
- **logging.py**: Structured logging support:
  - `LogConfig` for runtime configuration.
  - `StructuredLogAdapter` and `StructuredJsonFormatter`.
  - Context helpers (`add_logging_context`, `with_logging_context`).
- **examples.py**: Usage examples (FastAPI routes demonstrating `FrameworkError`, error contexts, and the Result API). Not part of production code.
- **py.typed**: Marker file indicating PEP 561 compliance for type checkers.

## Quick Start

```python
from uno.core.errors import FrameworkError, ErrorCode, with_error_context
from uno.core.errors import Success, Failure, from_exception

@with_error_context
def foo(x: int):
    if x < 0:
        raise FrameworkError(
            "Negative value", 
            error_code=ErrorCode.VALIDATION_ERROR, 
            value=x
        )
    return x
```  

## Error Context

Use context managers or decorators to attach context to all errors automatically:

```python
from uno.core.errors.base import with_error_context, with_async_error_context

# Synchronous
with with_error_context(user_id="42"):
    ...

# Asynchronous
async with with_async_error_context(order_id="abc"):
    ...
```

## Result Pattern

```python
from uno.core.errors.result import from_exception

@from_exception
def safe_div(a: int, b: int) -> int:
    return a // b

result = safe_div(10, 0)
if result.is_failure:
    print("Error:", result.error)
```  

## Structured Logging

```python
from uno.core.errors.logging import configure_logging, get_logger, with_logging_context

configure_logging()
logger = get_logger(__name__)

with_logging_context(request_id="xyz"):
    logger.info("Handling request")
```

## License

This package is provided under the MIT License. See the root `LICENSE` file for full terms.
