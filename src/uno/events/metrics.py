"""
Event metrics integration for the Uno framework.

This module provides metrics collection and reporting for event processing,
including event counts, processing times, and error rates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from uno.events.protocols import DomainEventProtocol
    from uno.logging.protocols import LoggerProtocol
    from uno.metrics.protocols import (
        CounterProtocol,
        GaugeProtocol,
        HistogramProtocol,
        MetricProtocol,
        TimerProtocol,
    )

E = TypeVar("E", bound="DomainEventProtocol")


class EventMetrics:
    """Metrics collected for event processing."""

    def __init__(
        self,
        metrics_factory: MetricProtocol,
        logger: LoggerProtocol,
    ) -> None:
        """Initialize event metrics with the given factory and logger.

        Args:
            metrics_factory: Factory for creating metric instances
            logger: Logger for reporting issues
        """
        self.metrics_factory = metrics_factory
        self.logger = logger

        # Event counters
        self.events_published = self._create_counter(
            "events_published_total",
            "Total number of events published",
            ["event_type"],
        )
        self.events_processed = self._create_counter(
            "events_processed_total",
            "Total number of events processed successfully",
            ["event_type"],
        )
        self.event_errors = self._create_counter(
            "event_errors_total",
            "Total number of event processing errors",
            ["event_type", "error_type"],
        )

        # Event timing
        self.processing_time = self._create_histogram(
            "event_processing_seconds",
            "Time taken to process events in seconds",
            ["event_type"],
        )

        # Active events gauge
        self.active_events = self._create_gauge(
            "active_events",
            "Number of events currently being processed",
            ["event_type"],
        )

    async def _create_counter(
        self, name: str, description: str, tags: list[str] | None = None
    ) -> CounterProtocol:
        """Create a counter metric.

        Args:
            name: Metric name
            description: Metric description
            tags: Optional list of tag names

        Returns:
            Configured counter instance
        """
        try:
            return self.metrics_factory.create_counter(name, description, tags or [])
        except Exception as e:
            await self.logger.warning(
                f"Failed to create counter {name}",
                error=str(e),
                exc_info=True,
            )
            return self.metrics_factory.create_counter("dummy_counter", "Dummy counter")

    async def _create_gauge(
        self, name: str, description: str, tags: list[str] | None = None
    ) -> GaugeProtocol:
        """Create a gauge metric.

        Args:
            name: Metric name
            description: Metric description
            tags: Optional list of tag names

        Returns:
            Configured gauge instance
        """
        try:
            return self.metrics_factory.create_gauge(name, description, tags or [])
        except Exception as e:
            await self.logger.warning(
                f"Failed to create gauge {name}",
                error=str(e),
                exc_info=True,
            )
            return self.metrics_factory.create_gauge("dummy_gauge", "Dummy gauge")

    async def _create_histogram(
        self, name: str, description: str, tags: list[str] | None = None
    ) -> HistogramProtocol:
        """Create a histogram metric.

        Args:
            name: Metric name
            description: Metric description
            tags: Optional list of tag names

        Returns:
            Configured histogram instance
        """
        try:
            return self.metrics_factory.create_histogram(name, description, tags or [])
        except Exception as e:
            await self.logger.warning(
                f"Failed to create histogram {name}",
                error=str(e),
                exc_info=True,
            )
            return self.metrics_factory.create_histogram(
                "dummy_histogram", "Dummy histogram"
            )

    async def _create_timer(
        self, name: str, description: str, tags: list[str] | None = None
    ) -> TimerProtocol:
        """Create a timer metric.

        Args:
            name: Metric name
            description: Metric description
            tags: Optional list of tag names

        Returns:
            Configured timer instance
        """
        try:
            return self.metrics_factory.create_timer(name, description, tags or [])
        except Exception as e:
            await self.logger.warning(
                f"Failed to create timer {name}",
                error=str(e),
                exc_info=True,
            )
            return self.metrics_factory.create_timer("dummy_timer", "Dummy timer")

    async def record_event_published(self, event: E) -> None:
        """Record that an event was published.

        Args:
            event: The published event
        """
        if not self.metrics_factory:
            return

        try:
            await self.events_published.increment()
        except Exception as e:
            if self.logger:
                await self.logger.error(
                    "Failed to record event published metric",
                    error=str(e),
                    event_type=getattr(event, "event_type", "unknown"),
                )

    async def record_event_processed(self, event: E) -> None:
        """Record that an event was processed successfully.

        Args:
            event: The processed event
        """
        if not self.metrics_factory:
            return

        try:
            await self.events_processed.increment()
        except Exception as e:
            if self.logger:
                await self.logger.error(
                    "Failed to record event processed metric",
                    error=str(e),
                    event_type=getattr(event, "event_type", "unknown"),
                )

    async def record_event_error(self, event: E, error: Exception) -> None:
        """Record that an error occurred while processing an event.

        Args:
            event: The event that caused the error
            error: The exception that was raised
        """
        if not self.metrics_factory:
            return

        try:
            await self.event_errors.increment()
        except Exception as e:
            if self.logger:
                await self.logger.error(
                    "Failed to record event error metric",
                    error=str(e),
                    event_type=getattr(event, "event_type", "unknown"),
                )

    async def record_processing_time(self, event: E, duration: float) -> None:
        """Record the time taken to process an event.

        Args:
            event: The processed event
            duration: Processing time in seconds
        """
        if not self.metrics_factory:
            return

        try:
            await self.processing_time.observe(duration)
        except Exception as e:
            if self.logger:
                await self.logger.error(
                    "Failed to record processing time metric",
                    error=str(e),
                    event_type=getattr(event, "event_type", "unknown"),
                )

    async def increment_active_events(self, event: E) -> None:
        """Increment the count of active events.

        Args:
            event: The event being processed
        """
        if not self.metrics_factory:
            return

        try:
            await self.active_events.increment()
        except Exception as e:
            if self.logger:
                await self.logger.error(
                    "Failed to increment active events metric",
                    error=str(e),
                    event_type=getattr(event, "event_type", "unknown"),
                )

    async def decrement_active_events(self, event: E) -> None:
        """Decrement the count of active events.

        Args:
            event: The event that was processed
        """
        if not self.metrics_factory:
            return

        try:
            await self.active_events.decrement()
        except Exception as e:
            if self.logger:
                await self.logger.error(
                    "Failed to decrement active events metric",
                    error=str(e),
                    event_type=getattr(event, "event_type", "unknown"),
                )


async def create_event_metrics(
    metrics_factory: MetricProtocol | None = None, logger: LoggerProtocol | None = None
) -> EventMetrics:
    """Create and initialize event metrics.

    This is a convenience function that creates an EventMetrics instance with the given factory and logger.

    Args:
        metrics_factory: Factory for creating metric instances
        logger: Logger for error reporting

    Returns:
        EventMetrics: Initialized event metrics instance
    """
    # We need to ensure metrics_factory and logger are not None
    if metrics_factory is None or logger is None:
        raise ValueError("Both metrics_factory and logger must be provided")

    return EventMetrics(metrics_factory=metrics_factory, logger=logger)
