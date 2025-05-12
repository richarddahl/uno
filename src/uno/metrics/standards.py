"""
Standard metric names and conventions for the Uno metrics system.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal


class MetricNames(str, Enum):
    """Standard metric names used across Uno."""

    # Event metrics
    EVENTS_PROCESSING_TIME = "events.processing_time"
    EVENTS_PROCESSED = "events.processed"
    EVENTS_PROCESSING_ERRORS = "events.processing_errors"
    EVENTS_IN_FLIGHT = "events.in_flight"

    # Error metrics
    ERRORS_TOTAL = "errors.total"
    ERRORS_BY_TYPE = "errors.by_type"
    ERRORS_PROCESSING_TIME = "errors.processing_time"

    # System metrics
    SYSTEM_MEMORY_USAGE = "system.memory_usage"
    SYSTEM_CPU_USAGE = "system.cpu_usage"
    SYSTEM_THREAD_COUNT = "system.thread_count"

    # Handler metrics
    HANDLERS_TOTAL = "handlers.total"
    HANDLERS_ACTIVE = "handlers.active"
    HANDLERS_PROCESSING_TIME = "handlers.processing_time"

    # Bus metrics
    BUS_EVENTS_RECEIVED = "bus.events_received"
    BUS_EVENTS_PUBLISHED = "bus.events_published"
    BUS_EVENTS_FAILED = "bus.events_failed"

    # Integration metrics
    INTEGRATION_LATENCY = "integration.latency"
    INTEGRATION_FAILURES = "integration.failures"
    INTEGRATION_THROUGHPUT = "integration.throughput"

    # Custom metrics
    CUSTOM = "custom"


class MetricTags:
    """Standard tags for metrics."""

    ENVIRONMENT = "environment"
    SERVICE = "service"
    COMPONENT = "component"
    OPERATION = "operation"
    STATUS = "status"
    TYPE = "type"


class MetricUnits:
    """Standard units for metrics."""

    SECONDS = "seconds"
    MILLISECONDS = "milliseconds"
    BYTES = "bytes"
    COUNT = "count"
    PERCENT = "percent"
    RATIO = "ratio"


class MetricTypes:
    """Standard metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


def create_metric_name(
    base: str,
    component: str,
    operation: str,
    suffix: str = "",
) -> str:
    """Create a standardized metric name.

    Args:
        base: Base name of the metric
        component: Component name
        operation: Operation name
        suffix: Optional suffix to add to the name

    Returns:
        Standardized metric name
    """
    parts = [base, component, operation]
    if suffix:
        parts.append(suffix)
    return ".".join(parts)


def create_metric_tags(
    environment: str,
    service: str,
    component: str,
    operation: str,
    status: str = "",
    type_: str = "",
) -> dict[str, str]:
    """Create standardized metric tags.

    Args:
        environment: Environment name (prod, dev, etc.)
        service: Service name
        component: Component name
        operation: Operation name
        status: Optional status tag
        type_: Optional type tag

    Returns:
        Dictionary of metric tags
    """
    tags = {
        MetricTags.ENVIRONMENT: environment,
        MetricTags.SERVICE: service,
        MetricTags.COMPONENT: component,
        MetricTags.OPERATION: operation,
    }
    if status:
        tags[MetricTags.STATUS] = status
    if type_:
        tags[MetricTags.TYPE] = type_
    return tags
