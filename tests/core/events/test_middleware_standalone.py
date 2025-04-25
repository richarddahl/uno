"""
Standalone tests for the event handler middleware components that don't depend on full framework integration.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import pytest

from uno.core.errors.result import Failure, Result, Success
from uno.core.events.handlers import EventHandlerContext, EventHandlerMiddleware
from uno.core.events.middleware import (
    CircuitBreakerMiddleware,
    CircuitBreakerState,
    EventMetrics,
    MetricsMiddleware,
    RetryMiddleware,
    RetryOptions,
)
from uno.core.logging.logger import LoggerService


@dataclass
class TestEvent:
    """A test event for middleware tests."""
    
    id: str
    payload: Dict[str, Any]


class TestEventHandler:
    """A test event handler for middleware tests."""
    
    def __init__(self, should_fail: bool = False, failure_count: int = 0):
        """
        Initialize the test handler.
        
        Args:
            should_fail: Whether the handler should fail when called
            failure_count: Number of times to fail before succeeding (for retry tests)
        """
        self.should_fail = should_fail
        self.failure_count = failure_count
        self.current_failures = 0
        self.call_count = 0
        self.last_event = None
    
    async def handle(self, event: TestEvent) -> Success | Failure:
        """Handle the test event."""
        self.call_count += 1
        self.last_event = event
        
        if self.should_fail:
            return Failure(error=ValueError("Test handler failed"))
        
        if self.current_failures < self.failure_count:
            self.current_failures += 1
            return Failure(error=ValueError(f"Test handler temporary failure {self.current_failures}"))
        
        return Success(value=None)


class TestMiddleware(EventHandlerMiddleware):
    """A simple pass-through middleware for testing."""
    
    def __init__(self):
        self.process_calls = 0
    
    async def process(
        self, 
        context: EventHandlerContext, 
        next_middleware: callable
    ) -> Success | Failure:
        """Process the event, count calls, and pass to next middleware."""
        self.process_calls += 1
        return await next_middleware(context)


@pytest.fixture
def test_event() -> TestEvent:
    """Create a test event."""
    return TestEvent(id="test-123", payload={"test": "data"})


@pytest.fixture
def success_handler() -> TestEventHandler:
    """Create a handler that always succeeds."""
    return TestEventHandler(should_fail=False)


@pytest.fixture
def failing_handler() -> TestEventHandler:
    """Create a handler that always fails."""
    return TestEventHandler(should_fail=True)


@pytest.fixture
def retry_handler() -> TestEventHandler:
    """Create a handler that fails a few times then succeeds."""
    return TestEventHandler(should_fail=False, failure_count=3)


@pytest.fixture
def test_logger() -> LoggerService:
    """Create a test logger."""
    return LoggerService(name="test.middleware")


@pytest.fixture
def event_context(test_event: TestEvent) -> EventHandlerContext:
    """Create a test event handler context."""
    return EventHandlerContext(
        event=test_event,
        event_type="test.event",
        handler_name="test_handler"
    )


class TestRetryMiddleware:
    """Tests for the RetryMiddleware."""
    
    @pytest.mark.asyncio
    async def test_no_retry_on_success(
        self, event_context: EventHandlerContext, success_handler: TestEventHandler, test_logger: LoggerService
    ):
        """Test that retry middleware doesn't retry on success."""
        # Arrange
        retry_middleware = RetryMiddleware(options=RetryOptions(max_retries=3))
        retry_middleware._logger = test_logger
        
        # Act
        result = await retry_middleware.process(
            event_context,
            lambda ctx: success_handler.handle(ctx.event)
        )
        
        # Assert
        assert result.is_success
        assert success_handler.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(
        self, event_context: EventHandlerContext, retry_handler: TestEventHandler, test_logger: LoggerService
    ):
        """Test that retry middleware retries on failure."""
        # Arrange
        retry_options = RetryOptions(max_retries=5, base_delay_ms=10)
        retry_middleware = RetryMiddleware(options=retry_options)
        retry_middleware._logger = test_logger
        
        # Act
        result = await retry_middleware.process(
            event_context,
            lambda ctx: retry_handler.handle(ctx.event)
        )
        
        # Assert
        assert result.is_success
        assert retry_handler.call_count == 4  # 1 initial + 3 retries
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(
        self, event_context: EventHandlerContext, retry_handler: TestEventHandler, test_logger: LoggerService
    ):
        """Test that retry middleware gives up after max retries."""
        # Arrange
        retry_handler.failure_count = 10  # More failures than max retries
        retry_options = RetryOptions(max_retries=3, base_delay_ms=10)
        retry_middleware = RetryMiddleware(options=retry_options)
        retry_middleware._logger = test_logger
        
        # Act
        result = await retry_middleware.process(
            event_context,
            lambda ctx: retry_handler.handle(ctx.event)
        )
        
        # Assert
        assert result.is_failure
        assert retry_handler.call_count == 4  # 1 initial + 3 retries
        assert isinstance(result.error, ValueError)


class TestCircuitBreakerMiddleware:
    """Tests for the CircuitBreakerMiddleware."""
    
    @pytest.mark.asyncio
    async def test_circuit_stays_closed_on_success(
        self, event_context: EventHandlerContext, success_handler: TestEventHandler, test_logger: LoggerService
    ):
        """Test that circuit stays closed when handlers succeed."""
        # Arrange
        circuit_breaker = CircuitBreakerMiddleware()
        circuit_breaker._logger = test_logger
        
        # Act & Assert - Circuit should stay closed for successful calls
        for _ in range(5):
            result = await circuit_breaker.process(
                event_context,
                lambda ctx: success_handler.handle(ctx.event)
            )
            assert result.is_success
            assert success_handler.call_count == _ + 1
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(
        self, event_context: EventHandlerContext, failing_handler: TestEventHandler, test_logger: LoggerService
    ):
        """Test that circuit opens after threshold failures."""
        # Arrange
        options = CircuitBreakerState(failure_threshold=3, recovery_timeout_seconds=0.1)
        circuit_breaker = CircuitBreakerMiddleware(options=options)
        circuit_breaker._logger = test_logger
        
        # Act - Generate failures to trigger circuit open
        results = []
        for _ in range(5):
            result = await circuit_breaker.process(
                event_context,
                lambda ctx: failing_handler.handle(ctx.event)
            )
            results.append(result)
            
        # Assert
        # First 3 should be regular failures
        for i in range(3):
            assert results[i].is_failure
            assert isinstance(results[i].error, ValueError)
        
        # Last 2 should be circuit open failures
        for i in range(3, 5):
            assert results[i].is_failure
            assert "circuit is open" in str(results[i].error).lower()
        
        # Handler should only be called for the first 3 failures
        assert failing_handler.call_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_recovery(
        self, event_context: EventHandlerContext, success_handler: TestEventHandler, test_logger: LoggerService
    ):
        """Test that circuit recovers after timeout."""
        # Arrange
        options = CircuitBreakerState(
            failure_threshold=2,
            recovery_timeout_seconds=0.1,
            success_threshold=1
        )
        circuit_breaker = CircuitBreakerMiddleware(options=options)
        circuit_breaker._logger = test_logger
        
        # Open the circuit with failures
        failing_handler = TestEventHandler(should_fail=True)
        for _ in range(3):
            await circuit_breaker.process(
                event_context,
                lambda ctx: failing_handler.handle(ctx.event)
            )
        
        # Verify circuit is open
        result = await circuit_breaker.process(
            event_context,
            lambda ctx: success_handler.handle(ctx.event)
        )
        assert result.is_failure
        assert "circuit is open" in str(result.error).lower()
        assert success_handler.call_count == 0
        
        # Wait for recovery timeout
        await asyncio.sleep(0.2)
        
        # Circuit should now be half-open and accept a trial request
        result = await circuit_breaker.process(
            event_context,
            lambda ctx: success_handler.handle(ctx.event)
        )
        assert result.is_success
        assert success_handler.call_count == 1
        
        # Circuit should now be closed again
        result = await circuit_breaker.process(
            event_context,
            lambda ctx: success_handler.handle(ctx.event)
        )
        assert result.is_success
        assert success_handler.call_count == 2


class TestMetricsMiddleware:
    """Tests for the MetricsMiddleware."""
    
    @pytest.mark.asyncio
    async def test_metrics_collection(
        self, event_context: EventHandlerContext, success_handler: TestEventHandler, test_logger: LoggerService
    ):
        """Test that metrics are collected for successful calls."""
        # Arrange
        metrics = MetricsMiddleware(report_interval_seconds=1.0)
        metrics._logger = test_logger
        
        # Act - Process a few events
        for _ in range(3):
            result = await metrics.process(
                event_context,
                lambda ctx: success_handler.handle(ctx.event)
            )
            assert result.is_success
        
        # Assert
        event_metrics = metrics.metrics.get(event_context.event_type)
        assert event_metrics is not None
        assert event_metrics.success_count == 3
        assert event_metrics.failure_count == 0
        assert len(event_metrics.durations) == 3
    
    @pytest.mark.asyncio
    async def test_metrics_collection_with_failures(
        self, event_context: EventHandlerContext, failing_handler: TestEventHandler, test_logger: LoggerService
    ):
        """Test that metrics are collected for failed calls."""
        # Arrange
        metrics = MetricsMiddleware(report_interval_seconds=1.0)
        metrics._logger = test_logger
        
        # Act - Process a few events with failures
        for _ in range(3):
            result = await metrics.process(
                event_context,
                lambda ctx: failing_handler.handle(ctx.event)
            )
            assert result.is_failure
        
        # Assert
        event_metrics = metrics.metrics.get(event_context.event_type)
        assert event_metrics is not None
        assert event_metrics.success_count == 0
        assert event_metrics.failure_count == 3
        assert len(event_metrics.durations) == 3
    
    @pytest.mark.asyncio
    async def test_metrics_reporting(
        self, event_context: EventHandlerContext, success_handler: TestEventHandler, test_logger: LoggerService
    ):
        """Test that metrics are reported after the interval."""
        # Arrange
        metrics = MetricsMiddleware(report_interval_seconds=0.1)
        metrics._logger = test_logger
        
        # Act - Process some events
        for _ in range(3):
            await metrics.process(
                event_context,
                lambda ctx: success_handler.handle(ctx.event)
            )
        
        # Force a report by processing again after interval
        time.sleep(0.2)
        
        # The metrics should have been reset after reporting
        await metrics.process(
            event_context,
            lambda ctx: success_handler.handle(ctx.event)
        )
        
        # Assert
        event_metrics = metrics.metrics.get(event_context.event_type)
        assert event_metrics is not None
        # After reporting, counts should be reset and only have the last call
        assert event_metrics.success_count == 1
        assert event_metrics.failure_count == 0
        assert len(event_metrics.durations) == 1


class TestMiddlewareChaining:
    """Tests for chaining multiple middleware components together."""
    
    @pytest.mark.asyncio
    async def test_middleware_chain_execution_order(
        self, event_context: EventHandlerContext, success_handler: TestEventHandler
    ):
        """Test that middleware are executed in the correct order."""
        # Arrange
        middleware1 = TestMiddleware()
        middleware2 = TestMiddleware()
        middleware3 = TestMiddleware()
        
        # Build the chain
        async def execute_handler(ctx: EventHandlerContext) -> Result:
            return await middleware1.process(
                ctx,
                lambda c1: middleware2.process(
                    c1,
                    lambda c2: middleware3.process(
                        c2,
                        lambda c3: success_handler.handle(c3.event)
                    )
                )
            )
        
        # Act
        result = await execute_handler(event_context)
        
        # Assert
        assert result.is_success
        assert middleware1.process_calls == 1
        assert middleware2.process_calls == 1
        assert middleware3.process_calls == 1
        assert success_handler.call_count == 1
    
    @pytest.mark.asyncio
    async def test_full_middleware_stack(
        self, event_context: EventHandlerContext, retry_handler: TestEventHandler, test_logger: LoggerService
    ):
        """Test a full middleware stack with metrics, circuit breaker, and retry."""
        # Arrange
        retry_handler.failure_count = 2  # Will succeed after 2 retries
        
        metrics = MetricsMiddleware(report_interval_seconds=60.0)
        metrics._logger = test_logger
        
        circuit_breaker = CircuitBreakerMiddleware(
            options=CircuitBreakerState(failure_threshold=5)
        )
        circuit_breaker._logger = test_logger
        
        retry = RetryMiddleware(options=RetryOptions(max_retries=3, base_delay_ms=10))
        retry._logger = test_logger
        
        # Build the chain (metrics -> circuit breaker -> retry -> handler)
        async def execute_handler(ctx: EventHandlerContext) -> Result:
            return await metrics.process(
                ctx,
                lambda c1: circuit_breaker.process(
                    c1,
                    lambda c2: retry.process(
                        c2,
                        lambda c3: retry_handler.handle(c3.event)
                    )
                )
            )
        
        # Act
        result = await execute_handler(event_context)
        
        # Assert
        assert result.is_success
        assert retry_handler.call_count == 3  # 1 initial + 2 retries
        
        # Check metrics were collected
        event_metrics = metrics.metrics.get(event_context.event_type)
        assert event_metrics is not None
        assert event_metrics.success_count == 1
        assert event_metrics.failure_count == 0
        assert len(event_metrics.durations) == 1
