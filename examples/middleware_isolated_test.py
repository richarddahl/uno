"""
Isolated tests for event middleware components that don't depend on the test infrastructure.

This script allows testing the middleware components independently without having to
rely on the project's test configuration, which has some dependencies on modules still
under development.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict

from uno.core.errors.result import Failure, Result, Success
from uno.core.events.handlers import EventHandlerContext, EventHandlerMiddleware
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
)
from uno.infrastructure.logging.factory import DefaultLoggerServiceFactory
from uno.infrastructure.logging.logger import LoggerService


class TestLogger(LoggerService):
    """Simple test logger that prints to console."""

    def __init__(self, name: str = "test"):
        """Initialize the logger."""
        super().__init__(name=name)

    def structured_log(self, level: str, message: str, **kwargs) -> None:
        """Print log messages to console."""
        print(f"[{level}] {self.name}: {message}")


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
            return Failure(
                error=ValueError(
                    f"Test handler temporary failure {self.current_failures}"
                )
            )

        return Success(value=None)


class TestLoggerFactory:
    """Test logger factory that creates test loggers."""

    def create(self, component_name: str) -> LoggerService:
        """Create a test logger."""
        return TestLogger(name=f"test.{component_name}")


async def test_retry_middleware():
    """Test that retry middleware retries on failure."""
    print("\n=== Testing RetryMiddleware ===")

    # Create test components
    logger_factory = TestLoggerFactory()
    logger = logger_factory.create("test")

    event = TestEvent(id="test-123", payload={"test": "data"})
    context = EventHandlerContext(
        event=event, event_type="test.event", handler_name="test_handler"
    )

    # Handler that will succeed after 3 failures
    handler = TestEventHandler(failure_count=3)

    # Create retry middleware with reasonable test settings
    retry_options = RetryOptions(max_retries=5, base_delay_ms=10)
    retry_middleware = RetryMiddleware(
        options=retry_options, logger_factory=logger_factory
    )

    # Process the event
    result = await retry_middleware.process(
        context, lambda ctx: handler.handle(ctx.event)
    )

    # Verify results
    print(f"Result is success: {result.is_success}")
    print(f"Handler call count: {handler.call_count}")
    assert result.is_success
    assert handler.call_count == 4  # 1 initial + 3 retries
    print("✅ RetryMiddleware test passed!")


async def test_circuit_breaker_middleware():
    """Test that circuit breaker middleware prevents cascading failures."""
    print("\n=== Testing CircuitBreakerMiddleware ===")

    # Create test components
    logger_factory = TestLoggerFactory()
    logger = logger_factory.create("test")

    event = TestEvent(id="test-123", payload={"test": "data"})
    context = EventHandlerContext(
        event=event, event_type="test.event", handler_name="test_handler"
    )

    # Handler that will always fail
    handler = TestEventHandler(should_fail=True)

    # Create circuit breaker middleware with low threshold for testing
    circuit_options = CircuitBreakerState(
        failure_threshold=3, recovery_timeout_seconds=0.1
    )
    circuit_breaker = CircuitBreakerMiddleware(
        options=circuit_options, logger_factory=logger_factory
    )

    # Process several events to trip the circuit
    results = []
    for i in range(5):
        print(f"Attempt {i + 1}...")
        result = await circuit_breaker.process(
            context, lambda ctx: handler.handle(ctx.event)
        )
        results.append(result)
        print(f"  Result: {result}")

    # Verify results
    print(f"Handler call count: {handler.call_count}")
    assert handler.call_count == 3  # Only the first 3 attempts should reach the handler
    assert all(r.is_failure for r in results)  # All attempts should fail

    # Verify circuit state
    circuit_state = circuit_breaker.circuit_states[context.event_type]
    print(f"Circuit state: {circuit_state}")
    assert circuit_state.is_open  # The circuit should be open

    print("✅ CircuitBreakerMiddleware test passed!")


async def test_metrics_middleware():
    """Test that metrics middleware collects performance data."""
    print("\n=== Testing MetricsMiddleware ===")

    # Create test components
    logger_factory = TestLoggerFactory()
    logger = logger_factory.create("test")

    event = TestEvent(id="test-123", payload={"test": "data"})
    context = EventHandlerContext(
        event=event, event_type="test.event", handler_name="test_handler"
    )

    # Create test handlers
    success_handler = TestEventHandler()
    failure_handler = TestEventHandler(should_fail=True)

    # Create metrics middleware
    metrics = MetricsMiddleware(logger_factory=logger_factory)

    # Process successful events
    for _ in range(3):
        await metrics.process(context, lambda ctx: success_handler.handle(ctx.event))

    # Process failed events
    failed_context = EventHandlerContext(
        event=event, event_type="test.failed_event", handler_name="test_handler"
    )

    for _ in range(2):
        await metrics.process(
            failed_context, lambda ctx: failure_handler.handle(ctx.event)
        )

    # Verify metrics
    success_metrics = metrics.metrics.get("test.event")
    failure_metrics = metrics.metrics.get("test.failed_event")

    print(f"Success metrics: {success_metrics}")
    print(f"Failure metrics: {failure_metrics}")

    assert success_metrics is not None
    assert success_metrics.success_count == 3
    assert success_metrics.failure_count == 0

    assert failure_metrics is not None
    assert failure_metrics.success_count == 0
    assert failure_metrics.failure_count == 2

    print("✅ MetricsMiddleware test passed!")


async def test_middleware_factory():
    """Test that the middleware factory creates middleware components correctly."""
    print("\n=== Testing EventHandlerMiddlewareFactory ===")

    # Create the factory
    logger_factory = TestLoggerFactory()
    middleware_factory = EventHandlerMiddlewareFactory(logger_factory=logger_factory)

    # Create middleware components
    retry = middleware_factory.create_retry_middleware()
    circuit_breaker = middleware_factory.create_circuit_breaker_middleware()
    metrics = middleware_factory.create_metrics_middleware()

    # Create a default stack
    stack = middleware_factory.create_default_middleware_stack()

    # Verify components
    print(f"Retry middleware: {retry}")
    print(f"Circuit breaker middleware: {circuit_breaker}")
    print(f"Metrics middleware: {metrics}")
    print(f"Default stack size: {len(stack)}")

    assert isinstance(retry, RetryMiddleware)
    assert isinstance(circuit_breaker, CircuitBreakerMiddleware)
    assert isinstance(metrics, MetricsMiddleware)
    assert len(stack) == 3

    print("✅ EventHandlerMiddlewareFactory test passed!")


async def test_middleware_chain():
    """Test that middleware components can be chained together."""
    print("\n=== Testing Middleware Chaining ===")

    # Create test components
    logger_factory = TestLoggerFactory()
    event = TestEvent(id="test-123", payload={"test": "data"})
    context = EventHandlerContext(
        event=event, event_type="test.event", handler_name="test_handler"
    )

    # Create a handler that fails a few times then succeeds
    handler = TestEventHandler(failure_count=2)

    # Create middleware components
    metrics = MetricsMiddleware(logger_factory=logger_factory)
    circuit_breaker = CircuitBreakerMiddleware(
        options=CircuitBreakerState(failure_threshold=5), logger_factory=logger_factory
    )
    retry = RetryMiddleware(
        options=RetryOptions(max_retries=3, base_delay_ms=10),
        logger_factory=logger_factory,
    )

    # Chain them together (metrics -> circuit_breaker -> retry -> handler)
    async def execute_chain(ctx):
        return await metrics.process(
            ctx,
            lambda c1: circuit_breaker.process(
                c1, lambda c2: retry.process(c2, lambda c3: handler.handle(c3.event))
            ),
        )

    # Process the event
    result = await execute_chain(context)

    # Verify results
    print(f"Result is success: {result.is_success}")
    print(f"Handler call count: {handler.call_count}")

    assert result.is_success
    assert handler.call_count == 3  # 1 initial + 2 retries

    # Check metrics were collected
    metrics_data = metrics.metrics.get(context.event_type)
    print(f"Metrics data: {metrics_data}")
    assert metrics_data is not None
    assert metrics_data.success_count == 1

    print("✅ Middleware chain test passed!")


async def main():
    """Run all tests."""
    print("Running middleware tests...")

    try:
        await test_retry_middleware()
        await test_circuit_breaker_middleware()
        await test_metrics_middleware()
        await test_middleware_factory()
        await test_middleware_chain()

        print("\n🎉 All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n❌ Error during tests: {e}")


if __name__ == "__main__":
    asyncio.run(main())
