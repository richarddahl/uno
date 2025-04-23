# Testing with Uno DI

Uno DI provides comprehensive support for testing your services and dependencies. This document covers various testing approaches and best practices for testing with Uno's dependency injection system.

## Test Service Provider

Uno DI includes a specialized test service provider for testing:

```python
from uno.core.di.test_helpers import TestServiceProvider

def test_my_service():
    # Create a test service provider
    provider = TestServiceProvider()
    
    # Register test services
    provider.register_singleton(IMyService, MockMyService)
    provider.register_singleton(IAnotherService, MockAnotherService)
    
    # Get and test the service
    service = provider.get_service(IMyService)
    assert service is not None
```

## Mocking Services

You can easily mock services for testing:

```python
from unittest.mock import Mock

def test_with_mocks():
    # Create a test service provider
    provider = TestServiceProvider()
    
    # Create mocks
    mock_db = Mock(spec=DatabaseProviderProtocol)
    mock_config = Mock(spec=ConfigProtocol)
    
    # Register mocks
    provider.register_singleton(DatabaseProviderProtocol, lambda: mock_db)
    provider.register_singleton(ConfigProtocol, lambda: mock_config)
    
    # Test your service
    service = provider.get_service(MyService)
    service.do_something()
    
    # Verify mocks
    mock_db.assert_called_once()
```

## Service Isolation

Test services in isolation:

```python
def test_service_isolation():
    # Create isolated test provider
    provider = TestServiceProvider()
    
    # Register only required dependencies
    provider.register_singleton(IRequiredService, MockRequiredService)
    
    # Test specific service
    service = provider.get_service(MyService)
    result = service.do_something()
    assert result == expected_result
```

## Service Lifecycle Testing

Test service initialization and disposal:

```python
class TestServiceLifecycle:
    def test_initialization(self):
        provider = TestServiceProvider()
        service = provider.get_service(MyService)
        assert service.is_initialized
        
    def test_disposal(self):
        provider = TestServiceProvider()
        service = provider.get_service(MyService)
        provider.dispose()
        assert service.is_disposed
```

## Named Service Testing

Test named service variants:

```python
def test_named_services():
    provider = TestServiceProvider()
    
    # Register named variants
    provider.register_singleton(IMyService, DefaultService, name="default")
    provider.register_singleton(IMyService, SpecialService, name="special")
    
    # Test default variant
    default_service = provider.get_service(IMyService, name="default")
    assert default_service is not None
    
    # Test special variant
    special_service = provider.get_service(IMyService, name="special")
    assert special_service is not None
```

## Service Factory Testing

Test service factories:

```python
def test_service_factory():
    provider = TestServiceProvider()
    
    # Register factory
    provider.register_singleton(
        MyService,
        lambda: MyService(config="test"),
        name="test"
    )
    
    # Test factory output
    service = provider.get_service(MyService, name="test")
    assert service.config == "test"
```

## Service Scope Testing

Test different service scopes:

```python
class TestServiceScopes:
    def test_singleton_scope(self):
        provider = TestServiceProvider()
        provider.register_singleton(MyService, MyService)
        
        service1 = provider.get_service(MyService)
        service2 = provider.get_service(MyService)
        assert service1 is service2
        
    def test_scoped_service(self):
        provider = TestServiceProvider()
        provider.register_scoped(MyService, MyService)
        
        with provider.create_scope() as scope:
            service1 = scope.get_service(MyService)
            service2 = scope.get_service(MyService)
            assert service1 is service2
        
    def test_transient_service(self):
        provider = TestServiceProvider()
        provider.register_transient(MyService, MyService)
        
        service1 = provider.get_service(MyService)
        service2 = provider.get_service(MyService)
        assert service1 is not service2
```

## Best Practices

1. **Test Isolation**
   - Test one service at a time
   - Mock external dependencies
   - Use isolated test providers
   - Clean up after tests

2. **Service Registration**
   - Register only required services
   - Use appropriate scopes
   - Handle service lifecycles
   - Document test configurations

3. **Dependency Management**
   - Mock external services
   - Use test doubles
   - Handle optional dependencies
   - Test dependency resolution

4. **Error Handling**
   - Test error cases
   - Handle initialization failures
   - Test disposal errors
   - Verify error propagation

## Advanced Testing Patterns

### Service Integration Testing

Test service integration:

```python
class TestServiceIntegration:
    def test_service_integration(self):
        provider = TestServiceProvider()
        
        # Register real services
        provider.register_singleton(DatabaseProviderProtocol, TestDatabase)
        provider.register_singleton(ConfigProtocol, TestConfig)
        
        # Test service integration
        service = provider.get_service(MyService)
        result = service.perform_operation()
        assert result == expected_result
```

### Service Factory Testing

Test complex service factories:

```python
def test_complex_factory():
    provider = TestServiceProvider()
    
    # Register dependencies
    provider.register_singleton(ConfigProtocol, TestConfig)
    provider.register_singleton(DatabaseProviderProtocol, TestDatabase)
    
    # Test factory
    service = provider.get_service(ComplexService)
    assert service.config is not None
    assert service.db is not None
```

### Service Lifecycle Testing

Test complete service lifecycle:

```python
class TestServiceLifecycle:
    def test_complete_lifecycle(self):
        provider = TestServiceProvider()
        
        # Register service
        provider.register_singleton(MyService, MyService)
        
        # Test initialization
        service = provider.get_service(MyService)
        assert service.is_initialized
        
        # Test operation
        result = service.do_something()
        assert result == expected_result
        
        # Test disposal
        provider.dispose()
        assert service.is_disposed
```

## Performance Testing

Test service performance:

```python
def test_service_performance():
    provider = TestServiceProvider()
    
    # Register service
    provider.register_singleton(MyService, MyService)
    
    # Test performance
    service = provider.get_service(MyService)
    start_time = time.time()
    for _ in range(1000):
        service.do_something()
    end_time = time.time()
    
    assert end_time - start_time < 0.1  # 100ms threshold
```

## Conclusion

Uno DI provides comprehensive support for testing your services and dependencies. By following these testing patterns and best practices, you can create more reliable, maintainable, and performant applications. The test service provider and mocking capabilities make it easy to test your services in isolation or as part of a larger system.
