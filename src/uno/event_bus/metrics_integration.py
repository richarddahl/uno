"""Integration with Uno's metrics system for event bus monitoring."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, TypeVar

from uno.domain.protocols import DomainEventProtocol
from uno.logging import LoggerProtocol
from uno.metrics import Counter, Gauge, Histogram, Timer

E = TypeVar("E", bound=DomainEventProtocol)


class EventBusMetrics:
    """Metrics collector for the event bus using Uno's metrics system.
    
    This class provides a consistent interface for collecting and reporting
    metrics about event bus operations.
    """
    
    def __init__(self, logger: LoggerProtocol) -> None:
        """Initialize the metrics collector.
        
        Args:
            logger: Logger instance for error reporting
        """
        self._logger = logger
        
        # Initialize counters
        self.events_published = Counter(
            "event_bus_events_published_total",
            "Total number of events published to the event bus"
        )
        
        self.events_processed = Counter(
            "event_bus_events_processed_total",
            "Total number of events processed by the event bus"
        )
        
        self.event_retries = Counter(
            "event_bus_event_retries_total",
            "Total number of event processing retries"
        )
        
        self.dead_letter_events = Counter(
            "event_bus_dead_letter_events_total",
            "Total number of events sent to dead letter queue"
        )
        
        # Initialize histograms
        self.processing_time = Histogram(
            "event_bus_processing_duration_seconds",
            "Time taken to process events in seconds"
        )
        
        # Initialize gauges
        self.active_subscriptions = Gauge(
            "event_bus_active_subscriptions",
            "Current number of active subscriptions"
        )
        
        self.queued_events = Gauge(
            "event_bus_queued_events",
            "Current number of events waiting to be processed"
        )
        
        # Store metrics for easy access
        self._metrics = {
            "events_published": self.events_published,
            "events_processed": self.events_processed,
            "event_retries": self.event_retries,
            "dead_letter_events": self.dead_letter_events,
            "processing_time": self.processing_time,
            "active_subscriptions": self.active_subscriptions,
            "queued_events": self.queued_events,
        }
    
    def record_event_published(self, event: E) -> None:
        """Record that an event was published.
        
        Args:
            event: The event that was published
        """
        try:
            self.events_published.inc()
        except Exception as e:
            self._logger.error("Failed to record event published metric", error=str(e))
    
    def record_event_processed(
        self, event: E, duration_seconds: float, success: bool
    ) -> None:
        """Record that an event was processed.
        
        Args:
            event: The event that was processed
            duration_seconds: How long processing took in seconds
            success: Whether processing was successful
        """
        try:
            self.events_processed.inc()
            self.processing_time.observe(duration_seconds)
        except Exception as e:
            self._logger.error("Failed to record event processed metric", error=str(e))
    
    def record_retry(self, event: E, attempt: int, delay_seconds: float) -> None:
        """Record that an event is being retried.
        
        Args:
            event: The event being retried
            attempt: The attempt number (1-based)
            delay_seconds: How long until the next retry
        """
        try:
            self.event_retries.inc()
        except Exception as e:
            self._logger.error("Failed to record retry metric", error=str(e))
    
    def record_dead_letter(
        self, event: E, reason: str, error: Optional[Exception] = None
    ) -> None:
        """Record that an event was dead-lettered.
        
        Args:
            event: The event that was dead-lettered
            reason: Why the event was dead-lettered
            error: The error that caused the dead-lettering, if any
        """
        try:
            self.dead_letter_events.inc()
        except Exception as e:
            self._logger.error("Failed to record dead letter metric", error=str(e))
    
    def update_subscription_count(self, count: int) -> None:
        """Update the count of active subscriptions.
        
        Args:
            count: Current number of active subscriptions
        """
        try:
            self.active_subscriptions.set(count)
        except Exception as e:
            self._logger.error("Failed to update subscription count metric", error=str(e))
    
    def update_queued_events_count(self, count: int) -> None:
        """Update the count of queued events.
        
        Args:
            count: Current number of queued events
        """
        try:
            self.queued_events.set(count)
        except Exception as e:
            self._logger.error("Failed to update queued events metric", error=str(e))
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get the current metric values.
        
        Returns:
            Dictionary of metric names to their current values
        """
        return {
            name: metric.get() 
            for name, metric in self._metrics.items()
        }


class MetricsMiddleware:
    """Middleware that collects metrics for event processing."""
    
    def __init__(self, metrics: EventBusMetrics) -> None:
        """Initialize the middleware.
        
        Args:
            metrics: The metrics collector to use
        """
        self._metrics = metrics
    
    async def process(self, event: E, next_fn: Any) -> None:
        """Process an event and record metrics.
        
        Args:
            event: The event to process
            next_fn: The next middleware or handler in the chain
        """
        # Record that the event was published
        self._metrics.record_event_published(event)
        
        # Process the event and time it
        start_time = time.monotonic()
        try:
            await next_fn(event)
            duration = time.monotonic() - start_time
            self._metrics.record_event_processed(event, duration, success=True)
        except Exception as e:
            duration = time.monotonic() - start_time
            self._metrics.record_event_processed(event, duration, success=False)
            raise
