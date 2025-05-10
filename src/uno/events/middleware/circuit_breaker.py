"""
CircuitBreakerMiddleware: Prevents cascading failures using the circuit breaker pattern.
"""

import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from uno.events.handlers import EventHandlerContext
from uno.events.interfaces import EventHandlerMiddleware
from uno.logging.logger import get_logger
from uno.logging.protocols import LoggerProtocol

logger = get_logger("uno.events.middleware.circuit_breaker")


@dataclass
class CircuitBreakerState:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    state: str = CLOSED
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    success_threshold: int = 1
    failure_count: int = 0
    success_count: int = 0
    opened_at: float = 0.0

    def record_success(self) -> None:
        if self.state == self.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = self.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == self.OPEN:
            # Should not happen, but reset if it does
            self.state = self.CLOSED
            self.failure_count = 0
            self.success_count = 0

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = self.OPEN
            self.opened_at = time.time()

    def can_execute(self) -> bool:
        current_time = time.time()
        if self.state == self.OPEN:
            if current_time - self.opened_at >= self.recovery_timeout_seconds:
                self.state = self.HALF_OPEN
                self.success_count = 0
                return True
            return False
        return True


class CircuitBreakerMiddleware(EventHandlerMiddleware):
    """
    CircuitBreakerMiddleware: Prevents cascading failures using the circuit breaker pattern.
    Requires a DI-injected LoggerProtocol instance (strict DI).
    """

    def __init__(
        self,
        logger: LoggerProtocol,
        event_types: list[str] | None = None,
        options: CircuitBreakerState | None = None,
    ) -> None:
        self.logger = logger
        self.event_types = event_types
        self.options = options or CircuitBreakerState()
        self.circuit_states: dict[str, CircuitBreakerState] = defaultdict(
            lambda: CircuitBreakerState(
                failure_threshold=self.options.failure_threshold,
                recovery_timeout_seconds=self.options.recovery_timeout_seconds,
                success_threshold=self.options.success_threshold,
            )
        )

    async def process(
        self,
        context: EventHandlerContext,
        next_middleware: Callable[[EventHandlerContext], None],
    ) -> None:
        event = context.event
        event_type = event.event_type
        circuit = self.circuit_states[event_type]
        if self.event_types is not None and event_type not in self.event_types:
            return await next_middleware(context)
        if not circuit.can_execute():
            logger.structured_log(
                "WARNING",
                f"Circuit open for event type {event_type}, skipping event",
                name="uno.events.middleware.circuit_breaker",
                event_id=event.event_id,
                aggregate_id=event.aggregate_id,
            )
            return False
        try:
            await next_middleware(context)
            circuit.record_success()
        except Exception as err:
            circuit.record_failure()
            if (
                circuit.state == CircuitBreakerState.OPEN
                and circuit.failure_count == circuit.failure_threshold
            ):
                self.logger.structured_log(
                    "WARNING",
                    f"Circuit opened for event type {event_type} after {circuit.failure_threshold} failures",
                    name="uno.events.middleware.circuit_breaker",
                    event_id=event.event_id,
                    aggregate_id=event.aggregate_id,
                    error=err,
                )
            raise
        # No return value; exceptions propagate
