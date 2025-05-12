from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..protocols import MetricProtocol


class InMemoryMetricStore:
    """In-memory store for metrics."""

    def __init__(self) -> None:
        """Initialize the in-memory store."""
        self._metrics: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def store(self, metrics: Dict[str, Any]) -> None:
        """Store metrics in memory.

        Args:
            metrics: Dictionary of metric names to their values
        """
        async with self._lock:
            for name, value in metrics.items():
                self._metrics[name] = value

    async def retrieve(self) -> Dict[str, Any]:
        """Retrieve all stored metrics.

        Returns:
            Dictionary of metric names to their values
        """
        async with self._lock:
            return self._metrics.copy()

    async def clear(self) -> None:
        """Clear all stored metrics."""
        async with self._lock:
            self._metrics.clear()

    async def get(self, name: str) -> Optional[Any]:
        """Get a specific metric by name.

        Args:
            name: Name of the metric to get

        Returns:
            The metric value if found, None otherwise
        """
        async with self._lock:
            return self._metrics.get(name)

    async def get_by_prefix(self, prefix: str) -> Dict[str, Any]:
        """Get all metrics with a specific prefix.

        Args:
            prefix: Prefix to filter metrics by

        Returns:
            Dictionary of metric names to their values
        """
        async with self._lock:
            return {
                name: value
                for name, value in self._metrics.items()
                if name.startswith(prefix)
            }
