"""
Integration tests for event handler middleware chain.

These tests verify that multiple middleware components can be chained together
and work correctly to process events through the EventHandlerRegistry.
"""

import asyncio
import time
from collections.abc import Callable
from typing import Any, cast

import pytest

from uno.core.errors.result import Failure, Result, Success
from uno.core.events.events import DomainEvent
from uno.core.events.handlers import (
    EventHandler,
    EventHandlerContext,
    EventHandlerMiddleware,
    EventHandlerRegistry,
    MiddlewareChainBuilder
)
from uno.core.events.middleware import (
    CircuitBreakerMiddleware,
    MetricsMiddleware,
    RetryMiddleware,
    RetryOptions
)


class TestEvent(DomainEvent):
    """Test event for middleware chain tests."""
    
    event_type = "test_chain_event"
    
    def __init__(self, aggregate_id: str = "test-aggregate", event_id: str = "test-id"):
        super().__init__(aggregate_id=aggregate_id, event_id=event_id)


class SuccessHandler(EventHandler):
    """Handler that always succeeds."""
    
    def __init__(self):
        self.call_count = 0
    
    async def handle(self, context: EventHandlerContext) -> Result[str, Exception]:
        """Handle the event successfully."""
        self.call_count += 1
        return Success(f"success-{self.call_count}")


class FlakyHandler(EventHandler):
    """Handler that fails initially but succeeds after a few attempts."""
    
    def __init__(self, succeed_after: int = 2):
        self.call_count = 0
        self.succeed_after = succeed_after
    
    async def handle(self, context: EventHandlerContext) -> Result[str, Exception]:
        """Handle the event, failing initially."""
        self.call_count += 1
        if self.call_count <= self.succeed_after:
            return Failure(ValueError(f"Simulated failure {self.call_count}"))
        return Success(f"success-after-{self.call_count}-attempts")


class FailureHandler(EventHandler):
    """Handler that always fails."""
    
    def __init__(self):
        self.call_count = 0
    
    async def handle(self, context: EventHandlerContext) -> Result[str, Exception]:
        """Handle the event with failure."""
        self.call_count += 1
        return Failure(ValueError(f"Permanent failure {self.call_count}"))


class LoggingMiddleware(EventHandlerMiddleware):
    """Simple middleware that logs events as they pass through."""
    
    def __init__(self, name: str = "LoggingMiddleware"):
        self.name = name
        self.logs = []
    
    async def process(
        self, 
        context: EventHandlerContext, 
        next_middleware: Callable[[EventHandlerContext], Result[Any, Exception]]
    ) -> Result[Any, Exception]:
        """Process the event and log it."""
        self.logs.append(f"{self.name} pre-processing event {context.event.event_type}")
        
        start_time = time.time()
        result = await next_middleware(context)
        duration = time.time() - start_time
        
        status = "success" if result.is_success else "failure"
        self.logs.append(f"{self.name} post-processing event {context.event.event_type} ({status}) in {duration:.2f}s")
        
        return result


@pytest.fixture
def event_context() -> EventHandlerContext:
    """Create a test event context."""
    event = TestEvent()
    return EventHandlerContext(event=event)


@pytest.fixture
def middleware_chain_builder() -> MiddlewareChainBuilder:
    """Create a middleware chain builder."""
    # Create a success handler
    handler = SuccessHandler()
    # Return a chain builder for this handler
    return MiddlewareChainBuilder(handler)


class TestMiddlewareChain:
    """Tests for middleware chain integration."""
    
    @pytest.mark.asyncio
    async def test_single_middleware(self, event_context: EventHandlerContext) -> None:
        """Test that a single middleware works correctly."""
        # Arrange
        handler = SuccessHandler()
        logging_middleware = LoggingMiddleware(name="TestLogger")
        
        chain_builder = MiddlewareChainBuilder(handler)
        processor = chain_builder.build_chain([logging_middleware])
        
        # Act
        result = await processor(event_context)
        
        # Assert
        assert result.is_success
        assert result.value == "success-1"
        assert len(logging_middleware.logs) == 2
        assert "pre-processing" in logging_middleware.logs[0]
        assert "post-processing" in logging_middleware.logs[1]
        assert "success" in logging_middleware.logs[1]
    
    @pytest.mark.asyncio
    async def test_multiple_middleware_chain(self, event_context: EventHandlerContext) -> None:
        """Test that multiple middleware can be chained together."""
        # Arrange
        handler = SuccessHandler()
        
        # Create middleware chain with multiple components
        logging_middleware_1 = LoggingMiddleware(name="LoggerOuter")
        logging_middleware_2 = LoggingMiddleware(name="LoggerInner")
        metrics_middleware = MetricsMiddleware()
        
        chain_builder = MiddlewareChainBuilder(handler)
        processor = chain_builder.build_chain([
            logging_middleware_1,  # Outermost (first to process)
            metrics_middleware,    # Middle
            logging_middleware_2   # Innermost (closest to handler)
        ])
        
        # Act
        result = await processor(event_context)
        
        # Assert
        assert result.is_success
        assert result.value == "success-1"
        
        # Check that both loggers were called in the right order
        assert len(logging_middleware_1.logs) == 2
        assert len(logging_middleware_2.logs) == 2
        
        # Outer middleware starts first, completes last
        assert logging_middleware_1.logs[0].startswith("LoggerOuter pre-processing")
        assert logging_middleware_2.logs[0].startswith("LoggerInner pre-processing")
        assert logging_middleware_2.logs[1].startswith("LoggerInner post-processing")
        assert logging_middleware_1.logs[1].startswith("LoggerOuter post-processing")
        
        # Check that metrics were recorded
        assert event_context.event.event_type in metrics_middleware.metrics
        assert metrics_middleware.metrics[event_context.event.event_type].count == 1
        assert metrics_middleware.metrics[event_context.event.event_type].success_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_and_metrics_middleware(self, event_context: EventHandlerContext) -> None:
        """Test that retry middleware works with metrics middleware."""
        # Arrange
        handler = FlakyHandler(succeed_after=2)  # Succeed on the 3rd attempt
        
        # Create retry middleware with short delays
        retry_options = RetryOptions(
            max_retries=3,
            base_delay_ms=10,
            backoff_factor=1.0
        )
        retry_middleware = RetryMiddleware(options=retry_options)
        
        # Create metrics middleware
        metrics_middleware = MetricsMiddleware()
        
        # Create logging middleware for observation
        logging_middleware = LoggingMiddleware()
        
        chain_builder = MiddlewareChainBuilder(handler)
        processor = chain_builder.build_chain([
            logging_middleware,  # Outermost
            metrics_middleware,  # Middle
            retry_middleware     # Innermost (closest to handler)
        ])
        
        # Act
        result = await processor(event_context)
        
        # Assert
        assert result.is_success
        assert result.value == "success-after-3-attempts"
        assert handler.call_count == 3  # Initial attempt + 2 retries
        
        # Check logs - should show only ONE request from the outside
        assert len(logging_middleware.logs) == 2
        
        # Check that metrics show only one operation (not 3)
        assert event_context.event.event_type in metrics_middleware.metrics
        assert metrics_middleware.metrics[event_context.event.event_type].count == 1
        assert metrics_middleware.metrics[event_context.event.event_type].success_count == 1
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_retry(self, event_context: EventHandlerContext) -> None:
        """Test that circuit breaker opens after retries are exhausted."""
        # Arrange
        handler = FailureHandler()  # Always fails
        
        # Create retry middleware with short delays
        retry_options = RetryOptions(
            max_retries=2,
            base_delay_ms=10,
            backoff_factor=1.0
        )
        retry_middleware = RetryMiddleware(options=retry_options)
        
        # Create circuit breaker with low threshold
        circuit_breaker = CircuitBreakerMiddleware(
            failure_threshold=1,  # Open after 1 failure
            reset_timeout_seconds=0.1  # Short timeout for testing
        )
        
        # Build the chain
        chain_builder = MiddlewareChainBuilder(handler)
        processor = chain_builder.build_chain([
            circuit_breaker,  # Outermost
            retry_middleware  # Innermost
        ])
        
        # Act - First call should retry and then fail
        result1 = await processor(event_context)
        
        # Assert - First call fails after retries are exhausted
        assert result1.is_failure
        assert handler.call_count == 3  # Initial + 2 retries
        
        # Circuit should now be open
        assert circuit_breaker.circuit_state[event_context.event.event_type] == "open"
        
        # Reset call count to track second attempt
        handler.call_count = 0
        
        # Act - Second call should fail immediately (circuit open)
        result2 = await processor(event_context)
        
        # Assert - Second call fails immediately without calling handler
        assert result2.is_failure
        assert "circuit is open" in str(result2.error)
        assert handler.call_count == 0  # Handler not called when circuit is open
        
        # Wait for circuit to transition to half-open
        await asyncio.sleep(0.15)  # Just over the reset timeout
        
        # Act - Third call should attempt handler again (circuit half-open)
        result3 = await processor(event_context)
        
        # Assert - Third call fails after retries
        assert result3.is_failure
        assert handler.call_count > 0  # Handler called in half-open state


class TestEventHandlerRegistryWithMiddleware:
    """Tests for EventHandlerRegistry with middleware integration."""
    
    @pytest.mark.asyncio
    async def test_registry_with_middleware(self) -> None:
        """Test that middleware can be registered and used with EventHandlerRegistry."""
        # Arrange
        registry = EventHandlerRegistry()
        
        # Create handlers
        success_handler = SuccessHandler()
        flaky_handler = FlakyHandler(succeed_after=1)  # Succeed on 2nd attempt
        
        # Register handlers
        registry.register_handler("test_chain_event", success_handler)
        registry.register_handler("test_chain_event", flaky_handler)
        
        # Create middleware
        logging_middleware = LoggingMiddleware()
        
        retry_options = RetryOptions(
            max_retries=2,
            base_delay_ms=10,
            backoff_factor=1.0
        )
        retry_middleware = RetryMiddleware(options=retry_options)
        
        # Register middleware
        registry.register_middleware(logging_middleware)
        registry.register_middleware(retry_middleware)
        
        # Create event
        event = TestEvent()
        context = EventHandlerContext(event=event)
        
        # Get middleware chain
        middleware_chain = registry.build_middleware_chain(event.event_type)
        
        # Act - Process each handler through middleware chain
        results = []
        for handler in registry.get_handlers(event.event_type):
            chain_builder = MiddlewareChainBuilder(cast(EventHandler, handler))
            processor = chain_builder.build_chain(middleware_chain)
            result = await processor(context)
            results.append(result)
        
        # Assert
        assert len(results) == 2
        assert all(r.is_success for r in results)
        assert flaky_handler.call_count == 2  # Initial attempt + 1 retry to succeed
        assert success_handler.call_count == 1  # No retries needed
        
        # Check logs
        assert len(logging_middleware.logs) == 4  # 2 pre + 2 post for two handlers
        assert "pre-processing" in logging_middleware.logs[0]
        assert "post-processing" in logging_middleware.logs[1]
        assert "pre-processing" in logging_middleware.logs[2]
        assert "post-processing" in logging_middleware.logs[3]
