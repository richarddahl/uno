"""
Logging reporter implementation for Uno metrics.

This module provides a logging-based reporter for Uno metrics,
allowing metrics to be logged in various formats.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
import asyncio

import structlog
from structlog.types import EventDict

from uno.metrics.backends.protocols import ReporterProtocol
from uno.metrics.types import Counter, Gauge, Histogram, Timer


class LogFormat(Enum):
    """Available log formats."""

    JSON = "json"
    TEXT = "text"
    STRUCTURED = "structured"


@dataclass
class LogConfig:
    """Configuration for the logging reporter."""

    format: LogFormat = LogFormat.JSON
    level: str = "info"
    prefix: str = "uno.metrics"
    timestamp_format: str = "%Y-%m-%d %H:%M:%S"


class LoggingReporter(ReporterProtocol):
    """Logging reporter implementation."""

    def __init__(self, config: Optional[LogConfig] = None) -> None:
        """
        Initialize the logging reporter.

        Args:
            config: Optional configuration for the reporter
        """
        self._config = config or LogConfig()
        self._logger = structlog.get_logger(self._config.prefix)

    async def report(self, metrics: List[Any]) -> None:
        """
        Report metrics to the configured logger.

        Args:
            metrics: List of metrics to report
        """
        for metric in metrics:
            await self._report_metric(metric)

    async def _report_metric(self, metric: Any) -> None:
        """
        Report a single metric.

        Args:
            metric: Metric to report
        """
        event_dict = await self._format_metric(metric)

        if self._config.format == LogFormat.JSON:
            self._logger.msg(
                self._config.prefix,
                **event_dict,
                _asdict=True,
            )
        elif self._config.format == LogFormat.TEXT:
            message = await self._format_text(event_dict)
            self._logger.msg(message)
        else:  # STRUCTURED
            self._logger.msg(
                self._config.prefix,
                **event_dict,
            )

    async def _format_metric(self, metric: Any) -> dict[str, Any]:
        """
        Format a metric as a dictionary.

        Args:
            metric: The metric to format

        Returns:
            The formatted metric
        """
        # Handle both sync and async get_value methods
        value = metric.get_value()
        if asyncio.iscoroutine(value):
            value = await value
        return {
            "name": metric.name,
            "description": metric.description,
            "value": value,
            "tags": metric.tags,
        }


    async def _format_text(self, event_dict: EventDict) -> str:
        """
        Format a metric as text.

        Args:
            event_dict: Dictionary of metric data

        Returns:
            Text representation of the metric
        """
        parts = []
        parts.append(f"{event_dict['name']}={event_dict['value']}")

        if event_dict.get("tags"):
            tags = ", ".join(f"{k}={v}" for k, v in event_dict["tags"].items())
            parts.append(f"tags={{{tags}}}")

        if event_dict.get("description"):
            parts.append(f"description={event_dict['description']}")

        return " ".join(parts)

    async def flush(self) -> None:
        """Flush any pending logs."""
        # structlog handles flushing automatically
        pass

    def set_level(self, level: str) -> None:
        """
        Set the logging level.

        Args:
            level: The logging level to set
        """
        self._config.level = level

    def set_format(self, format: LogFormat) -> None:
        """
        Set the log format.

        Args:
            format: The log format to use
        """
        self._config.format = format

    def set_prefix(self, prefix: str) -> None:
        """
        Set the log prefix.

        Args:
            prefix: The log prefix to use
        """
        self._config.prefix = prefix

    def set_timestamp_format(self, format: str) -> None:
        """
        Set the timestamp format.

        Args:
            format: The timestamp format to use
        """
        self._config.timestamp_format = format
