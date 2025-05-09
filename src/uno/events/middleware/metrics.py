"""
MetricsMiddleware: Collects metrics about event handler performance.
"""

import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uno.errors.result import Result
from uno.events.handlers import EventHandlerContext
from uno.events.interfaces import EventHandlerMiddleware
from uno.logging.logger import LoggerService


@dataclass
class EventMetrics:
    count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    max_duration_ms: float = 0.0

    @property
    def average_duration_ms(self) -> float:
        if self.count == 0:
            return 0.0
        return self.total_duration_ms / self.count

    @property
    def success_rate(self) -> float:
        if self.count == 0:
            return 0.0
        return (self.success_count / self.count) * 100.0

    def record(self, duration_ms: float, success: bool) -> None:
        self.count += 1
        self.total_duration_ms += duration_ms
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)


class MetricsMiddleware(EventHandlerMiddleware):
    """
    MetricsMiddleware: Collects metrics about event handler performance.
    Requires a DI-injected LoggerService instance (strict DI).
    """

    def __init__(
        self, logger: LoggerService, report_interval_seconds: float = 60.0
    ) -> None:
        self.logger = logger
        self.report_interval_seconds = report_interval_seconds
        self.last_report_time = time.time()
        self.metrics: dict[str, EventMetrics] = defaultdict(EventMetrics)

    async def process(
        self,
        context: EventHandlerContext,
        next_middleware: Callable[[EventHandlerContext], Result[Any, Exception]],
    ) -> Result[Any, Exception]:
        event = context.event
        start_time = time.time()
        result = await next_middleware(context)
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        self.metrics[event.event_type].record(duration_ms, result.is_success)
        current_time = time.time()
        if current_time - self.last_report_time >= self.report_interval_seconds:
            self._report_metrics()
            self.last_report_time = current_time
        return result

    def _report_metrics(self) -> None:
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
                min_duration_ms=(
                    f"{metrics.min_duration_ms:.2f}ms"
                    if metrics.min_duration_ms != float("inf")
                    else "N/A"
                ),
                max_duration_ms=f"{metrics.max_duration_ms:.2f}ms",
            )
