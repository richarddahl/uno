"""
Fully self-contained test script for event middleware components.

This script recreates simplified versions of the middleware components for testing,
without relying on the Uno framework's import structure, which may have circular dependencies
during development.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Protocol, TypeVar, cast


# ----- Simple Result monad implementation -----

T = TypeVar("T")
E = TypeVar("E")


class Success(Generic[T]):
    """Represents a successful operation with a result value."""

    def __init__(self, value: T):
        self.value = value

    @property
    def is_success(self) -> bool:
        return True

    @property
    def is_failure(self) -> bool:
        return False

    def __repr__(self) -> str:
        return f"Success({self.value})"


class Failure(Generic[E]):
    """Represents a failed operation with an error value."""

    def __init__(self, error: E):
        self.error = error

    @property
    def is_success(self) -> bool:
        return False

    @property
    def is_failure(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"Failure({self.error})"


Result = Success[T] | Failure[E]


# ----- Simple logger implementation -----


class LoggerService:
    """Simple logger service for testing."""

    def __init__(self, name: str):
        self.name = name

    def structured_log(self, level: str, message: str, **kwargs) -> None:
        """Print log messages to console."""
        extra = ", ".join(f"{k}={v}" for k, v in kwargs.items() if k != "name")
        if extra:
            print(f"[{level}] {self.name}: {message} ({extra})")
        else:
            print(f"[{level}] {self.name}: {message}")


class LoggerServiceFactory(Protocol):
    """Protocol for logger factory implementations."""

    def create(self, component_name: str) -> LoggerService:
        """Create a logger for a specific component."""
        ...


class DefaultLoggerFactory:
    """Default implementation of logger factory."""

    def __init__(self, base_namespace: str = "test"):
        self.base_namespace = base_namespace

    def create(self, component_name: str) -> LoggerService:
        return LoggerService(f"{self.base_namespace}.{component_name}")


# ----- Event types and context -----


@dataclass
class TestEvent:
    """A simple event for testing."""

    id: str
    payload: Dict[str, Any]


@dataclass
class EventHandlerContext:
    """Context for event handler execution."""

    event: Any
    event_type: str
    handler_name: str


# ----- Event handler middleware -----


class EventHandlerMiddleware(Protocol):
    """Protocol for event handler middleware."""

    async def process(
        self,
        context: EventHandlerContext,
        next_middleware: Callable[[EventHandlerContext], Result],
    ) -> Result:
        """Process an event through the middleware chain."""
        ...


# ----- Test event handler -----


class TestEventHandler:
    """Test event handler that can be configured to fail."""

    def __init__(
        self,
        name: str = "test_handler",
        should_fail: bool = False,
        failure_count: int = 0,
    ):
        self.name = name
        self.should_fail = should_fail
        self.failure_count = failure_count
        self.current_failures = 0
        self.call_count = 0

    async def handle(self, event: TestEvent) -> Result:
        """Handle the event, with configurable failure behavior."""
        self.call_count += 1

        if self.should_fail:
            return Failure(
                ValueError(f"Handler {self.name} failed (permanent failure)")
            )

        if self.current_failures < self.failure_count:
            self.current_failures += 1
            return Failure(
                ValueError(
                    f"Handler {self.name} failed (temporary failure {self.current_failures}/{self.failure_count})"
                )
            )

        return Success(f"Event {event.id} handled successfully by {self.name}")


# ----- Middleware implementations -----


@dataclass
class RetryOptions:
    """Configuration options for RetryMiddleware."""

    max_retries: int = 3
    base_delay_ms: int = 100

    def get_delay_for_attempt(self, attempt: int) -> float:
        """Calculate delay for a given retry attempt using exponential backoff."""
        delay_ms = self.base_delay_ms * (2 ** (attempt - 1))
        return delay_ms / 1000  # Convert to seconds


class RetryMiddleware:
    """Middleware for automatically retrying failed event handlers."""

    def __init__(
        self,
        options: RetryOptions | None = None,
        logger_factory: LoggerServiceFactory | None = None,
    ):
        """Initialize the middleware."""
        self.options = options or RetryOptions()
        self.logger_factory = logger_factory
        self._logger: LoggerService | None = None

    @property
    def logger(self) -> LoggerService:
        """Get the logger, creating it if needed."""
        if self._logger is None:
            if self.logger_factory:
                self._logger = self.logger_factory.create("events.middleware.retry")
            else:
                self._logger = LoggerService(name="events.middleware.retry")
        return self._logger

    async def process(
        self,
        context: EventHandlerContext,
        next_middleware: Callable[[EventHandlerContext], Result],
    ) -> Result:
        """Process an event with retry logic for failures."""
        # Initial attempt
        result = await next_middleware(context)
        if result.is_success:
            return result

        # Handle failures with retries
        last_error = cast(Failure, result).error
        for attempt in range(1, self.options.max_retries + 1):
            delay = self.options.get_delay_for_attempt(attempt)

            self.logger.structured_log(
                "INFO",
                f"Retrying event handler after failure",
                event_type=context.event_type,
                handler=context.handler_name,
                attempt=attempt,
                delay_seconds=delay,
                error=str(last_error),
            )

            # Wait before retry
            await asyncio.sleep(delay)

            # Retry the handler
            result = await next_middleware(context)
            if result.is_success:
                self.logger.structured_log(
                    "INFO",
                    f"Retry succeeded",
                    event_type=context.event_type,
                    handler=context.handler_name,
                    attempt=attempt,
                )
                return result

            last_error = cast(Failure, result).error

        # If we get here, all retries failed
        self.logger.structured_log(
            "ERROR",
            f"All retry attempts failed",
            event_type=context.event_type,
            handler=context.handler_name,
            max_retries=self.options.max_retries,
            error=str(last_error),
        )
        return Failure(last_error)


@dataclass
class CircuitBreakerState:
    """State for circuit breaker pattern."""

    failure_threshold: int = 5
    success_threshold: int = 1
    recovery_timeout_seconds: float = 30.0

    # Instance state (not part of the configuration)
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0
    is_open: bool = False

    def record_failure(self) -> None:
        """Record a failure, potentially opening the circuit."""
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.is_open = True

    def record_success(self) -> None:
        """Record a success, potentially closing the circuit."""
        self.success_count += 1
        self.failure_count = 0

        if self.success_count >= self.success_threshold:
            self.is_open = False

    def should_allow_request(self) -> bool:
        """Determine if a request should be allowed through the circuit."""
        if not self.is_open:
            return True

        # Check if recovery timeout has elapsed
        elapsed = time.time() - self.last_failure_time
        if elapsed >= self.recovery_timeout_seconds:
            return True  # Allow a test request

        return False

    def __repr__(self) -> str:
        state = "OPEN" if self.is_open else "CLOSED"
        return f"CircuitBreaker({state}, failures={self.failure_count}, successes={self.success_count})"


class CircuitBreakerMiddleware:
    """Middleware for preventing cascading failures using the circuit breaker pattern."""

    def __init__(
        self,
        event_types: List[str] | None = None,
        options: CircuitBreakerState | None = None,
        logger_factory: LoggerServiceFactory | None = None,
    ):
        """Initialize the middleware."""
        self.event_types = event_types
        self.options = options or CircuitBreakerState()
        self.logger_factory = logger_factory
        self._logger: LoggerService | None = None

        # Track circuit breaker state per event type
        self.circuit_states: Dict[str, CircuitBreakerState] = {}

    @property
    def logger(self) -> LoggerService:
        """Get the logger, creating it if needed."""
        if self._logger is None:
            if self.logger_factory:
                self._logger = self.logger_factory.create(
                    "events.middleware.circuit_breaker"
                )
            else:
                self._logger = LoggerService(name="events.middleware.circuit_breaker")
        return self._logger

    def _get_circuit_state(self, event_type: str) -> CircuitBreakerState:
        """Get or create circuit state for an event type."""
        if event_type not in self.circuit_states:
            # Create a new state with the same options as the defaults
            self.circuit_states[event_type] = CircuitBreakerState(
                failure_threshold=self.options.failure_threshold,
                recovery_timeout_seconds=self.options.recovery_timeout_seconds,
                success_threshold=self.options.success_threshold,
            )
        return self.circuit_states[event_type]

    def _should_apply_to_event(self, event_type: str) -> bool:
        """Determine if this middleware should be applied to the event type."""
        if self.event_types is None:
            return True
        return event_type in self.event_types

    async def process(
        self,
        context: EventHandlerContext,
        next_middleware: Callable[[EventHandlerContext], Result],
    ) -> Result:
        """Process an event using the circuit breaker pattern."""
        event_type = context.event_type

        # Skip if not configured for this event type
        if not self._should_apply_to_event(event_type):
            return await next_middleware(context)

        # Get circuit state
        circuit = self._get_circuit_state(event_type)

        # Check if circuit is open
        if circuit.is_open and not circuit.should_allow_request():
            self.logger.structured_log(
                "WARN",
                f"Circuit is open, rejecting request",
                event_type=event_type,
                handler=context.handler_name,
            )
            return Failure(ValueError(f"Circuit breaker is open for {event_type}"))

        # Circuit is closed or we're allowing a test request
        result = await next_middleware(context)

        if result.is_success:
            circuit.record_success()
            if circuit.is_open:
                self.logger.structured_log(
                    "INFO",
                    f"Circuit is now closed after successful test request",
                    event_type=event_type,
                    handler=context.handler_name,
                )
        else:
            circuit.record_failure()
            if circuit.is_open:
                self.logger.structured_log(
                    "WARN",
                    f"Circuit is now open after failures",
                    event_type=event_type,
                    handler=context.handler_name,
                    threshold=circuit.failure_threshold,
                    failures=circuit.failure_count,
                )

        return result


@dataclass
class EventMetrics:
    """Metrics for a specific event type."""

    success_count: int = 0
    failure_count: int = 0
    durations: List[float] = field(default_factory=list)

    def record_success(self, duration_ms: float) -> None:
        """Record a successful event handling."""
        self.success_count += 1
        self.durations.append(duration_ms)

    def record_failure(self, duration_ms: float) -> None:
        """Record a failed event handling."""
        self.failure_count += 1
        self.durations.append(duration_ms)

    def get_average_duration(self) -> float:
        """Calculate the average duration in milliseconds."""
        if not self.durations:
            return 0.0
        return sum(self.durations) / len(self.durations)

    def __repr__(self) -> str:
        avg = self.get_average_duration()
        return f"EventMetrics(success={self.success_count}, failure={self.failure_count}, avg_ms={avg:.2f})"


class MetricsMiddleware:
    """Middleware for collecting metrics about event handler performance."""

    def __init__(
        self,
        report_interval_seconds: float = 60.0,
        logger_factory: LoggerServiceFactory | None = None,
    ):
        """Initialize the middleware."""
        self.report_interval_seconds = report_interval_seconds
        self.last_report_time = time.time()
        self.metrics: Dict[str, EventMetrics] = {}
        self.logger_factory = logger_factory
        self._logger: LoggerService | None = None

    @property
    def logger(self) -> LoggerService:
        """Get the logger, creating it if needed."""
        if self._logger is None:
            if self.logger_factory:
                self._logger = self.logger_factory.create("events.middleware.metrics")
            else:
                self._logger = LoggerService(name="events.middleware.metrics")
        return self._logger

    def _get_metrics(self, event_type: str) -> EventMetrics:
        """Get or create metrics for an event type."""
        if event_type not in self.metrics:
            self.metrics[event_type] = EventMetrics()
        return self.metrics[event_type]

    def _should_report(self) -> bool:
        """Determine if it's time to report metrics."""
        now = time.time()
        elapsed = now - self.last_report_time
        return elapsed >= self.report_interval_seconds

    def _report_metrics(self) -> None:
        """Report metrics and reset counters."""
        self.logger.structured_log("INFO", "Event handler metrics report:")

        for event_type, metrics in self.metrics.items():
            total = metrics.success_count + metrics.failure_count
            if total == 0:
                continue

            success_rate = (metrics.success_count / total) * 100 if total > 0 else 0
            avg_duration = metrics.get_average_duration()

            self.logger.structured_log(
                "INFO",
                f"Event metrics: {metrics}",
                event_type=event_type,
                success_count=metrics.success_count,
                failure_count=metrics.failure_count,
                success_rate=f"{success_rate:.1f}%",
                avg_duration_ms=f"{avg_duration:.2f}",
            )

        # Reset metrics for next interval but keep the dictionaries
        for metrics in self.metrics.values():
            metrics.success_count = 0
            metrics.failure_count = 0
            metrics.durations = []

        self.last_report_time = time.time()

    async def process(
        self,
        context: EventHandlerContext,
        next_middleware: Callable[[EventHandlerContext], Result],
    ) -> Result:
        """Process an event and collect metrics."""
        start_time = time.time()

        # Process the event
        result = await next_middleware(context)

        # Calculate duration in milliseconds
        duration_ms = (time.time() - start_time) * 1000

        # Record metrics
        metrics = self._get_metrics(context.event_type)
        if result.is_success:
            metrics.record_success(duration_ms)
        else:
            metrics.record_failure(duration_ms)

        # Report if interval has passed
        if self._should_report():
            self._report_metrics()

        return result


# ----- Middleware factory -----


class EventHandlerMiddlewareFactory:
    """Factory for creating middleware components."""

    def __init__(self, logger_factory: LoggerServiceFactory):
        """Initialize with a logger factory."""
        self.logger_factory = logger_factory

    def create_retry_middleware(
        self, options: RetryOptions | None = None
    ) -> RetryMiddleware:
        """Create a retry middleware instance."""
        return RetryMiddleware(options=options, logger_factory=self.logger_factory)

    def create_circuit_breaker_middleware(
        self,
        event_types: List[str] | None = None,
        options: CircuitBreakerState | None = None,
    ) -> CircuitBreakerMiddleware:
        """Create a circuit breaker middleware instance."""
        return CircuitBreakerMiddleware(
            event_types=event_types, options=options, logger_factory=self.logger_factory
        )

    def create_metrics_middleware(
        self, report_interval_seconds: float = 60.0
    ) -> MetricsMiddleware:
        """Create a metrics middleware instance."""
        return MetricsMiddleware(
            report_interval_seconds=report_interval_seconds,
            logger_factory=self.logger_factory,
        )

    def create_default_middleware_stack(
        self,
        retry_options: RetryOptions | None = None,
        circuit_breaker_options: CircuitBreakerState | None = None,
        metrics_interval_seconds: float = 60.0,
    ) -> List[EventHandlerMiddleware]:
        """Create a default middleware stack with common components."""
        metrics = self.create_metrics_middleware(
            report_interval_seconds=metrics_interval_seconds
        )
        circuit_breaker = self.create_circuit_breaker_middleware(
            options=circuit_breaker_options
        )
        retry = self.create_retry_middleware(options=retry_options)

        # Order matters: metrics (outer) -> circuit_breaker -> retry (inner)
        return [metrics, circuit_breaker, retry]


def create_middleware_factory(
    logger_factory: LoggerServiceFactory | None = None,
) -> EventHandlerMiddlewareFactory:
    """Create a middleware factory."""
    if logger_factory is None:
        logger_factory = DefaultLoggerFactory(base_namespace="uno")
    return EventHandlerMiddlewareFactory(logger_factory=logger_factory)


# ----- Tests -----


async def test_retry_middleware():
    """Test that retry middleware retries on failure."""
    print("\n=== Testing RetryMiddleware ===")

    # Create test components
    logger_factory = DefaultLoggerFactory()
    event = TestEvent(id="test-123", payload={"test": "data"})
    context = EventHandlerContext(
        event=event, event_type="test.event", handler_name="test_handler"
    )

    # Handler that will succeed after 3 failures
    handler = TestEventHandler(failure_count=3)

    # Create retry middleware
    retry_options = RetryOptions(max_retries=5, base_delay_ms=10)
    retry_middleware = RetryMiddleware(
        options=retry_options, logger_factory=logger_factory
    )

    # Process the event
    result = await retry_middleware.process(
        context, lambda ctx: handler.handle(ctx.event)
    )

    # Verify results
    assert result.is_success
    assert handler.call_count == 4  # 1 initial + 3 retries
    print(f"✓ Handler call count: {handler.call_count}")
    print("✅ RetryMiddleware test passed!")


async def test_circuit_breaker_middleware():
    """Test that circuit breaker middleware prevents cascading failures."""
    print("\n=== Testing CircuitBreakerMiddleware ===")

    # Create test components
    logger_factory = DefaultLoggerFactory()
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

    # Verify results
    assert handler.call_count == 3  # Only the first 3 attempts should reach the handler
    print(f"✓ Handler call count: {handler.call_count}")

    # Verify circuit state
    circuit_state = circuit_breaker._get_circuit_state(context.event_type)
    assert circuit_state.is_open  # The circuit should be open
    print(f"✓ Circuit state: {circuit_state}")

    # Now test recovery
    print("Waiting for recovery timeout...")
    await asyncio.sleep(0.2)

    # Create a handler that succeeds
    success_handler = TestEventHandler()

    # Try again - this should be allowed through as a test request
    result = await circuit_breaker.process(
        context, lambda ctx: success_handler.handle(ctx.event)
    )

    # Verify the result
    assert result.is_success
    assert success_handler.call_count == 1

    # Circuit should now be closed
    assert not circuit_state.is_open
    print("✓ Circuit closed after successful test request")

    print("✅ CircuitBreakerMiddleware test passed!")


async def test_metrics_middleware():
    """Test that metrics middleware collects performance data."""
    print("\n=== Testing MetricsMiddleware ===")

    # Create test components
    logger_factory = DefaultLoggerFactory()
    event = TestEvent(id="test-123", payload={"test": "data"})
    context = EventHandlerContext(
        event=event, event_type="test.event", handler_name="test_handler"
    )

    # Create handlers
    success_handler = TestEventHandler()
    failure_handler = TestEventHandler(should_fail=True)

    # Create metrics middleware with short interval for testing
    metrics = MetricsMiddleware(
        report_interval_seconds=0.1, logger_factory=logger_factory
    )

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
    success_metrics = metrics._get_metrics("test.event")
    failure_metrics = metrics._get_metrics("test.failed_event")

    assert success_metrics.success_count == 3
    assert success_metrics.failure_count == 0
    print(f"✓ Success metrics: {success_metrics}")

    assert failure_metrics.success_count == 0
    assert failure_metrics.failure_count == 2
    print(f"✓ Failure metrics: {failure_metrics}")

    # Wait for a report
    print("Waiting for metrics report...")
    await asyncio.sleep(0.2)

    # Metrics should be reset after reporting
    assert success_metrics.success_count == 0
    assert failure_metrics.failure_count == 0
    print("✓ Metrics reset after reporting")

    print("✅ MetricsMiddleware test passed!")


async def test_middleware_factory():
    """Test that the middleware factory creates middleware components correctly."""
    print("\n=== Testing EventHandlerMiddlewareFactory ===")

    # Create the factory
    logger_factory = DefaultLoggerFactory()
    middleware_factory = EventHandlerMiddlewareFactory(logger_factory=logger_factory)

    # Create middleware components
    retry = middleware_factory.create_retry_middleware()
    circuit_breaker = middleware_factory.create_circuit_breaker_middleware()
    metrics = middleware_factory.create_metrics_middleware()

    # Create a default stack
    stack = middleware_factory.create_default_middleware_stack(
        retry_options=RetryOptions(max_retries=2),
        circuit_breaker_options=CircuitBreakerState(failure_threshold=3),
        metrics_interval_seconds=30.0,
    )

    # Verify components
    assert isinstance(retry, RetryMiddleware)
    assert isinstance(circuit_breaker, CircuitBreakerMiddleware)
    assert isinstance(metrics, MetricsMiddleware)
    assert len(stack) == 3

    # Verify custom options were applied
    assert stack[2].options.max_retries == 2  # Retry middleware
    assert stack[1].options.failure_threshold == 3  # Circuit breaker
    assert stack[0].report_interval_seconds == 30.0  # Metrics

    print("✓ Factory creates middleware with correct options")
    print("✅ EventHandlerMiddlewareFactory test passed!")


async def test_middleware_chain():
    """Test that middleware components can be chained together."""
    print("\n=== Testing Middleware Chaining ===")

    # Create test components
    logger_factory = DefaultLoggerFactory()
    event = TestEvent(id="test-123", payload={"test": "data"})
    context = EventHandlerContext(
        event=event, event_type="test.event", handler_name="test_handler"
    )

    # Create a handler that fails a few times then succeeds
    handler = TestEventHandler(failure_count=2)

    # Create middleware components
    metrics = MetricsMiddleware(
        report_interval_seconds=1.0, logger_factory=logger_factory
    )
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
    assert result.is_success
    assert handler.call_count == 3  # 1 initial + 2 retries
    print(f"✓ Handler call count: {handler.call_count}")

    # Check metrics were collected
    metrics_data = metrics._get_metrics(context.event_type)
    assert metrics_data.success_count == 1
    assert metrics_data.failure_count == 0
    print(f"✓ Metrics collected: {metrics_data}")

    print("✅ Middleware chain test passed!")


async def main():
    """Run all tests."""
    print("Starting standalone middleware tests...")

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
