"""
Event handler middleware implementations.

This module provides middleware for the event handling system:
- RetryMiddleware: Automatically retries failed event handlers
- MetricsMiddleware: Collects metrics about event handler performance
- CircuitBreakerMiddleware: Prevents cascading failures
"""

import asyncio
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from uno.core.errors.result import Failure, Result
from uno.core.events.handlers import EventHandlerContext, EventHandlerMiddleware
from uno.core.logging.factory import LoggerServiceFactory
from uno.core.logging.logger import LoggerService


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
    
    def __init__(
        self, 
        options: RetryOptions | None = None,
        logger_factory: LoggerServiceFactory | None = None
    ):
        """
        Initialize the middleware.
        
        Args:
            options: Optional retry options
            logger_factory: Optional factory for creating loggers
        """
        self.options = options or RetryOptions()
        self.logger_factory = logger_factory
        
        # Default logger is created on first access
        self._logger: LoggerService | None = None
    
    @property
    def logger(self) -> LoggerService:
        """Get the logger instance, creating it if needed."""
        if self._logger is None:
            if self.logger_factory:
                self._logger = self.logger_factory.create("events.middleware.retry")
            else:
                self._logger = LoggerService(name="uno.events.middleware.retry")
        return self._logger
    
    async def process(
        self, 
        context: EventHandlerContext, 
        next_middleware: Callable[[EventHandlerContext], Result[Any, Exception]]
    ) -> Result[Any, Exception]:
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
                    self.logger.structured_log(
                        "INFO",
                        f"Event {event.event_type} succeeded after {attempt + 1} attempts",
                        name="uno.events.middleware.retry",
                        event_id=event.event_id,
                        aggregate_id=event.aggregate_id,
                        attempts=attempt + 1
                    )
                elif attempt >= self.options.max_retries and result.is_failure:
                    self.logger.structured_log(
                        "ERROR",
                        f"Event {event.event_type} failed after {attempt + 1} attempts: {result.error}",
                        name="uno.events.middleware.retry",
                        error=result.error,
                        event_id=event.event_id,
                        aggregate_id=event.aggregate_id,
                        attempts=attempt + 1
                    )
                
                return result
            
            # Check if we should retry
            if isinstance(result.error, Exception) and self.options.should_retry(result.error):
                attempt += 1
                delay_ms = self.options.get_delay_ms(attempt - 1)
                
                self.logger.structured_log(
                    "DEBUG",
                    f"Retrying event {event.event_type} after {delay_ms}ms (attempt {attempt + 1}/{self.options.max_retries + 1})",
                    name="uno.events.middleware.retry",
                    error=result.error,
                    event_id=event.event_id,
                    aggregate_id=event.aggregate_id,
                    attempt=attempt,
                    delay_ms=delay_ms
                )
                
                # Wait before retrying
                await asyncio.sleep(delay_ms / 1000)
            else:
                # Not retryable, return the failure
                self.logger.structured_log(
                    "DEBUG",
                    f"Error not retryable for event {event.event_type}: {result.error}",
                    name="uno.events.middleware.retry",
                    error=result.error,
                    event_id=event.event_id,
                    aggregate_id=event.aggregate_id
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
        options: CircuitBreakerState | None = None,
        logger_factory: LoggerServiceFactory | None = None
    ):
        """
        Initialize the middleware.
        
        Args:
            event_types: Optional list of event types to apply circuit breaking to.
                         If None, circuit breaking is applied to all event types.
            options: Optional circuit breaker options
            logger_factory: Optional factory for creating loggers
        """
        self.event_types = event_types
        self.options = options or CircuitBreakerState()
        self.logger_factory = logger_factory
        
        # Track circuit breaker state per event type
        self.circuit_states: dict[str, CircuitBreakerState] = defaultdict(
            lambda: CircuitBreakerState(
                failure_threshold=self.options.failure_threshold,
                recovery_timeout_seconds=self.options.recovery_timeout_seconds,
                success_threshold=self.options.success_threshold
            )
        )
        
        # Default logger is created on first access
        self._logger: LoggerService | None = None
    
    @property
    def logger(self) -> LoggerService:
        """Get the logger instance, creating it if needed."""
        if self._logger is None:
            if self.logger_factory:
                self._logger = self.logger_factory.create("events.middleware.circuit_breaker")
            else:
                self._logger = LoggerService(name="uno.events.middleware.circuit_breaker")
        return self._logger
    
    async def process(
        self, 
        context: EventHandlerContext, 
        next_middleware: Callable[[EventHandlerContext], Result[Any, Exception]]
    ) -> Result[Any, Exception]:
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
        circuit = self.circuit_states[event.event_type]
        
        # Check if the circuit allows execution
        if not circuit.can_execute():
            error = Exception(f"Circuit breaker open for event type {event.event_type}")
            
            self.logger.structured_log(
                "WARNING",
                f"Circuit breaker preventing execution of {event.event_type}",
                name="uno.events.middleware.circuit_breaker",
                event_id=event.event_id,
                aggregate_id=event.aggregate_id,
                circuit_state=circuit.state
            )
            
            return Failure(error)
        
        # Execute the event handler
        result = await next_middleware(context)
        
        # Record success or failure
        if result.is_success:
            circuit.record_success()
            
            # Log state transition if it happened
            if circuit.state == CircuitBreakerState.CLOSED and circuit.success_count == 0:
                self.logger.structured_log(
                    "INFO",
                    f"Circuit closed for event type {event.event_type}",
                    name="uno.events.middleware.circuit_breaker",
                    event_id=event.event_id,
                    aggregate_id=event.aggregate_id
                )
        else:
            circuit.record_failure()
            
            # Log state transition if it happened
            if circuit.state == CircuitBreakerState.OPEN and circuit.failure_count == circuit.failure_threshold:
                self.logger.structured_log(
                    "WARNING",
                    f"Circuit opened for event type {event.event_type} after {circuit.failure_threshold} failures",
                    name="uno.events.middleware.circuit_breaker",
                    event_id=event.event_id,
                    aggregate_id=event.aggregate_id,
                    error=result.error
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
        report_interval_seconds: float = 60.0,
        logger_factory: LoggerServiceFactory | None = None
    ):
        """
        Initialize the middleware.
        
        Args:
            report_interval_seconds: Interval in seconds to report metrics
            logger_factory: Optional factory for creating loggers
        """
        self.report_interval_seconds = report_interval_seconds
        self.last_report_time = time.time()
        self.metrics: dict[str, EventMetrics] = defaultdict(EventMetrics)
        self.logger_factory = logger_factory
        
        # Default logger is created on first access
        self._logger: LoggerService | None = None
    
    @property
    def logger(self) -> LoggerService:
        """Get the logger instance, creating it if needed."""
        if self._logger is None:
            if self.logger_factory:
                self._logger = self.logger_factory.create("events.middleware.metrics")
            else:
                self._logger = LoggerService(name="uno.events.middleware.metrics")
        return self._logger
    
    async def process(
        self, 
        context: EventHandlerContext, 
        next_middleware: Callable[[EventHandlerContext], Result[Any, Exception]]
    ) -> Result[Any, Exception]:
        """
        Collect metrics and pass to next middleware.
        
        Args:
            context: The event handler context
            next_middleware: The next middleware to call
            
        Returns:
            Result from the next middleware
        """
        event = context.event
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
        for event_type, metrics in self.metrics.items():
            self.logger.structured_log(
                "INFO",
                f"Event metrics for {event_type}",
                name="uno.events.middleware.metrics",
                event_type=event_type,
                count=metrics.count,
                success_count=metrics.success_count,
                failure_count=metrics.failure_count,
                success_rate=f"{metrics.success_rate:.2f}%",
                avg_duration_ms=f"{metrics.average_duration_ms:.2f}ms",
                min_duration_ms=f"{metrics.min_duration_ms:.2f}ms" if metrics.min_duration_ms != float('inf') else "N/A",
                max_duration_ms=f"{metrics.max_duration_ms:.2f}ms"
            )
