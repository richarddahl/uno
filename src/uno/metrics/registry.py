"""
Metric registry manages all metrics and provides a consistent interface for metric collection.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .types import Metric


class MetricRegistry:
    """Central registry for all metrics."""

    def __init__(self) -> None:
        """Initialize the metric registry."""
        self._metrics: dict[str, Metric] = {}
        self._lock = asyncio.Lock()

    def register(self, name: str, metric: Metric) -> None:
        """Register a new metric.

        Args:
            name: Unique name for the metric
            metric: Metric instance to register

        Raises:
            ValueError: If a metric with the same name already exists
        """
        if name in self._metrics:
            raise ValueError(f"Metric '{name}' already registered")

        self._metrics[name] = metric

    def get(self, name: str) -> Metric | None:
        """Get a registered metric by name.

        Args:
            name: Name of the metric to get

        Returns:
            The metric instance if found, None otherwise
        """
        return self._metrics.get(name)

    def remove(self, name: str) -> None:
        """Remove a registered metric.

        Args:
            name: Name of the metric to remove
        """
        if name in self._metrics:
            del self._metrics[name]

    def clear(self) -> None:
        """Clear all registered metrics."""
        self._metrics.clear()

    def snapshot(self) -> dict[str, Any]:
        """Get a snapshot of all current metric values.

        Returns:
            Dictionary of metric names to their current values
        """
        return {name: metric.get_value() for name, metric in self._metrics.items()}

    async def async_snapshot(self) -> dict[str, Any]:
        """Get an async snapshot of all current metric values.

        Returns:
            Dictionary of metric names to their current values
        """
        async with self._lock:
            return {name: metric.get_value() for name, metric in self._metrics.items()}

    def __contains__(self, name: str) -> bool:
        """Check if a metric is registered."""
        return name in self._metrics
