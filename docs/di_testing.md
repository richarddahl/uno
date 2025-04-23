# Uno DI: Testing Utilities and Best Practices

This guide covers how to use Uno's DI test helpers for effective, isolated, and robust testing.

## Test Helpers Overview

The `TestDI` class in `uno.core.di.test_helpers` provides utilities for:
- Creating isolated `ServiceProvider` instances for each test
- Temporarily overriding service registrations or instances (sync and async)
- Registering mocks/test doubles
- Resetting DI state between tests
- Initializing providers with custom configs

## Common Test Patterns

### 1. Isolated Providers
```python
from uno.core.di.test_helpers import TestDI

def test_my_feature():
    provider = TestDI.create_test_provider()
    # Register services/mocks as needed
    ...
```

### 2. Temporary Service Override (Sync)
```python
from uno.core.di.test_helpers import TestDI

with TestDI.override_service(provider, MyService, my_mock):
    # Inside this block, MyService resolves to my_mock
    ...
```

### 3. Temporary Service Override (Async)
```python
from uno.core.di.test_helpers import TestDI

async with TestDI.async_override_service(provider, MyService, my_mock):
    ...
```

### 4. Registering Mocks
```python
TestDI.register_mock(provider, MyService, my_mock)
```

### 5. Resetting DI State
```python
TestDI.reset_di_state()
```

### 6. Initializing Providers with Custom Config
```python
provider = TestDI.initialize_test_provider(site_name="My Test Site", env="ci")
```

### 7. Full Test Setup (Async)
```python
provider = await TestDI.setup_test_services()
```

## Best Practices
- Always use isolated providers per test to avoid cross-test contamination.
- Use the override context managers for temporary changes.
- Reset DI state after tests if using globals.
- Prefer dependency injection over patching globals.

---

For more, see the `uno.core.di.test_helpers` module docstrings and source code.
