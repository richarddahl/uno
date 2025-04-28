# uno.core.errors

Comprehensive error handling framework for the Uno application.

## Modules

- **__init__.py**: Package entrypoint; re-exports public API and registers core errors on import.
- **base.py**: Defines `FrameworkError`, error-context utilities (`get_error_context`, `add_error_context`), context managers/decorators (`with_error_context`, `with_async_error_context`), and core enums/types (`ErrorCode`, `ErrorCategory`, `ErrorSeverity`, `ErrorInfo`).
- **catalog.py**: Central registry for error metadata; provides `ErrorCatalog`, `register_error()`, and lookup helpers (`get_error_code_info()`, `get_all_error_codes()`).
- **definitions.py**: Canonical source for all error classes and error codes (config, init, dependency, object, serialization, protocol, general, security, validation). All errors are registered with the error catalog here.
  - `ValidationContext` to collect nested validation errors.
  - `ValidationError` exception and top-level `validate_fields()` helper.
- **result.py**: Result/Either monad implementation:
  - `Result[T, E]`, `Success[T, E]`, `Failure[T, E]`.
  - Functional combinators: `.map`, `.flat_map`, `.ensure`, `.recover`, `.map_async`, `.flat_map_async`.
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
from uno.core.errors.result import Result, Success, Failure

@with_error_context
def foo(x: int):
    if x < 0:
        raise FrameworkError(
            "Negative value", 
            error_code=ErrorCode.VALIDATION_ERROR, 
            value=x
        )
    return x

# Functional error handling with Result

def divide(a: int, b: int) -> Result[float, Exception]:
    if b == 0:
        return Failure(ValueError("division by zero"))
    return Success(a / b)

# Chaining with combinators
result = divide(10, 2).map(lambda x: x * 100).ensure(lambda x: x > 200, ValueError("too small")).recover(lambda e: 0.0)
if result.is_success:
    print("Result:", result.unwrap())
else:
    print("Error:", result.error)

# Async combinators
import asyncio
async def async_divide(a: int, b: int) -> Result[float, Exception]:
    await asyncio.sleep(0)
    if b == 0:
        return Failure(ValueError("division by zero"))
    return Success(a / b)
async def main():
    r = await Success(10).map_async(lambda x: x + 2)
    r2 = await Success(10).flat_map_async(lambda x: async_divide(x, 2))
asyncio.run(main())
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

The Uno Result monad enables functional, exception-free error handling for all domain, service, and application logic.

```python
from uno.core.errors.result import Result, Success, Failure

def safe_div(a: int, b: int) -> Result[int, Exception]:
    if b == 0:
        return Failure(ValueError("division by zero"))
    return Success(a // b)

# Chaining
result = safe_div(10, 2).map(lambda x: x * 10).ensure(lambda x: x > 0, ValueError("must be positive"))

# Recovering from errors
result = safe_div(10, 0).recover(lambda e: 0)

# Async chaining
import asyncio
async def async_safe_div(a: int, b: int) -> Result[int, Exception]:
    await asyncio.sleep(0)
    if b == 0:
        return Failure(ValueError("division by zero"))
    return Success(a // b)
async def main():
    r = await Success(10).map_async(lambda x: x + 2)
    r2 = await Success(10).flat_map_async(lambda x: async_safe_div(x, 2))
asyncio.run(main())
```

### Migration Guidance
- Refactor domain/service methods to return `Result[...]` instead of raising for expected errors.
- Use `.map`, `.flat_map`, `.ensure`, `.recover`, and async variants for clean workflows.
- Only raise exceptions for unrecoverable, framework-level failures.

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
