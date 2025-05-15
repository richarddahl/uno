"""
SQL performance monitoring.
"""

from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field
from uno.persistance.sql.interfaces import PerformanceMonitorProtocol


class PerformanceMetrics(BaseModel):
    """SQL performance metrics."""

    total_executions: int = Field(
        default=0, description="Total number of statement executions"
    )
    total_duration: float = Field(
        default=0.0, description="Total execution duration in seconds"
    )
    avg_duration: float = Field(
        default=0.0, description="Average execution duration in seconds"
    )
    min_duration: float = Field(
        default=float("inf"), description="Minimum execution duration in seconds"
    )
    max_duration: float = Field(
        default=0.0, description="Maximum execution duration in seconds"
    )
    error_count: int = Field(default=0, description="Number of execution errors")


class StatementMetrics(BaseModel):
    """SQL statement performance metrics."""

    statement: str = Field(
        ..., description="SQL statement", json_schema_extra={"env": "STATEMENT"}
    )
    executions: int = Field(
        default=0,
        description="Number of executions",
        json_schema_extra={"env": "EXECUTIONS"},
    )
    total_duration: float = Field(
        default=0.0,
        description="Total execution duration in seconds",
        json_schema_extra={"env": "TOTAL_DURATION"},
    )
    avg_duration: float = Field(
        default=0.0,
        description="Average execution duration in seconds",
        json_schema_extra={"env": "AVG_DURATION"},
    )
    last_execution: datetime = Field(
        ...,
        description="Last execution timestamp",
        json_schema_extra={"env": "LAST_EXECUTION"},
    )
    error_count: int = Field(
        default=0,
        description="Number of execution errors",
        json_schema_extra={"env": "ERROR_COUNT"},
    )


class PerformanceMonitor:
    """Monitors SQL performance metrics."""

    def __init__(self) -> None:
        """Initialize performance monitor."""
        self._metrics = PerformanceMetrics()
        self._statement_metrics: dict[str, StatementMetrics] = {}

    def record_execution_time(self, statement: Any, duration: float) -> None:
        """Record statement execution time.

        Args:
            statement: SQL statement
            duration: Execution duration in seconds
        """
        # Update overall metrics
        self._metrics.total_executions += 1
        self._metrics.total_duration += duration
        self._metrics.avg_duration = (
            self._metrics.total_duration / self._metrics.total_executions
        )
        self._metrics.min_duration = min(self._metrics.min_duration, duration)
        self._metrics.max_duration = max(self._metrics.max_duration, duration)

        # Update statement-specific metrics
        statement_str = str(statement)
        if statement_str not in self._statement_metrics:
            self._statement_metrics[statement_str] = StatementMetrics(
                statement=statement_str, last_execution=datetime.now()
            )

        metrics = self._statement_metrics[statement_str]
        metrics.executions += 1
        metrics.total_duration += duration
        metrics.avg_duration = metrics.total_duration / metrics.executions
        metrics.last_execution = datetime.now()

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics.

        Returns:
            Dictionary containing performance metrics
        """
        return {
            "overall": self._metrics.model_dump(),
            "statements": {
                stmt: metrics.model_dump()
                for stmt, metrics in self._statement_metrics.items()
            },
        }

    def record_error(self, statement: Any) -> None:
        """Record statement execution error.

        Args:
            statement: SQL statement
        """
        self._metrics.error_count += 1
        statement_str = str(statement)
        if statement_str in self._statement_metrics:
            self._statement_metrics[statement_str].error_count += 1
