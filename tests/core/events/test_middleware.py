"""
Tests for event handler middleware.
"""

import asyncio
import time

import pytest

from uno.core.errors.result import Failure, Result, Success
from uno.core.events.events import DomainEvent
from uno.core.events.handlers import EventHandlerContext
from uno.core.events.middleware import (
    CircuitBreakerMiddleware,
    CircuitBreakerState,
    EventMetrics,
    MetricsMiddleware,
    RetryMiddleware,
    RetryOptions,
)


class TestEvent(DomainEvent):
    """Test event for middleware tests."""
    
    event_type = "test"
    
    def __init__(self, aggregate_id: str = "test-aggregate", event_id: str = "test-id"):
        super().__init__(aggregate_id=aggregate_id, event_id=event_id)


@pytest.fixture
def event_context() -> EventHandlerContext:
    """Create a test event context."""
    event = TestEvent()
    return EventHandlerContext(event=event)


# Constants for test values
COUNT_ONE = 1
COUNT_TWO = 2
COUNT_THREE = 3
COUNT_FOUR = 4
COUNT_TEN = 10

# Test metric values
DURATION_100MS = 100.0
DURATION_200MS = 200.0
DURATION_300MS = 300.0
DURATION_600MS = 600.0


class TestRetryMiddleware:
    """Tests for RetryMiddleware."""
    
    @pytest.mark.asyncio
    async def test_success_no_retry(self, event_context: EventHandlerContext) -> None:
        """Test that a successful handler is not retried."""
        # Arrange
        retry_middleware = RetryMiddleware()
        call_count = 0
        
        async def next_middleware(_: EventHandlerContext) -> Result[str, Exception]:
            nonlocal call_count
            call_count += 1
            return Success("success")
        
        # Act
        result = await retry_middleware.process(event_context, next_middleware)
        
        # Assert
        assert result.is_success
        assert result.value == "success"
        assert call_count == COUNT_ONE
    
    @pytest.mark.asyncio
    async def test_retry_until_success(self, event_context: EventHandlerContext) -> None:
        """Test that a handler is retried until success."""
        # Arrange
        options = RetryOptions(
            max_retries=COUNT_THREE,
            base_delay_ms=1,  # Small delay for tests
            backoff_factor=1.0
        )
        retry_middleware = RetryMiddleware(options=options)
        call_count = 0
        
        async def next_middleware(_: EventHandlerContext) -> Result[str, Exception]:
            nonlocal call_count
            call_count += 1
            if call_count < COUNT_THREE:
                return Failure(ValueError("test error"))
            return Success("success")
        
        # Act
        result = await retry_middleware.process(event_context, next_middleware)
        
        # Assert
        assert result.is_success
        assert result.value == "success"
        assert call_count == COUNT_THREE
    
    @pytest.mark.asyncio
    async def test_retry_max_attempts(self, event_context: EventHandlerContext) -> None:
        """Test that a handler is not retried beyond max attempts."""
        # Arrange
        options = RetryOptions(
            max_retries=COUNT_TWO,
            base_delay_ms=1,  # Small delay for tests
            backoff_factor=1.0
        )
        retry_middleware = RetryMiddleware(options=options)
        call_count = 0
        
        async def next_middleware(_: EventHandlerContext) -> Result[str, Exception]:
            nonlocal call_count
            call_count += 1
            return Failure(ValueError("test error"))
        
        # Act
        result = await retry_middleware.process(event_context, next_middleware)
        
        # Assert
        assert result.is_failure
        assert isinstance(result.error, ValueError)
        assert call_count == COUNT_THREE  # Initial attempt + 2 retries
    
    @pytest.mark.asyncio
    async def test_retry_specific_exceptions(self, event_context: EventHandlerContext) -> None:
        """Test that only specific exceptions are retried."""
        # Arrange
        options = RetryOptions(
            max_retries=2,
            base_delay_ms=1,  # Small delay for tests
            backoff_factor=1.0,
            retryable_exceptions=[ValueError]
        )
        retry_middleware = RetryMiddleware(options=options)
        call_count = 0
        
        async def next_middleware(_: EventHandlerContext) -> Result[str, Exception]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Failure(ValueError("retryable error"))
            return Failure(TypeError("non-retryable error"))
        
        # Act
        result = await retry_middleware.process(event_context, next_middleware)
        
        # Assert
        assert result.is_failure
        assert isinstance(result.error, TypeError)
        assert call_count == 2  # Initial attempt + 1 retry for ValueError
    
    @pytest.mark.asyncio
    async def test_retry_backoff(self, event_context: EventHandlerContext) -> None:
        """Test that retry backoff is applied."""
        # Arrange
        options = RetryOptions(
            max_retries=COUNT_THREE,
            base_delay_ms=10,
            backoff_factor=2.0
        )
        retry_middleware = RetryMiddleware(options=options)
        call_times: list[float] = []
        
        async def next_middleware(_: EventHandlerContext) -> Result[str, Exception]:
            call_times.append(time.time())
            return Failure(ValueError("test error"))
        
        # Act
        # We'll compare time deltas from call_times directly, so this variable isn't needed
        result = await retry_middleware.process(event_context, next_middleware)
        
        # Assert
        assert result.is_failure
        assert len(call_times) == COUNT_FOUR  # Initial attempt + 3 retries
        
        # Calculate time deltas (we can't be exact but we should see increasing delays)
        deltas = [
            call_times[i] - call_times[i-1] for i in range(1, len(call_times))
        ]
        
        # Index constants for clarity
        first_delta = 0
        second_delta = 1
        third_delta = 2
        
        # Each delay should be approximately base_delay * backoff_factor^(attempt-1)
        # 10ms, 20ms, 40ms
        assert deltas[second_delta] > deltas[first_delta], "Second delay should be longer than first"
        assert deltas[third_delta] > deltas[second_delta], "Third delay should be longer than second"


class TestCircuitBreakerMiddleware:
    """Tests for CircuitBreakerMiddleware."""
    
    @pytest.mark.asyncio
    async def test_closed_circuit(self, event_context: EventHandlerContext) -> None:
        """Test that requests pass through when circuit is closed."""
        # Arrange
        circuit_breaker = CircuitBreakerMiddleware()
        
        async def next_middleware(_: EventHandlerContext) -> Result[str, Exception]:
            return Success("success")
        
        # Act
        result = await circuit_breaker.process(event_context, next_middleware)
        
        # Assert
        assert result.is_success
        assert result.value == "success"
        
        # Circuit should still be closed
        circuit = circuit_breaker.circuit_states[event_context.event.event_type]
        assert circuit.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_open_circuit_after_failures(self, event_context: EventHandlerContext) -> None:
        """Test that circuit opens after threshold failures."""
        # Arrange
        options = CircuitBreakerState(failure_threshold=COUNT_THREE)
        circuit_breaker = CircuitBreakerMiddleware(options=options)
        
        async def next_middleware(_: EventHandlerContext) -> Result[str, Exception]:
            return Failure(ValueError("test error"))
        
        # Act - trigger failures up to threshold
        for _ in range(options.failure_threshold):
            result = await circuit_breaker.process(event_context, next_middleware)
            assert result.is_failure
        
        # Circuit should now be open
        circuit = circuit_breaker.circuit_states[event_context.event.event_type]
        assert circuit.state == CircuitBreakerState.OPEN
        
        # Next request should be blocked by circuit breaker
        result = await circuit_breaker.process(event_context, next_middleware)
        assert result.is_failure
        assert "Circuit breaker open" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self, event_context: EventHandlerContext) -> None:
        """Test that circuit transitions to half-open after timeout."""
        # Arrange
        options = CircuitBreakerState(
            failure_threshold=2,
            recovery_timeout_seconds=0.01  # Small timeout for tests
        )
        circuit_breaker = CircuitBreakerMiddleware(options=options)
        circuit = circuit_breaker.circuit_states[event_context.event.event_type]
        
        # Open the circuit
        circuit.failure_count = options.failure_threshold
        circuit.state = CircuitBreakerState.OPEN
        circuit.opened_at = time.time()
        
        call_count = 0
        
        async def next_middleware(_: EventHandlerContext) -> Result[str, Exception]:
            nonlocal call_count
            call_count += 1
            return Success("success")
        
        # Wait for timeout to elapse
        await asyncio.sleep(options.recovery_timeout_seconds + 0.01)
        
        # Act - request should go through in half-open state
        result = await circuit_breaker.process(event_context, next_middleware)
        
        # Assert
        assert result.is_success
        assert call_count == 1
        assert circuit.state == CircuitBreakerState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_closes_after_success_threshold(self, event_context: EventHandlerContext) -> None:
        """Test that circuit closes after success threshold in half-open state."""
        # Arrange
        options = CircuitBreakerState(
            success_threshold=COUNT_TWO
        )
        circuit_breaker = CircuitBreakerMiddleware(options=options)
        circuit = circuit_breaker.circuit_states[event_context.event.event_type]
        
        # Set to half-open state
        circuit.state = CircuitBreakerState.HALF_OPEN
        
        async def next_middleware(_: EventHandlerContext) -> Result[str, Exception]:
            return Success("success")
        
        # Act - trigger successes up to threshold
        for _ in range(options.success_threshold):
            result = await circuit_breaker.process(event_context, next_middleware)
            assert result.is_success
        
        # Assert
        assert circuit.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_reopens_on_failure_in_half_open(self, event_context: EventHandlerContext) -> None:
        """Test that circuit reopens on failure in half-open state."""
        # Arrange
        circuit_breaker = CircuitBreakerMiddleware()
        circuit = circuit_breaker.circuit_states[event_context.event.event_type]
        
        # Set to half-open state
        circuit.state = CircuitBreakerState.HALF_OPEN
        
        async def next_middleware(_: EventHandlerContext) -> Result[str, Exception]:
            return Failure(ValueError("test error"))
        
        # Act
        result = await circuit_breaker.process(event_context, next_middleware)
        
        # Assert
        assert result.is_failure
        assert circuit.state == CircuitBreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_filtered_event_types(self, event_context: EventHandlerContext) -> None:
        """Test that circuit breaking only applies to specified event types."""
        # Arrange
        circuit_breaker = CircuitBreakerMiddleware(event_types=["different-event"])
        
        failure_count = 0
        
        async def next_middleware(_: EventHandlerContext) -> Result[str, Exception]:
            nonlocal failure_count
            failure_count += 1
            return Failure(ValueError("test error"))
        
        # Act - trigger many failures (more than threshold)
        for _ in range(COUNT_TEN):
            result = await circuit_breaker.process(event_context, next_middleware)
            assert result.is_failure
        
        # Assert - circuit should never open for this event type
        assert failure_count == COUNT_TEN


class TestMetricsMiddleware:
    """Tests for MetricsMiddleware."""
    
    def test_event_metrics_calculations(self) -> None:
        """Test that EventMetrics calculations are correct."""
        # Arrange
        metrics = EventMetrics()
        
        # Act
        metrics.record(DURATION_100MS, True)
        metrics.record(DURATION_200MS, True)
        metrics.record(DURATION_300MS, False)
        
        # Assert
        assert metrics.count == COUNT_THREE
        assert metrics.success_count == COUNT_TWO
        assert metrics.failure_count == COUNT_ONE
        assert metrics.total_duration_ms == DURATION_600MS
        assert metrics.min_duration_ms == DURATION_100MS
        assert metrics.max_duration_ms == DURATION_300MS
        assert metrics.average_duration_ms == DURATION_200MS
        assert metrics.success_rate == pytest.approx(66.67, 0.01)
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, event_context: EventHandlerContext) -> None:
        """Test that metrics are collected correctly."""
        # Arrange
        metrics_middleware = MetricsMiddleware(report_interval_seconds=3600)  # Long interval to avoid automatic reporting
        
        success_call_count = 0
        failure_call_count = 0
        
        async def success_middleware(_: EventHandlerContext) -> Result[str, Exception]:
            nonlocal success_call_count
            success_call_count += 1
            await asyncio.sleep(0.01)  # Add small delay for timing
            return Success("success")
        
        async def failure_middleware(_: EventHandlerContext) -> Result[str, Exception]:
            nonlocal failure_call_count
            failure_call_count += 1
            await asyncio.sleep(0.02)  # Add small delay for timing
            return Failure(ValueError("test error"))
        
        # Act
        await metrics_middleware.process(event_context, success_middleware)
        await metrics_middleware.process(event_context, success_middleware)
        await metrics_middleware.process(event_context, failure_middleware)
        
        # Get metrics for the test event type
        metrics = metrics_middleware.metrics[event_context.event.event_type]
        
        # Assert
        assert metrics.count == COUNT_THREE
        assert metrics.success_count == COUNT_TWO
        assert metrics.failure_count == COUNT_ONE
        assert metrics.min_duration_ms > 0
        assert metrics.max_duration_ms > 0
        assert success_call_count == COUNT_TWO
        assert failure_call_count == COUNT_ONE
        
        # Rough timing check - failure middleware should take longer
        assert metrics.max_duration_ms > metrics.min_duration_ms
    
    @pytest.mark.asyncio
    async def test_metrics_reporting(self, event_context: EventHandlerContext) -> None:
        """Test that metrics are reported at the appropriate interval."""
        # Arrange
        metrics_middleware = MetricsMiddleware(report_interval_seconds=0.01)  # Small interval for testing
        
        async def next_middleware(_: EventHandlerContext) -> Result[str, Exception]:
            return Success("success")
        
        # Act - first call
        await metrics_middleware.process(event_context, next_middleware)
        
        # Record the last report time
        first_report_time = metrics_middleware.last_report_time
        
        # Wait for report interval to elapse
        await asyncio.sleep(0.02)
        
        # Act - second call should trigger reporting
        await metrics_middleware.process(event_context, next_middleware)
        
        # Assert
        assert metrics_middleware.last_report_time > first_report_time
