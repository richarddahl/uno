"""
SQL performance monitoring.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from uno.logging import LogLevel
from uno.logging.protocols import LoggerProtocol
from uno.persistence.sql.config import SQLConfig

if TYPE_CHECKING:
    from uno.logging.protocols import LoggerProtocol
    from uno.persistence.sql.config import SQLConfig


class StatementMetrics(BaseModel):
    """Metrics for a single SQL statement execution."""

    statement: str
    parameters: dict[str, Any]
    execution_time_ms: float
    rows_affected: int
    timestamp: datetime
    user_id: str | None = None
    error: str | None = None


class PerformanceMetrics(BaseModel):
    """Aggregated performance metrics for SQL operations."""

    slow_queries: list[StatementMetrics]
    errors: list[StatementMetrics]
    total_queries: int
    total_execution_time_ms: float
    average_execution_time_ms: float
    max_execution_time_ms: float
    min_execution_time_ms: float
    total_rows_affected: int
    average_rows_affected: float
    max_rows_affected: int
    min_rows_affected: int


class SQLPerformanceMonitor:
    """Monitors and records SQL performance metrics."""

    def __init__(
        self,
        config: SQLConfig,
        logger: LoggerProtocol,
        metrics_window: timedelta = timedelta(minutes=5),
    ) -> None:
        """Initialize the SQL performance monitor.

        Args:
            config: SQL configuration
            logger: Logger for performance metrics
            metrics_window: Window for aggregating metrics
        """
        self._config = config
        self._logger = logger
        self._metrics_window = metrics_window
        self._statement_metrics: list[StatementMetrics] = []
        self._start_time = datetime.now(tz=datetime.UTC)

    def record_statement(
        self,
        statement: str,
        parameters: dict[str, Any],
        execution_time_ms: float,
        rows_affected: int,
        user_id: str | None = None,
        error: str | None = None,
    ) -> None:
        """Record statement execution metrics.

        Args:
            statement: SQL statement
            parameters: Statement parameters
            execution_time_ms: Execution time in milliseconds
            rows_affected: Number of rows affected
            user_id: User ID executing statement
            error: Error message if any
        """
        metrics = StatementMetrics(
            statement=statement,
            parameters=parameters,
            execution_time_ms=execution_time_ms,
            rows_affected=rows_affected,
            timestamp=datetime.now(tz=datetime.UTC),
            user_id=user_id,
            error=error,
        )
        self._statement_metrics.append(metrics)

        # Log slow queries
        if execution_time_ms > self._config.DB_SLOW_QUERY_THRESHOLD * 1000:
            self._logger.structured_log(
                LogLevel.WARNING,
                f"Slow query detected: {execution_time_ms}ms",
                name="uno.sql.performance",
                statement=statement,
                execution_time_ms=execution_time_ms,
                threshold_ms=self._config.DB_SLOW_QUERY_THRESHOLD * 1000,
            )

        # Log errors
        if error:
            self._logger.structured_log(
                LogLevel.ERROR,
                f"Query error: {error}",
                name="uno.sql.performance",
                statement=statement,
                error=error,
            )

    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics.

        Returns:
            Current performance metrics
        """
        now = datetime.now(tz=datetime.UTC)
        window_start = now - self._metrics_window

        # Filter metrics within window
        window_metrics = [
            m for m in self._statement_metrics if m.timestamp >= window_start
        ]

        # Calculate metrics
        total_queries = len(window_metrics)
        total_execution_time_ms = sum(m.execution_time_ms for m in window_metrics)
        total_rows_affected = sum(m.rows_affected for m in window_metrics)

        # Calculate averages
        average_execution_time_ms = (
            total_execution_time_ms / total_queries if total_queries > 0 else 0
        )
        average_rows_affected = (
            total_rows_affected / total_queries if total_queries > 0 else 0
        )

        # Calculate min/max
        if window_metrics:
            max_execution_time_ms = max(m.execution_time_ms for m in window_metrics)
            min_execution_time_ms = min(m.execution_time_ms for m in window_metrics)
            max_rows_affected = max(m.rows_affected for m in window_metrics)
            min_rows_affected = min(m.rows_affected for m in window_metrics)
        else:
            max_execution_time_ms = 0
            min_execution_time_ms = 0
            max_rows_affected = 0
            min_rows_affected = 0

        # Find slow queries and errors
        slow_queries = [
            m
            for m in window_metrics
            if m.execution_time_ms > self._config.DB_SLOW_QUERY_THRESHOLD * 1000
        ]
        errors = [m for m in window_metrics if m.error]

        return PerformanceMetrics(
            slow_queries=slow_queries,
            errors=errors,
            total_queries=total_queries,
            total_execution_time_ms=total_execution_time_ms,
            average_execution_time_ms=average_execution_time_ms,
            max_execution_time_ms=max_execution_time_ms,
            min_execution_time_ms=min_execution_time_ms,
            total_rows_affected=total_rows_affected,
            average_rows_affected=average_rows_affected,
            max_rows_affected=max_rows_affected,
            min_rows_affected=min_rows_affected,
        )

    def get_slow_queries(self) -> list[StatementMetrics]:
        """Get list of slow queries.

        Returns:
            List of slow query metrics
        """
        return [
            m
            for m in self._statement_metrics
            if m.execution_time_ms > self._config.DB_SLOW_QUERY_THRESHOLD * 1000
        ]

    def get_error_queries(self) -> list[StatementMetrics]:
        """Get list of queries with errors.

        Returns:
            List of error query metrics
        """
        return [m for m in self._statement_metrics if m.error]

    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        self._statement_metrics.clear()
        self._start_time = datetime.now(tz=UTC)

    @property
    def statement_metrics(self) -> list[StatementMetrics]:
        """Get all recorded statement metrics."""
        return self._statement_metrics
