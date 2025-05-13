"""
Protocols for the metrics system.

This module defines the interfaces that metrics implementations must follow.
"""

from __future__ import annotations

from typing import Protocol, Self, runtime_checkable


@runtime_checkable
class TimerContextProtocol(Protocol):
    """Protocol defining a timer context manager for measuring code execution time."""

    async def __aenter__(self) -> Self:
        """Enter the timer context, starting the timer."""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the timer context, stopping the timer and recording the duration."""
        ...


@runtime_checkable
class CounterProtocol(Protocol):
    """Protocol defining a counter metric implementation."""

    async def increment(self, amount: float = 1.0) -> None:
        """
        Increment the counter by the given amount.

        Args:
            amount: Amount to increment by (default: 1.0)
        """
        ...

    async def decrement(self, amount: float = 1.0) -> None:
        """
        Decrement the counter by the given amount.

        Args:
            amount: Amount to decrement by (default: 1.0)
        """
        ...

    async def set(self, value: float) -> None:
        """
        Set the counter to the given value.

        Args:
            value: Value to set the counter to
        """
        ...

    async def get(self) -> float:
        """
        Get the current value of the counter.

        Returns:
            Current value of the counter
        """
        ...


@runtime_checkable
class GaugeProtocol(Protocol):
    """Protocol defining a gauge metric implementation."""

    async def set(self, value: float) -> None:
        """
        Set the gauge to the given value.

        Args:
            value: Value to set the gauge to
        """
        ...

    async def get(self) -> float:
        """
        Get the current value of the gauge.

        Returns:
            Current value of the gauge
        """
        ...

    async def increment(self, amount: float = 1.0) -> None:
        """
        Increment the gauge by the given amount.

        Args:
            amount: Amount to increment by (default: 1.0)
        """
        ...

    async def decrement(self, amount: float = 1.0) -> None:
        """
        Decrement the gauge by the given amount.

        Args:
            amount: Amount to decrement by (default: 1.0)
        """
        ...


@runtime_checkable
class HistogramProtocol(Protocol):
    """Protocol defining a histogram metric implementation."""

    async def observe(self, value: float) -> None:
        """
        Observe a value.

        Args:
            value: Value to observe
        """
        ...

    async def get_buckets(self) -> dict[float, int]:
        """
        Get the current buckets.

        Returns:
            Dictionary mapping bucket upper bounds to counts
        """
        ...


@runtime_checkable
class TimerProtocol(Protocol):
    """Protocol defining a timer metric implementation."""

    async def time(self) -> TimerContextProtocol:
        """
        Create a timer context for measuring code execution time.

        Returns:
            A context manager that measures execution time
        """
        ...

    async def observe(self, seconds: float) -> None:
        """
        Observe a duration in seconds.

        Args:
            seconds: Duration in seconds
        """
        ...


@runtime_checkable
class MetricProtocol(Protocol):
    """Base protocol for all metrics."""

    async def time(self) -> TimerContextProtocol:
        """
        Create a timer context for measuring code execution time.

        Returns:
            A context manager that measures execution time
        """
        ...
