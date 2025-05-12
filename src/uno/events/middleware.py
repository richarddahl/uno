"""
Middleware implementations for event processing.

This module provides middleware components that can be used to add
cross-cutting concerns to event processing, such as retrying, metrics,
and circuit breaking.
"""

from __future__ import annotations

import asyncio
import time
from enum import Enum, auto
from typing import TYPE_CHECKING, Protocol

from uno.domain.protocols import DomainEventProtocol
from uno.events.errors import EventHandlerError

if TYPE_CHECKING:
    from uno.logging.protocols import LoggerProtocol
    from uno.metrics.protocols import CounterProtocol, GaugeProtocol, TimerProtocol


class NextMiddlewareCallable(Protocol):
    """Protocol for the next middleware in the chain."""

    async def __call__(self, event: DomainEventProtocol) -> None: ...


class RetryOptions:
    """Configuration options for retry middleware."""

    def __init__(
        self,
        max_attempts: int = 3,
        delay_ms: int = 500,
        backoff_factor: float = 1.5,
        max_delay_ms: int = 10000,
    ) -> None:
        """
        Initialize retry options.

        Args:
            max_attempts: Maximum number of retry attempts
            delay_ms: Initial delay between retries in milliseconds
            backoff_factor: Factor to increase delay by after each retry
            max_delay_ms: Maximum delay between retries in milliseconds
        """
        self.max_attempts = max_attempts
        self.delay_ms = delay_ms
        self.backoff_factor = backoff_factor
        self.max_delay_ms = max_delay_ms


class RetryMiddleware:
    """
    Middleware for automatically retrying failed event handlers.

    This middleware will catch exceptions from event handlers and retry
    the operation based on the configured retry options.
    """

    def __init__(
        self,
        logger: "LoggerProtocol",
        options: RetryOptions | None = None,
    ) -> None:
        """
        Initialize the retry middleware.

        Args:
            logger: Logger for structured logging
            options: Retry configuration options
        """
        self.logger = logger
        self.options = options or RetryOptions()

    async def process(
        self,
        event: "DomainEventProtocol",
        next_middleware: NextMiddlewareCallable,
    ) -> None:
        """
        Process an event with retry logic.

        Args:
            event: The domain event to process
            next_middleware: The next middleware to call

        Raises:
            EventHandlerError: If all retry attempts fail
        """
        attempt = 0
        last_error = None
        delay_ms = self.options.delay_ms

        while attempt < self.options.max_attempts:
            try:
                if attempt > 0:
                    self.logger.info(
                        f"Retrying event handler (attempt {attempt+1}/{self.options.max_attempts})",
                        event_type=getattr(event, "event_type", None),
                        event_id=getattr(event, "event_id", None),
                        retry_attempt=attempt + 1,
                        max_attempts=self.options.max_attempts,
                    )

                # Call the next middleware in the chain
                await next_middleware(event)

                # If we get here, it succeeded
                if attempt > 0:
                    self.logger.info(
                        "Retry successful",
                        event_type=getattr(event, "event_type", None),
                        event_id=getattr(event, "event_id", None),
                        retry_attempt=attempt + 1,
                    )

                return

            except Exception as e:
                attempt += 1
                last_error = e

                if attempt >= self.options.max_attempts:
                    # We've used all our retry attempts
                    break

                self.logger.warning(
                    f"Event handler failed (will retry)",
                    event_type=getattr(event, "event_type", None),
                    event_id=getattr(event, "event_id", None),
                    retry_attempt=attempt,
                    max_attempts=self.options.max_attempts,
                    error=str(e),
                )

                # Wait before the next retry, with exponential backoff
                await asyncio.sleep(delay_ms / 1000.0)
                delay_ms = min(
                    delay_ms * self.options.backoff_factor, self.options.max_delay_ms
                )

        # If we get here, all retries failed
        self.logger.error(
            "All retry attempts failed",
            event_type=getattr(event, "event_type", None),
            event_id=getattr(event, "event_id", None),
            retry_attempts=attempt,
            max_attempts=self.options.max_attempts,
            error=str(last_error),
        )

        if last_error:
            if isinstance(last_error, EventHandlerError):
                raise last_error

            handler_name = "unknown"  # We don't have access to the handler name here
            raise EventHandlerError(
                event_type=getattr(event, "event_type", type(event).__name__),
                handler_name=handler_name,
                reason=f"Failed after {attempt} retry attempts: {last_error}",
            ) from last_error


class CircuitBreakerState(Enum):
    """Possible states for the circuit breaker."""

    CLOSED = auto()  # Normal operation, requests go through
    OPEN = auto()  # Circuit is open, all requests fail fast
    HALF_OPEN = auto()  # Testing if the service is back online


class CircuitBreakerMiddleware:
    """
    Middleware implementing the circuit breaker pattern.

    This middleware will track failures and "trip" (open the circuit) when
    too many failures occur in a short period, preventing further calls
    that are likely to fail and allowing the system time to recover.
    """

    def __init__(
        self,
        logger: "LoggerProtocol",
        failure_threshold: int = 5,
        reset_timeout_seconds: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        """
        Initialize the circuit breaker middleware.

        Args:
            logger: Logger for structured logging
            failure_threshold: Number of failures before opening the circuit
            reset_timeout_seconds: Time to wait before testing if service is back
            half_open_max_calls: Number of test calls to allow in half-open state
        """
        self.logger = logger
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.half_open_calls = 0

    async def process(
        self,
        event: "DomainEventProtocol",
        next_middleware: NextMiddlewareCallable,
    ) -> None:
        """
        Process an event through the circuit breaker.

        Args:
            event: The domain event to process
            next_middleware: The next middleware to call

        Raises:
            EventHandlerError: If the circuit is open or the handler fails
        """
        # Check circuit state
        if self.state == CircuitBreakerState.OPEN:
            # Check if it's time to try again
            if time.time() - self.last_failure_time >= self.reset_timeout_seconds:
                self.logger.info(
                    "Circuit half-open, allowing test call",
                    event_type=getattr(event, "event_type", None),
                    event_id=getattr(event, "event_id", None),
                )
                self.state = CircuitBreakerState.HALF_OPEN
                self.half_open_calls = 0
            else:
                # Still open, fail fast
                raise EventHandlerError(
                    event_type=getattr(event, "event_type", type(event).__name__),
                    handler_name="circuit_breaker",
                    reason="Circuit breaker is open",
                )

        if self.state == CircuitBreakerState.HALF_OPEN:
            # Only allow a limited number of test calls
            if self.half_open_calls >= self.half_open_max_calls:
                raise EventHandlerError(
                    event_type=getattr(event, "event_type", type(event).__name__),
                    handler_name="circuit_breaker",
                    reason="Circuit breaker is half-open and max test calls reached",
                )
            self.half_open_calls += 1

        try:
            # Attempt to process the event
            await next_middleware(event)

            # Success - if we were in half-open state, close the circuit
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.logger.info(
                    "Circuit closed after successful test call",
                    event_type=getattr(event, "event_type", None),
                    event_id=getattr(event, "event_id", None),
                )
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0

            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0

        except Exception as e:
            # Track this failure
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitBreakerState.HALF_OPEN:
                # Failed test call, reopen the circuit
                self.logger.warning(
                    "Circuit reopened after failed test call",
                    event_type=getattr(event, "event_type", None),
                    event_id=getattr(event, "event_id", None),
                    error=str(e),
                )
                self.state = CircuitBreakerState.OPEN

            elif (
                self.state == CircuitBreakerState.CLOSED
                and self.failure_count >= self.failure_threshold
            ):
                # Too many failures, open the circuit
                self.logger.warning(
                    f"Circuit opened after {self.failure_count} failures",
                    event_type=getattr(event, "event_type", None),
                    event_id=getattr(event, "event_id", None),
                    error=str(e),
                )
                self.state = CircuitBreakerState.OPEN

            # Re-raise the original exception
            raise


class EventMetrics:
    """Metrics collected for event processing."""

    def __init__(
        self,
        event_count: "CounterProtocol",
        event_processing_time: "TimerProtocol",
        event_errors: "CounterProtocol",
        active_events: "GaugeProtocol",
    ) -> None:
        """
        Initialize event metrics.

        Args:
            event_count: Counter for events processed
            event_processing_time: Timer for event processing duration
            event_errors: Counter for event processing errors
            active_events: Gauge for currently processing events
        """
        self.event_count = event_count
        self.event_processing_time = event_processing_time
        self.event_errors = event_errors
        self.active_events = active_events


class MetricsMiddleware:
    """
    Middleware for collecting metrics during event processing.

    This middleware will track event counts, processing time, errors,
    and active event processing.
    """

    def __init__(
        self,
        logger: "LoggerProtocol",
        metrics: EventMetrics,
    ) -> None:
        """
        Initialize the metrics middleware.

        Args:
            logger: Logger for structured logging
            metrics: Metrics collection for events
        """
        self.logger = logger
        self.metrics = metrics

    async def process(
        self,
        event: "DomainEventProtocol",
        next_middleware: NextMiddlewareCallable,
    ) -> None:
        """
        Process an event and collect metrics.

        Args:
            event: The domain event to process
            next_middleware: The next middleware to call

        Raises:
            Exception: If the handler fails
        """
        # Track the event
        self.metrics.event_count.increment()
        self.metrics.active_events.increment()

        start_time = time.time()

        try:
            # Process the event
            await next_middleware(event)
        except Exception as e:
            # Track errors
            self.metrics.event_errors.increment()

            tag_dict = {
                "event_type": getattr(event, "event_type", None),
                "error_type": type(e).__name__,
            }

            self.metrics.event_errors.increment(tags=tag_dict)

            # Re-raise the exception
            raise
        finally:
            # Track processing time
            elapsed = time.time() - start_time

            tags = {
                "event_type": getattr(event, "event_type", None),
            }

            self.metrics.event_processing_time.record(elapsed, tags=tags)
            self.metrics.active_events.decrement()
