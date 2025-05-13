"""
Concrete metric types for the metrics system.

This module provides implementations of the metric protocol interfaces.
"""

from __future__ import annotations

import asyncio
from typing import Any

from uno.metrics.protocols import (
    CounterProtocol,
    GaugeProtocol,
    HistogramProtocol,
    TimerContextProtocol,
    TimerProtocol,
)


class Counter:
    """Counter metric implementation."""

    def __init__(
        self, name: str, description: str, tags: dict[str, str] | None = None
    ) -> None:
        """Initialize the counter.

        Args:
            name: The name of the counter
            description: A description of what the counter measures
            tags: Optional tags/labels for the counter
        """
        self._value = 0.0
        self.name = name
        self.description = description
        self.tags = tags or {}

    async def inc(self, amount: float = 1.0) -> None:
        """Increment counter by the given amount.

        Args:
            amount: Amount to increment
        """
        self._value += amount

    async def dec(self, amount: float = 1.0) -> None:
        """Decrement counter by the given amount.

        Args:
            amount: Amount to decrement
        """
        self._value -= amount

    async def get_value(self) -> float:
        """Get the current value of the counter.

        Returns:
            The current counter value
        """
        return self._value


class Gauge:
    """Gauge metric implementation."""

    def __init__(
        self, name: str, description: str, tags: dict[str, str] | None = None
    ) -> None:
        """Initialize the gauge.

        Args:
            name: The name of the gauge
            description: A description of what the gauge measures
            tags: Optional tags/labels for the gauge
        """
        self._value = 0.0
        self.name = name
        self.description = description
        self.tags = tags or {}

    async def set(self, value: float) -> None:
        """Set gauge to the given value.

        Args:
            value: Value to set
        """
        self._value = value

    async def inc(self, amount: float = 1.0) -> None:
        """Increment gauge by the given amount.

        Args:
            amount: Amount to increment
        """
        self._value += amount

    async def dec(self, amount: float = 1.0) -> None:
        """Decrement gauge by the given amount.

        Args:
            amount: Amount to decrement
        """
        self._value -= amount

    async def get_value(self) -> float:
        """Get the current value of the gauge.

        Returns:
            The current gauge value
        """
        return self._value


class Histogram:
    """Histogram metric implementation."""

    def __init__(
        self,
        name: str,
        description: str,
        tags: dict[str, str] | None = None,
        buckets: list[float] | None = None,
    ) -> None:
        """Initialize the histogram.

        Args:
            name: The name of the histogram
            description: A description of what the histogram measures
            tags: Optional tags/labels for the histogram
            buckets: Optional bucket boundaries
        """
        self._values: list[float] = []
        self.name = name
        self.description = description
        self.tags = tags or {}
        self.buckets = buckets or [
            0.005,
            0.01,
            0.025,
            0.05,
            0.1,
            0.25,
            0.5,
            1.0,
            2.5,
            5.0,
            10.0,
        ]

    async def observe(self, value: float) -> None:
        """Add an observation to the histogram.

        Args:
            value: Value to observe
        """
        self._values.append(value)

    async def get_value(self) -> dict[str, float]:
        """Get histogram stats.

        Returns:
            A dictionary containing histogram statistics
        """
        if not self._values:
            return {
                "count": 0,
                "sum": 0.0,
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
            }

        values = sorted(self._values)
        count = len(values)
        total = sum(values)

        result = {
            "count": count,
            "sum": total,
            "min": values[0],
            "max": values[-1],
            "mean": total / count if count > 0 else 0.0,
        }

        # Add bucket counts
        for bucket in self.buckets:
            bucket_count = sum(1 for v in values if v <= bucket)
            result[f"le_{bucket}"] = bucket_count

        return result


class Timer:
    """Timer metric implementation."""

    def __init__(
        self, name: str, description: str, tags: dict[str, str] | None = None
    ) -> None:
        """Initialize the timer.

        Args:
            name: The name of the timer
            description: A description of what the timer measures
            tags: Optional tags/labels for the timer
        """
        self._durations: list[float] = []
        self._lock = asyncio.Lock()
        self.name = name
        self.description = description
        self.tags = tags or {}

    async def time(self) -> TimerContextProtocol:
        """Start timing an operation.

        Returns:
            A context manager for timing operations
        """

        class Context(TimerContextProtocol):
            def __init__(self, timer: "Timer") -> None:
                self.timer = timer
                self.start_time = 0.0

            async def __aenter__(self) -> "Context":
                self.start_time = asyncio.get_event_loop().time()
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
                duration = asyncio.get_event_loop().time() - self.start_time
                await self.timer.record(duration)

        return Context(self)

    async def record(self, duration: float) -> None:
        """Record a duration.

        Args:
            duration: Duration to record in seconds
        """
        async with self._lock:
            self._durations.append(duration)

    async def get_value(self) -> dict[str, float]:
        """Get timer statistics.

        Returns:
            A dictionary containing timer statistics
        """
        async with self._lock:
            if not self._durations:
                return {
                    "min": 0.0,
                    "max": 0.0,
                    "mean": 0.0,
                    "count": 0,
                }

            durations = self._durations
            return {
                "min": min(durations),
                "max": max(durations),
                "mean": sum(durations) / len(durations),
                "count": len(durations),
            }
