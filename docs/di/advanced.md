# Dependency Injection Advanced Features

This document covers advanced features of the Uno framework's dependency injection system.

## Factory Pattern

The factory pattern allows for more complex object creation logic when simple constructor injection isn't sufficient.

### Registration

```python
from uno.core.di import ServiceCollection

services = ServiceCollection()
services.add_factory(ComplexObject, lambda service_provider: ComplexObject(
    dependency1=service_provider.resolve(Dependency1),
    dependency2=service_provider.resolve(Dependency2),
    config_value="custom_value"
))
```

### Use Cases

- When a service requires non-injected parameters
- When you need conditional logic during instantiation
- When you need to perform additional setup after construction

## Lazy Resolution

Lazy resolution defers the actual creation of a service until it's accessed, which can improve startup performance and break circular dependencies.

### Registration

```python
# Register a service to be lazily initialized
services.add_lazy(ExpensiveService)
```

### Resolution

```python
# Get a lazy reference
lazy_service = ServiceContainer.resolve_lazy(ExpensiveService)

# Later in the code
if condition:
    actual_service = lazy_service.value  # Only resolved when accessed
```

### Implementation

The lazy resolution returns a proxy object that wraps the actual service:

```python
class LazyServiceProxy:
    def __init__(self, resolver, service_type):
        self._resolver = resolver
        self._service_type = service_type
        self._instance = None
    
    @property
    def value(self):
        if self._instance is None:
            self._instance = self._resolver.resolve(self._service_type)
        return self._instance
```

## Conditional Registration

You can register different implementations based on environment, configuration, or other conditions:

```python
# Register different implementations based on environment
if app_config.environment == "production":
    services.add_singleton(EmailService, ProductionEmailService)
else:
    services.add_singleton(EmailService, DevelopmentEmailService)

# Or use a factory for more complex conditions
services.add_factory(StorageService, lambda sp: 
    AzureStorageService(sp.resolve(AzureConfig)) 
    if app_config.cloud_provider == "azure" 
    else AwsStorageService(sp.resolve(AwsConfig))
)
```

## Resolution Middleware

Middleware allows you to intercept and modify the service resolution process:

```python
from uno.core.di import ServiceResolutionMiddleware

class LoggingMiddleware(ServiceResolutionMiddleware):
    def resolve(self, service_type, next):
        print(f"Resolving service: {service_type.__name__}")
        result = next(service_type)
        print(f"Resolved service: {service_type.__name__}")
        return result

# Register middleware
ServiceContainer.add_middleware(LoggingMiddleware())
```

Common middleware use cases:
- Logging
- Performance monitoring
- Caching
- Authorization checks

## Async Initialization and Disposal

For services that require async initialization or cleanup:

```python
from uno.core.di import AsyncInitializable, Disposable

class DatabaseService(AsyncInitializable, Disposable):
    async def initialize(self):
        self.connection = await create_connection_async(self.connection_string)
        await self.connection.open()
    
    async def dispose_async(self):
        await self.connection.close()
```

Using async services:

```python
async with ServiceContainer.create_async_scope() as scope:
    db = await scope.resolve_async(DatabaseService)
    results = await db.query("SELECT * FROM users")
```

## Service Decorators

You can use decorators to simplify service registration:

```python
from uno.core.di import singleton, scoped, transient

@singleton
class ConfigService:
    pass

@scoped
class UserService:
    def __init__(self, db: DatabaseService):
        self.db = db

@transient
class EmailMessage:
    pass
```

## Keyed Services

Register multiple implementations of the same interface with different keys:

```python
services.add_keyed_singleton(PaymentProcessor, "stripe", StripePaymentProcessor)
services.add_keyed_singleton(PaymentProcessor, "paypal", PayPalPaymentProcessor)

# Resolve by key
stripe_processor = ServiceContainer.resolve_keyed(PaymentProcessor, "stripe")
```

## Service Collections

Register and resolve collections of services that implement the same interface:

```python
# Register multiple implementations
services.add_to_collection(Validator, EmailValidator)
services.add_to_collection(Validator, PasswordValidator)
services.add_to_collection(Validator, UsernameValidator)

# Resolve all implementations
validators = ServiceContainer.resolve_collection(Validator)
for validator in validators:
    validator.validate(data)
```

## Scoped Lifetime Management

Advanced scope management for web applications or other contexts:

```python
# In a web application
async def handle_request(request):
    async with ServiceContainer.create_async_scope(scope_id=request.id) as scope:
        handler = await scope.resolve_async(RequestHandler)
        return await handler.handle(request)
```

## Testing with the DI Container

Simplified testing with DI:

```python
def test_user_service():
    # Setup test container
    services = ServiceCollection()
    services.add_instance(DatabaseService, MockDatabase())
    services.add_scoped(UserService)
    
    # Create test scope
    with ServiceContainer.initialize(services).create_scope() as scope:
        user_service = scope.resolve(UserService)
        
        # Test the service
        result = user_service.get_user(1)
        assert result.name == "Test User"
```