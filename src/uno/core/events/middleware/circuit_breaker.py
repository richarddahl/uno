"""
CircuitBreakerMiddleware: Prevents cascading failures using the circuit breaker pattern.
"""
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uno.core.errors.result import Result
from uno.core.events.handlers import EventHandlerContext
from uno.core.events.interfaces import EventHandlerMiddleware
from uno.core.logging.factory import LoggerServiceFactory
from uno.core.logging.logger import LoggerService

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
    def __init__(
        self,
        event_types: list[str] | None = None,
        options: CircuitBreakerState | None = None,
        logger_factory: LoggerServiceFactory | None = None
    ):
        self.event_types = event_types
        self.options = options or CircuitBreakerState()
        self.logger_factory = logger_factory
        self.circuit_states: dict[str, CircuitBreakerState] = defaultdict(
            lambda: CircuitBreakerState(
                failure_threshold=self.options.failure_threshold,
                recovery_timeout_seconds=self.options.recovery_timeout_seconds,
                success_threshold=self.options.success_threshold
            )
        )
        self._logger: LoggerService | None = None

    @property
    def logger(self) -> LoggerService:
        if self._logger is None:
            if self.logger_factory:
                self._logger = self.logger_factory.create("events.middleware.circuit_breaker")
            else:
                from uno.core.logging.config import LoggingConfig
                self._logger = LoggerService(LoggingConfig())
        return self._logger

    async def process(
        self,
        context: EventHandlerContext,
        next_middleware: Callable[[EventHandlerContext], Result[Any, Exception]]
    ) -> Result[Any, Exception]:
        event = context.event
        event_type = event.event_type
        circuit = self.circuit_states[event_type]
        if self.event_types is not None and event_type not in self.event_types:
            return await next_middleware(context)
        if not circuit.can_execute():
            self.logger.structured_log(
                "WARNING",
                f"Circuit open for event type {event_type}, skipping event",
                name="uno.events.middleware.circuit_breaker",
                event_id=event.event_id,
                aggregate_id=event.aggregate_id
            )
            return Result.failure(Exception(f"Circuit open for event type {event_type}"))
        result = await next_middleware(context)
        if result.is_success:
            circuit.record_success()
        else:
            circuit.record_failure()
            if circuit.state == CircuitBreakerState.OPEN and circuit.failure_count == circuit.failure_threshold:
                self.logger.structured_log(
                    "WARNING",
                    f"Circuit opened for event type {event_type} after {circuit.failure_threshold} failures",
                    name="uno.events.middleware.circuit_breaker",
                    event_id=event.event_id,
                    aggregate_id=event.aggregate_id,
                    error=result.error
                )
        return result
