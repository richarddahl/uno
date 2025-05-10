"""
RetryMiddleware: Automatically retries failed event handlers.
"""

import asyncio
from collections.abc import Callable
from typing import Any

from uno.events.handlers import EventHandlerContext
from uno.events.interfaces import EventHandlerMiddleware
from uno.logging.protocols import LoggerProtocol
from dataclasses import dataclass, field


@dataclass
class RetryOptions:
    max_retries: int = 3
    base_delay_ms: int = 100
    max_delay_ms: int = 5000
    backoff_factor: float = 2.0
    retryable_exceptions: list[type[Exception]] = field(default_factory=list)

    def should_retry(self, error: Exception) -> bool:
        if not self.retryable_exceptions:
            return True
        return any(
            isinstance(error, exc_type) for exc_type in self.retryable_exceptions
        )

    def get_delay_ms(self, attempt: int) -> int:
        delay = self.base_delay_ms * (self.backoff_factor**attempt)
        return min(int(delay), self.max_delay_ms)


class RetryMiddleware(EventHandlerMiddleware):
    """
    RetryMiddleware: Automatically retries failed event handlers.
    Requires a DI-injected LoggerProtocol instance (strict DI).
    """

    def __init__(
        self, logger: LoggerProtocol, options: RetryOptions | None = None
    ) -> None:
        self.logger = logger
        self.options = options or RetryOptions()

    async def process(
        self,
        context: EventHandlerContext,
        next_middleware: Callable[[EventHandlerContext], None],
    ) -> None:
        event = context.event
        attempt = 0
        while True:
            try:
                await next_middleware(context)
                if attempt > 0:
                    self.logger.structured_log(
                        "INFO",
                        f"Event {event.event_type} succeeded after {attempt + 1} attempts",
                        name="uno.events.middleware.retry",
                        event_id=event.event_id,
                        aggregate_id=event.aggregate_id,
                    )
                return
            except Exception as err:
                if not self.options.should_retry(err) or attempt >= self.options.max_retries:
                    self.logger.structured_log(
                        "ERROR",
                        f"Event {event.event_type} failed after {attempt + 1} attempts",
                        name="uno.events.middleware.retry",
                        event_id=event.event_id,
                        aggregate_id=event.aggregate_id,
                        error=err,
                    )
                    raise
                self.logger.structured_log(
                    "WARNING",
                    f"Retrying event {event.event_type} (attempt {attempt + 1}) after {self.options.get_delay_ms(attempt)}ms",
                    name="uno.events.middleware.retry",
                    event_id=event.event_id,
                    aggregate_id=event.aggregate_id,
                    attempt=attempt + 1,
                    delay_ms=self.options.get_delay_ms(attempt),
                )
                await asyncio.sleep(self.options.get_delay_ms(attempt) / 1000)
                attempt += 1
