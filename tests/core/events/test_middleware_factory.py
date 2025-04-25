"""
Tests for the EventHandlerMiddlewareFactory.
"""

from unittest.mock import MagicMock

import pytest

from uno.core.events.middleware import (
    CircuitBreakerMiddleware,
    CircuitBreakerState,
    MetricsMiddleware,
    RetryMiddleware,
    RetryOptions,
)
from uno.core.events.middleware_factory import (
    EventHandlerMiddlewareFactory,
    create_middleware_factory,
    register_with_result,
)
from uno.core.logging.logger import LoggerService


class MockLoggerFactory:
    """Mock implementation of LoggerServiceFactory for testing."""
    
    def create(self, component_name: str) -> LoggerService:
        """Create a mock logger."""
        logger = MagicMock(spec=LoggerService)
        logger.name = f"test.{component_name}"
        return logger


class TestEventHandlerMiddlewareFactory:
    """Tests for the EventHandlerMiddlewareFactory."""
    
    @pytest.fixture
    def logger_factory(self) -> MockLoggerFactory:
        """Create a mock logger factory for testing."""
        return MockLoggerFactory()
    
    @pytest.fixture
    def middleware_factory(self, logger_factory: MockLoggerFactory) -> EventHandlerMiddlewareFactory:
        """Create a middleware factory for testing."""
        return EventHandlerMiddlewareFactory(logger_factory=logger_factory)
    
    def test_create_retry_middleware(self, middleware_factory: EventHandlerMiddlewareFactory) -> None:
        """Test creating a RetryMiddleware."""
        # Act
        middleware = middleware_factory.create_retry_middleware()
        
        # Assert
        assert isinstance(middleware, RetryMiddleware)
        assert middleware.options is not None
    
    def test_create_retry_middleware_with_options(self, middleware_factory: EventHandlerMiddlewareFactory) -> None:
        """Test creating a RetryMiddleware with custom options."""
        # Test values
        max_retries = 5
        base_delay_ms = 200
        
        # Arrange
        options = RetryOptions(max_retries=max_retries, base_delay_ms=base_delay_ms)
        
        # Act
        middleware = middleware_factory.create_retry_middleware(options=options)
        
        # Assert
        assert isinstance(middleware, RetryMiddleware)
        assert middleware.options == options
        assert middleware.options.max_retries == max_retries
        assert middleware.options.base_delay_ms == base_delay_ms
    
    def test_create_circuit_breaker_middleware(self, middleware_factory: EventHandlerMiddlewareFactory) -> None:
        """Test creating a CircuitBreakerMiddleware."""
        # Act
        middleware = middleware_factory.create_circuit_breaker_middleware()
        
        # Assert
        assert isinstance(middleware, CircuitBreakerMiddleware)
        assert middleware.options is not None
    
    def test_create_circuit_breaker_middleware_with_options(self, middleware_factory: EventHandlerMiddlewareFactory) -> None:
        """Test creating a CircuitBreakerMiddleware with custom options."""
        # Test values
        failure_threshold = 10
        recovery_timeout = 60.0
        
        # Arrange
        options = CircuitBreakerState(failure_threshold=failure_threshold, recovery_timeout_seconds=recovery_timeout)
        event_types = ["user.created", "order.placed"]
        
        # Act
        middleware = middleware_factory.create_circuit_breaker_middleware(
            event_types=event_types,
            options=options
        )
        
        # Assert
        assert isinstance(middleware, CircuitBreakerMiddleware)
        assert middleware.options == options
        assert middleware.options.failure_threshold == failure_threshold
        assert middleware.options.recovery_timeout_seconds == recovery_timeout
        assert middleware.event_types == event_types
    
    def test_create_metrics_middleware(self, middleware_factory: EventHandlerMiddlewareFactory) -> None:
        """Test creating a MetricsMiddleware."""
        # Test values
        default_report_interval = 60.0
        
        # Act
        middleware = middleware_factory.create_metrics_middleware()
        
        # Assert
        assert isinstance(middleware, MetricsMiddleware)
        assert middleware.report_interval_seconds == default_report_interval
    
    def test_create_metrics_middleware_with_custom_interval(self, middleware_factory: EventHandlerMiddlewareFactory) -> None:
        """Test creating a MetricsMiddleware with a custom reporting interval."""
        # Arrange
        interval = 30.0
        
        # Act
        middleware = middleware_factory.create_metrics_middleware(report_interval_seconds=interval)
        
        # Assert
        assert isinstance(middleware, MetricsMiddleware)
        assert middleware.report_interval_seconds == interval
    
    def test_create_default_middleware_stack(self, middleware_factory: EventHandlerMiddlewareFactory) -> None:
        """Test creating the default middleware stack."""
        # Test values
        expected_stack_size = 3
        metrics_index = 0
        circuit_breaker_index = 1
        retry_index = 2
        
        # Act
        middleware_stack = middleware_factory.create_default_middleware_stack()
        
        # Assert
        assert len(middleware_stack) == expected_stack_size
        assert isinstance(middleware_stack[metrics_index], MetricsMiddleware)
        assert isinstance(middleware_stack[circuit_breaker_index], CircuitBreakerMiddleware)
        assert isinstance(middleware_stack[retry_index], RetryMiddleware)
    
    def test_create_default_middleware_stack_with_options(self, middleware_factory: EventHandlerMiddlewareFactory) -> None:
        """Test creating the default middleware stack with custom options."""
        # Test values
        custom_max_retries = 5
        custom_failure_threshold = 10
        custom_metrics_interval = 30.0
        expected_stack_size = 3
        metrics_index = 0
        circuit_breaker_index = 1
        retry_index = 2
        
        # Arrange
        retry_options = RetryOptions(max_retries=custom_max_retries)
        circuit_breaker_options = CircuitBreakerState(failure_threshold=custom_failure_threshold)
        metrics_interval = custom_metrics_interval
        
        # Act
        middleware_stack = middleware_factory.create_default_middleware_stack(
            retry_options=retry_options,
            circuit_breaker_options=circuit_breaker_options,
            metrics_interval_seconds=metrics_interval
        )
        
        # Assert
        assert len(middleware_stack) == expected_stack_size
        metrics = middleware_stack[metrics_index]
        circuit_breaker = middleware_stack[circuit_breaker_index]
        retry = middleware_stack[retry_index]
        
        assert isinstance(metrics, MetricsMiddleware)
        assert metrics.report_interval_seconds == custom_metrics_interval
        
        assert isinstance(circuit_breaker, CircuitBreakerMiddleware)
        assert circuit_breaker.options.failure_threshold == custom_failure_threshold
        
        assert isinstance(retry, RetryMiddleware)
        assert retry.options.max_retries == custom_max_retries


class TestFactoryFunctions:
    """Tests for the factory functions."""
    
    def test_create_middleware_factory(self) -> None:
        """Test creating a middleware factory."""
        # Arrange
        logger_factory = MockLoggerFactory()
        
        # Act
        factory = create_middleware_factory(logger_factory=logger_factory)
        
        # Assert
        assert isinstance(factory, EventHandlerMiddlewareFactory)
        assert factory.logger_factory == logger_factory
    
    def test_register_with_result_success(self) -> None:
        """Test registering middleware with a registry successfully."""
        # Test values
        expected_middleware_count = 3
        
        # Arrange
        logger_factory = MockLoggerFactory()
        middleware_factory = EventHandlerMiddlewareFactory(logger_factory=logger_factory)
        
        registry = MagicMock()
        registry.register_middleware = MagicMock()
        
        # Act
        result = register_with_result(registry, middleware_factory)
        
        # Assert
        assert result.is_success
        # Should register the expected number of middleware components
        assert registry.register_middleware.call_count == expected_middleware_count
    
    def test_register_with_result_failure(self) -> None:
        """Test registering middleware with a registry that fails."""
        # Arrange
        logger_factory = MockLoggerFactory()
        middleware_factory = EventHandlerMiddlewareFactory(logger_factory=logger_factory)
        
        registry = MagicMock()
        registry.register_middleware = MagicMock(side_effect=ValueError("Test error"))
        
        # Act
        result = register_with_result(registry, middleware_factory)
        
        # Assert
        assert result.is_failure
        assert isinstance(result.error, ValueError)
        assert str(result.error) == "Test error"
