"""
Standard event metric names and types for Uno event-driven systems.
"""

EVENT_METRIC_PUBLISHED = "events.published"
EVENT_METRIC_PROCESSED = "events.processed"
EVENT_METRIC_FAILED = "events.failed"
EVENT_METRIC_RETRIED = "events.retried"
EVENT_METRIC_LATENCY = "events.latency"

STANDARD_EVENT_METRICS = [
    EVENT_METRIC_PUBLISHED,
    EVENT_METRIC_PROCESSED,
    EVENT_METRIC_FAILED,
    EVENT_METRIC_RETRIED,
    EVENT_METRIC_LATENCY,
]
