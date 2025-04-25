"""
Standalone example demonstrating the event handler middleware patterns.

This example implements a minimal version of the core components
needed to demonstrate the middleware functionality without
depending on the full framework.
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol


# Setup basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("middleware_example")


# ---- Core Result Pattern ----

class Result(Protocol):
    """Result protocol for error handling."""
    
    @property
    def is_success(self) -> bool:
        ...
    
    @property
    def is_failure(self) -> bool:
        ...


@dataclass
class Success:
    """Represents a successful result."""
    
    value: Any
    
    @property
    def is_success(self) -> bool:
        return True
    
    @property
    def is_failure(self) -> bool:
        return False


@dataclass
class Failure:
    """Represents a failed result."""
    
    error: Exception
    
    @property
    def is_success(self) -> bool:
        return False
    
    @property
    def is_failure(self) -> bool:
        return True


# ---- Event System ----

@dataclass
class DomainEvent:
    """Base class for domain events."""
    
    event_type: str
    aggregate_id: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self) -> None:
        """Validate the event after initialization."""
        if not self.event_type:
            raise ValueError("Event type cannot be empty")
        if not self.aggregate_id:
            raise ValueError("Aggregate ID cannot be empty")


@dataclass
class EventHandlerContext:
    """Context for event handlers with metadata and utilities."""
    
    event: DomainEvent
    metadata: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


class EventHandler(ABC):
    """Base class for event handlers."""
    
    @abstractmethod
    async def handle(self, context: EventHandlerContext) -> Success | Failure:
        """
        Handle the event.
        
        Args:
            context: The event handler context
            
        Returns:
            Result with a value on success, or an error
        """
        pass


class EventHandlerMiddleware(ABC):
    """Base class for event handler middleware."""
    
    @abstractmethod
    async def process(
        self, 
        context: EventHandlerContext, 
        next_middleware: Callable[[EventHandlerContext], Success | Failure]
    ) -> Success | Failure:
        """
        Process the event and pass it to the next middleware.
        
        Args:
            context: The event handler context
            next_middleware: The next middleware to call
            
        Returns:
            Result with a value on success, or an error
        """
        pass


# ---- Middleware Implementations ----

class LoggingMiddleware(EventHandlerMiddleware):
    """Middleware for logging event handling."""
    
    async def process(
        self, 
        context: EventHandlerContext, 
        next_middleware: Callable[[EventHandlerContext], Success | Failure]
    ) -> Success | Failure:
        """
        Log event handling and pass to next middleware.
        
        Args:
            context: The event handler context
            next_middleware: The next middleware to call
            
        Returns:
            Result from the next middleware
        """
        event = context.event
        
        logger.debug(
            f"Processing event {event.event_type} "
            f"(ID: {event.event_id}, Aggregate: {event.aggregate_id})"
        )
        
        try:
            result = await next_middleware(context)
            
            if result.is_failure:
                logger.error(
                    f"Event handling failed for {event.event_type}: {result.error}"
                )
            else:
                logger.debug(
                    f"Event handling succeeded for {event.event_type}"
                )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Unexpected error handling event {event.event_type}: {e}"
            )
            return Failure(e)


class TimingMiddleware(EventHandlerMiddleware):
    """Middleware for timing event handling."""
    
    async def process(
        self, 
        context: EventHandlerContext, 
        next_middleware: Callable[[EventHandlerContext], Success | Failure]
    ) -> Success | Failure:
        """
        Time event handling and pass to next middleware.
        
        Args:
            context: The event handler context
            next_middleware: The next middleware to call
            
        Returns:
            Result from the next middleware
        """
        event = context.event
        start_time = time.time()
        
        try:
            result = await next_middleware(context)
            
            end_time = time.time()
            elapsed_ms = (end_time - start_time) * 1000
            
            logger.debug(
                f"Event {event.event_type} handled in {elapsed_ms:.2f}ms"
            )
            
            return result
            
        except Exception as e:
            end_time = time.time()
            elapsed_ms = (end_time - start_time) * 1000
            
            logger.error(
                f"Error handling event {event.event_type} after {elapsed_ms:.2f}ms: {e}"
            )
            
            return Failure(e)


@dataclass
class RetryOptions:
    """Options for retry middleware."""
    
    max_retries: int = 3
    base_delay_ms: int = 100
    max_delay_ms: int = 5000
    backoff_factor: float = 2.0
    retryable_exceptions: list[type[Exception]] = field(default_factory=list)
    
    def should_retry(self, error: Exception) -> bool:
        """
        Determine if an error should be retried.
        
        Args:
            error: The error to check
            
        Returns:
            True if the error should be retried, False otherwise
        """
        # If no specific exceptions are provided, retry all exceptions
        if not self.retryable_exceptions:
            return True
            
        # Otherwise, only retry specific exceptions
        return any(isinstance(error, exc_type) for exc_type in self.retryable_exceptions)
        
    def get_delay_ms(self, attempt: int) -> int:
        """
        Calculate the delay for a retry attempt.
        
        Args:
            attempt: The retry attempt number (0-based)
            
        Returns:
            The delay in milliseconds
        """
        delay = self.base_delay_ms * (self.backoff_factor ** attempt)
        return min(int(delay), self.max_delay_ms)


class RetryMiddleware(EventHandlerMiddleware):
    """Middleware for automatically retrying failed event handlers."""
    
    def __init__(self, options: RetryOptions | None = None):
        """
        Initialize the middleware.
        
        Args:
            options: Optional retry options
        """
        self.options = options or RetryOptions()
    
    async def process(
        self, 
        context: EventHandlerContext, 
        next_middleware: Callable[[EventHandlerContext], Success | Failure]
    ) -> Success | Failure:
        """
        Retry failed event handlers and pass to next middleware.
        
        Args:
            context: The event handler context
            next_middleware: The next middleware to call
            
        Returns:
            Result from the next middleware
        """
        event = context.event
        attempt = 0
        
        while True:
            result = await next_middleware(context)
            
            # If successful or we've reached max retries, return the result
            if result.is_success or attempt >= self.options.max_retries:
                if attempt > 0 and result.is_success:
                    logger.info(
                        f"Event {event.event_type} succeeded after {attempt + 1} attempts"
                    )
                elif attempt >= self.options.max_retries and result.is_failure:
                    logger.error(
                        f"Event {event.event_type} failed after {attempt + 1} attempts: {result.error}"
                    )
                
                return result
            
            # Check if we should retry
            if isinstance(result.error, Exception) and self.options.should_retry(result.error):
                attempt += 1
                delay_ms = self.options.get_delay_ms(attempt - 1)
                
                logger.debug(
                    f"Retrying event {event.event_type} after {delay_ms}ms "
                    f"(attempt {attempt + 1}/{self.options.max_retries + 1})"
                )
                
                # Wait before retrying
                await asyncio.sleep(delay_ms / 1000)
            else:
                # Not retryable, return the failure
                logger.debug(
                    f"Error not retryable for event {event.event_type}: {result.error}"
                )
                return result


@dataclass
class CircuitBreakerState:
    """State for the circuit breaker."""
    
    # Circuit states
    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Circuit is tripped, requests are rejected
    HALF_OPEN = "half_open"  # Testing if the service has recovered
    
    # Current state
    state: str = CLOSED
    
    # Failure threshold before opening the circuit
    failure_threshold: int = 5
    
    # Recovery timeout in seconds before trying half-open state
    recovery_timeout_seconds: float = 30.0
    
    # Success threshold in half-open state before closing the circuit
    success_threshold: int = 2
    
    # Counters
    failure_count: int = 0
    success_count: int = 0
    
    # Timestamp when the circuit was opened
    opened_at: float = 0.0
    
    def record_success(self) -> None:
        """Record a successful operation."""
        if self.state == self.CLOSED:
            # Reset failure count in closed state
            self.failure_count = 0
        elif self.state == self.HALF_OPEN:
            # Increment success count in half-open state
            self.success_count += 1
            
            # If we've reached the success threshold, close the circuit
            if self.success_count >= self.success_threshold:
                self.state = self.CLOSED
                self.success_count = 0
                self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record a failed operation."""
        if self.state == self.CLOSED:
            # Increment failure count in closed state
            self.failure_count += 1
            
            # If we've reached the failure threshold, open the circuit
            if self.failure_count >= self.failure_threshold:
                self.state = self.OPEN
                self.opened_at = time.time()
        elif self.state == self.HALF_OPEN:
            # Any failure in half-open state reopens the circuit
            self.state = self.OPEN
            self.opened_at = time.time()
            self.success_count = 0
    
    def can_execute(self) -> bool:
        """
        Check if the operation can be executed.
        
        Returns:
            True if the operation can be executed, False otherwise
        """
        current_time = time.time()
        
        if self.state == self.OPEN:
            # Check if recovery timeout has elapsed
            if current_time - self.opened_at >= self.recovery_timeout_seconds:
                # Transition to half-open state
                self.state = self.HALF_OPEN
                self.success_count = 0
                return True
            return False
        
        # Always allow execution in CLOSED or HALF_OPEN states
        return True


class CircuitBreakerMiddleware(EventHandlerMiddleware):
    """Middleware for preventing cascading failures using the circuit breaker pattern."""
    
    def __init__(
        self,
        event_types: list[str] | None = None,
        options: CircuitBreakerState | None = None
    ):
        """
        Initialize the middleware.
        
        Args:
            event_types: Optional list of event types to apply circuit breaking to.
                         If None, circuit breaking is applied to all event types.
            options: Optional circuit breaker options
        """
        self.event_types = event_types
        self.options = options or CircuitBreakerState()
        
        # Track circuit breaker state per event type
        self.circuit_states: dict[str, CircuitBreakerState] = {}
    
    def _get_circuit_state(self, event_type: str) -> CircuitBreakerState:
        """Get or create a circuit state for an event type."""
        if event_type not in self.circuit_states:
            self.circuit_states[event_type] = CircuitBreakerState(
                failure_threshold=self.options.failure_threshold,
                recovery_timeout_seconds=self.options.recovery_timeout_seconds,
                success_threshold=self.options.success_threshold
            )
        return self.circuit_states[event_type]
    
    async def process(
        self, 
        context: EventHandlerContext, 
        next_middleware: Callable[[EventHandlerContext], Success | Failure]
    ) -> Success | Failure:
        """
        Apply circuit breaking and pass to next middleware.
        
        Args:
            context: The event handler context
            next_middleware: The next middleware to call
            
        Returns:
            Result from the next middleware
        """
        event = context.event
        
        # Skip circuit breaking if this event type is not in the list
        if self.event_types is not None and event.event_type not in self.event_types:
            return await next_middleware(context)
        
        # Get circuit state for this event type
        circuit = self._get_circuit_state(event.event_type)
        
        # Check if the circuit allows execution
        if not circuit.can_execute():
            error = Exception(f"Circuit breaker open for event type {event.event_type}")
            
            logger.warning(
                f"Circuit breaker preventing execution of {event.event_type}"
            )
            
            return Failure(error)
        
        # Execute the event handler
        result = await next_middleware(context)
        
        # Record success or failure
        if result.is_success:
            circuit.record_success()
            
            # Log state transition if it happened
            if circuit.state == CircuitBreakerState.CLOSED and circuit.success_count == 0:
                logger.info(
                    f"Circuit closed for event type {event.event_type}"
                )
        else:
            circuit.record_failure()
            
            # Log state transition if it happened
            if circuit.state == CircuitBreakerState.OPEN and circuit.failure_count == circuit.failure_threshold:
                logger.warning(
                    f"Circuit opened for event type {event.event_type} after {circuit.failure_threshold} failures"
                )
        
        return result


@dataclass
class EventMetrics:
    """Metrics for an event type."""
    
    count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    
    @property
    def average_duration_ms(self) -> float:
        """
        Calculate the average duration.
        
        Returns:
            The average duration in milliseconds
        """
        if self.count == 0:
            return 0.0
        return self.total_duration_ms / self.count
    
    @property
    def success_rate(self) -> float:
        """
        Calculate the success rate.
        
        Returns:
            The success rate as a percentage
        """
        if self.count == 0:
            return 0.0
        return (self.success_count / self.count) * 100.0
    
    def record(self, duration_ms: float, success: bool) -> None:
        """
        Record a metric.
        
        Args:
            duration_ms: The duration in milliseconds
            success: Whether the operation was successful
        """
        self.count += 1
        self.total_duration_ms += duration_ms
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)


class MetricsMiddleware(EventHandlerMiddleware):
    """Middleware for collecting metrics about event handler performance."""
    
    def __init__(
        self,
        report_interval_seconds: float = 60.0
    ):
        """
        Initialize the middleware.
        
        Args:
            report_interval_seconds: Interval in seconds to report metrics
        """
        self.report_interval_seconds = report_interval_seconds
        self.last_report_time = time.time()
        self.metrics: dict[str, EventMetrics] = {}
    
    async def process(
        self, 
        context: EventHandlerContext, 
        next_middleware: Callable[[EventHandlerContext], Success | Failure]
    ) -> Success | Failure:
        """
        Collect metrics and pass to next middleware.
        
        Args:
            context: The event handler context
            next_middleware: The next middleware to call
            
        Returns:
            Result from the next middleware
        """
        event = context.event
        
        # Ensure we have a metrics object for this event type
        if event.event_type not in self.metrics:
            self.metrics[event.event_type] = EventMetrics()
        
        start_time = time.time()
        
        # Execute the event handler
        result = await next_middleware(context)
        
        # Calculate duration
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Record metrics
        self.metrics[event.event_type].record(duration_ms, result.is_success)
        
        # Check if it's time to report metrics
        current_time = time.time()
        if current_time - self.last_report_time >= self.report_interval_seconds:
            self._report_metrics()
            self.last_report_time = current_time
        
        return result
    
    def _report_metrics(self) -> None:
        """Report metrics."""
        print("\n----- Event Metrics Report -----")
        for event_type, metrics in self.metrics.items():
            print(f"Event Type: {event_type}")
            print(f"  Count: {metrics.count}")
            print(f"  Success/Failure: {metrics.success_count}/{metrics.failure_count}")
            print(f"  Success Rate: {metrics.success_rate:.2f}%")
            print(f"  Avg Duration: {metrics.average_duration_ms:.2f}ms")
            print(f"  Min Duration: {metrics.min_duration_ms:.2f}ms" if metrics.min_duration_ms != float('inf') else "  Min Duration: N/A")
            print(f"  Max Duration: {metrics.max_duration_ms:.2f}ms")
            print()


class EventHandlerRegistry:
    """Registry for event handlers and middleware."""
    
    def __init__(self):
        """Initialize the registry."""
        self._handlers: dict[str, list[EventHandler]] = {}
        self._middleware: list[EventHandlerMiddleware] = []
    
    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        """
        Register a handler for an event type.
        
        Args:
            event_type: The event type to handle
            handler: The handler to register
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
            
        self._handlers[event_type].append(handler)
        
        logger.debug(f"Registered handler {handler.__class__.__name__} for event type {event_type}")
    
    def register_middleware(self, middleware: EventHandlerMiddleware) -> None:
        """
        Register middleware.
        
        Args:
            middleware: The middleware to register
        """
        self._middleware.append(middleware)
        
        logger.debug(f"Registered middleware {middleware.__class__.__name__}")
    
    def get_handlers(self, event_type: str) -> list[EventHandler]:
        """
        Get all handlers for an event type.
        
        Args:
            event_type: The event type to get handlers for
            
        Returns:
            List of handlers for the event type
        """
        return self._handlers.get(event_type, [])
    
    def get_middleware(self) -> list[EventHandlerMiddleware]:
        """
        Get all middleware.
        
        Returns:
            List of middleware
        """
        return self._middleware


# ---- Example Event Types ----

class UserCreatedEvent(DomainEvent):
    """Event representing a user being created."""
    
    def __init__(self, aggregate_id: str, username: str, email: str, event_id: str | None = None):
        """Initialize the user created event."""
        super().__init__(
            event_type="user.created",
            aggregate_id=aggregate_id,
            event_id=event_id or str(uuid.uuid4())
        )
        self.username = username
        self.email = email


class OrderPlacedEvent(DomainEvent):
    """Event representing an order being placed."""
    
    def __init__(
        self, 
        aggregate_id: str, 
        order_id: str, 
        user_id: str, 
        total_amount: float, 
        event_id: str | None = None
    ):
        """Initialize the order placed event."""
        super().__init__(
            event_type="order.placed",
            aggregate_id=aggregate_id,
            event_id=event_id or str(uuid.uuid4())
        )
        self.order_id = order_id
        self.user_id = user_id
        self.total_amount = total_amount


# ---- Example Handlers ----

class EmailNotificationHandler(EventHandler):
    """Handler that sends email notifications for events."""
    
    def __init__(self, fail_rate: float = 0.0):
        """
        Initialize the handler.
        
        Args:
            fail_rate: Rate at which the handler should simulate failure (0.0-1.0)
        """
        self.fail_rate = fail_rate
        self.call_count = 0
    
    async def handle(self, context: EventHandlerContext) -> Success | Failure:
        """
        Handle the event by sending an email notification.
        
        Args:
            context: The event handler context
            
        Returns:
            Success or Failure
        """
        event = context.event
        self.call_count += 1
        
        # Simulate occasional failures if requested
        if self.fail_rate > 0.0 and self.call_count % int(1 / self.fail_rate) == 0:
            logger.error(f"Failed to send email notification for event {event.event_type}")
            return Failure(Exception("Email service unavailable"))
        
        # Simulate processing delay
        await asyncio.sleep(0.05)
        
        if isinstance(event, UserCreatedEvent):
            logger.info(f"Sent welcome email to {event.username} ({event.email})")
        elif isinstance(event, OrderPlacedEvent):
            logger.info(f"Sent order confirmation email for order {event.order_id}")
        
        return Success("Email sent")


class SlowExternalServiceHandler(EventHandler):
    """Handler that integrates with an external service."""
    
    def __init__(self, service_name: str, delay_seconds: float = 0.1):
        """
        Initialize the handler.
        
        Args:
            service_name: Name of the external service
            delay_seconds: Simulated delay for the service call
        """
        self.service_name = service_name
        self.delay_seconds = delay_seconds
    
    async def handle(self, context: EventHandlerContext) -> Success | Failure:
        """
        Handle the event by calling an external service.
        
        Args:
            context: The event handler context
            
        Returns:
            Success or Failure
        """
        event = context.event
        
        # Simulate an external service call with delay
        await asyncio.sleep(self.delay_seconds)
        
        logger.info(f"Processed event {event.event_type} with {self.service_name}")
        
        return Success(f"Processed with {self.service_name}")


# ---- Example Execution ----

async def process_event(registry: EventHandlerRegistry, event: DomainEvent) -> None:
    """
    Process an event with all registered handlers.
    
    Args:
        registry: The event handler registry
        event: The event to process
    """
    context = EventHandlerContext(event=event)
    
    # Get handlers for this event type
    handlers = registry.get_handlers(event.event_type)
    if not handlers:
        print(f"No handlers registered for event type {event.event_type}")
        return
    
    # Process with each handler
    for handler in handlers:
        # Build middleware chain
        middleware = registry.get_middleware()
        
        # Start with the handler
        async def execute_handler(ctx: EventHandlerContext):
            return await handler.handle(ctx)
        
        # Build the middleware chain in reverse order
        next_middleware = execute_handler
        
        # Process the middleware chain in reverse order (from last to first)
        for mw in reversed(middleware):
            # Correctly capture the current middleware and next function in the closure
            def create_middleware_fn(current_mw=mw, next_fn=next_middleware):
                async def chain_middleware(ctx: EventHandlerContext):
                    return await current_mw.process(ctx, next_fn)
                return chain_middleware
            
            # Update the next middleware function
            next_middleware = create_middleware_fn()
        
        # Execute the middleware chain
        result = await next_middleware(context)
        
        if result.is_failure:
            print(f"Handler {handler.__class__.__name__} failed: {result.error}")
        else:
            print(f"Handler {handler.__class__.__name__} succeeded: {result.value}")


async def main() -> None:
    """Run the example."""
    # Create event handler registry
    registry = EventHandlerRegistry()
    
    # Register middleware
    # Order matters - middleware is executed in the order registered
    
    # Timing middleware - records execution time
    registry.register_middleware(TimingMiddleware())
    
    # Logging middleware - logs events and results
    registry.register_middleware(LoggingMiddleware())
    
    # Metrics middleware - collects metrics about event handler performance
    registry.register_middleware(MetricsMiddleware(report_interval_seconds=2.0))
    
    # Retry middleware - automatically retries failed handlers
    retry_options = RetryOptions(
        max_retries=3,
        base_delay_ms=100,
        backoff_factor=2.0
    )
    registry.register_middleware(RetryMiddleware(options=retry_options))
    
    # Circuit breaker middleware - prevents cascading failures
    circuit_options = CircuitBreakerState(
        failure_threshold=5,
        recovery_timeout_seconds=10.0,
        success_threshold=2
    )
    registry.register_middleware(CircuitBreakerMiddleware(options=circuit_options))
    
    # Register event handlers
    registry.register_handler("user.created", EmailNotificationHandler())
    registry.register_handler("order.placed", EmailNotificationHandler(fail_rate=0.3))
    registry.register_handler("user.created", SlowExternalServiceHandler("analytics"))
    registry.register_handler("order.placed", SlowExternalServiceHandler("shipping", delay_seconds=0.2))
    
    # Process some events
    print("\n--- Processing User Created Events ---")
    for i in range(3):
        user_id = f"user-{i}"
        event = UserCreatedEvent(
            aggregate_id=user_id,
            username=f"user{i}",
            email=f"user{i}@example.com"
        )
        print(f"\nProcessing event: {event.event_type} (ID: {event.event_id})")
        await process_event(registry, event)
    
    print("\n--- Processing Order Placed Events (with occasional failures) ---")
    for i in range(10):
        order_id = f"ord{i}"
        user_id = f"user-{i % 3}"
        event = OrderPlacedEvent(
            aggregate_id=f"order-{i}",
            order_id=order_id,
            user_id=user_id,
            total_amount=99.99 + i
        )
        print(f"\nProcessing event: {event.event_type} (ID: {event.event_id})")
        await process_event(registry, event)
        
        # Add small delay between events
        await asyncio.sleep(0.1)
    
    # Wait to see metrics report (happens every 2 seconds)
    print("\nWaiting for metrics report...")
    await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
