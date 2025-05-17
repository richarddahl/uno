from __future__ import annotations

import asyncio
import contextlib
from typing import Any


class AsyncMetricCollector:
    """Async-compatible metric collector."""

    def __init__(self, interval: float = 1.0) -> None:
        """Initialize the async collector.

        Args:
            interval: Collection interval in seconds (default: 1.0)
        """
        self._interval = interval
        self._task: asyncio.Task | None = None
        self._running = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the async collection task."""
        async with self._lock:
            if not self._running:
                self._running = True
                self._task = asyncio.create_task(self._collect())

    async def stop(self) -> None:
        """Stop the async collection task."""
        async with self._lock:
            if self._running and self._task:
                self._running = False
                self._task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._task

    async def _collect(self) -> None:
        """Background collection task."""
        while self._running:
            try:
                # Collect metrics
                metrics = await self._collect_metrics()

                # Process metrics
                await self._process_metrics(metrics)

                # Sleep until next collection
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue collection
                self._log_error(f"Error collecting metrics: {e}")
                await asyncio.sleep(self._interval)

    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current metric values."""
        # This should be implemented by subclasses
        raise NotImplementedError("_collect_metrics must be implemented by subclasses")

    async def _process_metrics(self, metrics: Dict[str, Any]) -> None:
        """Process collected metrics."""
        # This should be implemented by subclasses
        raise NotImplementedError("_process_metrics must be implemented by subclasses")

    def _log_error(self, message: str) -> None:
        """Log an error message."""
        # This should be implemented by subclasses
        pass


class AsyncMetricReporter(AsyncMetricCollector):
    """Async metric reporter that sends metrics to multiple backends."""

    def __init__(
        self,
        interval: float = 1.0,
        backends: Optional[list[Any]] = None,  # Replace with actual backend types
    ) -> None:
        """Initialize the async reporter.

        Args:
            interval: Collection interval in seconds (default: 1.0)
            backends: List of metric backends to report to
        """
        super().__init__(interval)
        self._backends = backends or []

    async def add_backend(
        self, backend: Any
    ) -> None:  # Replace with actual backend type
        """Add a metric backend.

        Args:
            backend: Metric backend to add
        """
        self._backends.append(backend)

    async def remove_backend(
        self, backend: Any
    ) -> None:  # Replace with actual backend type
        """Remove a metric backend.

        Args:
            backend: Metric backend to remove
        """
        if backend in self._backends:
            self._backends.remove(backend)

    async def _process_metrics(self, metrics: Dict[str, Any]) -> None:
        """Send metrics to all registered backends."""
        for backend in self._backends:
            try:
                await backend.report(metrics)
            except Exception as e:
                self._log_error(f"Error reporting to backend: {e}")

    def _log_error(self, message: str) -> None:
        """Log an error message."""
        # Implementation depends on logging system
        pass
