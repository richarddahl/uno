"""
Protocol definitions for metrics backends.

This module provides protocols that define the interfaces for metrics
storage, reporting, and exporting.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from collections.abc import AsyncIterable, AsyncIterator
from datetime import datetime


@runtime_checkable
class BackendProtocol(Protocol):
    """Protocol for metric storage backends."""

    async def store(self, metric: Any) -> None:
        """
        Store a metric.

        Args:
            metric: The metric to store
        """
        ...

    async def retrieve(self, query: Any) -> AsyncIterable[Any]:
        """
        Retrieve metrics matching a query.

        Args:
            query: The query to match metrics against

        Returns:
            AsyncIterable of matching metrics
        """
        ...

    async def delete(self, query: Any) -> None:
        """
        Delete metrics matching a query.

        Args:
            query: The query to match metrics against
        """
        ...


@runtime_checkable
class ReporterProtocol(Protocol):
    """Protocol for metric reporters."""

    async def report(self, metrics: list[Any]) -> None:
        """
        Report a batch of metrics.

        Args:
            metrics: List of metrics to report
        """
        ...

    async def flush(self) -> None:
        """
        Flush any pending metrics.
        """
        ...


@runtime_checkable
class ExporterProtocol(Protocol):
    """Protocol for metric exporters."""

    async def export(self, metrics: list[Any]) -> None:
        """
        Export a batch of metrics.

        Args:
            metrics: List of metrics to export
        """
        ...

    async def format(self, metrics: list[Any]) -> str:
        """
        Format metrics for export.

        Args:
            metrics: List of metrics to format

        Returns:
            Formatted string representation of metrics
        """
        ...


@runtime_checkable
class QueryProtocol(Protocol):
    """Protocol for metric queries."""

    def filter_by_name(self, name: str) -> QueryProtocol:
        """
        Filter metrics by name.

        Args:
            name: The metric name to filter by

        Returns:
            New query with name filter applied
        """
        ...

    def filter_by_tags(self, tags: dict[str, Any]) -> QueryProtocol:
        """
        Filter metrics by tags.

        Args:
            tags: Dictionary of tag key-value pairs to filter by

        Returns:
            New query with tag filters applied
        """
        ...

    def filter_by_time(self, start: datetime, end: datetime) -> QueryProtocol:
        """
        Filter metrics by time range.

        Args:
            start: Start time for the range
            end: End time for the range

        Returns:
            New query with time range filter applied
        """
        ...

    async def execute(self) -> AsyncIterator[Any]:
        """
        Execute the query and return results.

        Returns:
            AsyncIterator of matching metrics
        """
        ...


@runtime_checkable
class AggregatorProtocol(Protocol):
    """Protocol for metric aggregation."""

    def aggregate(self, metrics: list[Any]) -> Any:
        """
        Aggregate a list of metrics.

        Args:
            metrics: List of metrics to aggregate

        Returns:
            Aggregated result
        """
        ...

    def aggregate_by_tags(self, metrics: list[Any], tags: list[str]) -> dict:
        """
        Aggregate metrics by specified tags.

        Args:
            metrics: List of metrics to aggregate
            tags: List of tag keys to group by

        Returns:
            Dictionary of aggregated results grouped by tags
        """
        ...

    def aggregate_by_time(self, metrics: list[Any], interval: str) -> dict:
        """
        Aggregate metrics by time interval.

        Args:
            metrics: List of metrics to aggregate
            interval: Time interval to group by (e.g., "1h", "1d")

        Returns:
            Dictionary of aggregated results grouped by time
        """
        ...
