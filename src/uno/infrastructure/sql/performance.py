"""
SQL performance monitoring.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from sqlalchemy import text
from uno.core.errors.result import Result, Success, Failure
from uno.infrastructure.sql.config import SQLConfig
from uno.infrastructure.logging.logger import LoggerService


class StatementMetrics(BaseModel):
    """SQL statement performance metrics."""
    
    statement: str
    parameters: dict[str, Any]
    execution_time_ms: float
    rows_affected: int
    timestamp: datetime
    user_id: Optional[str]
    error: Optional[str]


class PerformanceMetrics(BaseModel):
    """Overall performance metrics."""
    
    total_queries: int
    total_execution_time_ms: float
    avg_execution_time_ms: float
    slow_queries: int
    errors: int
    start_time: datetime
    end_time: datetime


class SQLPerformanceMonitor:
    """Monitors SQL performance and collects metrics."""

    def __init__(
        self,
        config: SQLConfig,
        logger: LoggerService,
        metrics_window: timedelta = timedelta(minutes=5)
    ) -> None:
        """Initialize performance monitor.
        
        Args:
            config: SQL configuration
            logger: Logger service
            metrics_window: Time window for metrics collection
        """
        self._config = config
        self._logger = logger
        self._metrics_window = metrics_window
        self._statement_metrics: list[StatementMetrics] = []
        self._start_time = datetime.now()

    def record_statement(
        self,
        statement: str,
        parameters: dict[str, Any],
        execution_time_ms: float,
        rows_affected: int,
        user_id: Optional[str] = None,
        error: Optional[str] = None
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
            timestamp=datetime.now(),
            user_id=user_id,
            error=error
        )
        self._statement_metrics.append(metrics)
        
        # Log slow queries
        if execution_time_ms > self._config.DB_SLOW_QUERY_THRESHOLD * 1000:
            self._logger.structured_log(
                "WARNING",
                f"Slow query detected: {execution_time_ms}ms",
                name="uno.sql.performance",
                statement=statement,
                execution_time_ms=execution_time_ms,
                threshold_ms=self._config.DB_SLOW_QUERY_THRESHOLD * 1000
            )
        
        # Log errors
        if error:
            self._logger.structured_log(
                "ERROR",
                f"Query error: {error}",
                name="uno.sql.performance",
                statement=statement,
                error=error
            )

    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics.
        
        Returns:
            Current performance metrics
        """
        now = datetime.now()
        window_start = now - self._metrics_window
        
        # Filter metrics within window
        window_metrics = [
            m for m in self._statement_metrics
            if m.timestamp >= window_start
        ]
        
        if not window_metrics:
            return PerformanceMetrics(
                total_queries=0,
                total_execution_time_ms=0.0,
                avg_execution_time_ms=0.0,
                slow_queries=0,
                errors=0,
                start_time=window_start,
                end_time=now
            )
        
        total_time = sum(m.execution_time_ms for m in window_metrics)
        slow_queries = sum(
            1 for m in window_metrics
            if m.execution_time_ms > self._config.DB_SLOW_QUERY_THRESHOLD * 1000
        )
        errors = sum(1 for m in window_metrics if m.error)
        
        return PerformanceMetrics(
            total_queries=len(window_metrics),
            total_execution_time_ms=total_time,
            avg_execution_time_ms=total_time / len(window_metrics),
            slow_queries=slow_queries,
            errors=errors,
            start_time=window_start,
            end_time=now
        )

    def get_slow_queries(self) -> list[StatementMetrics]:
        """Get list of slow queries.
        
        Returns:
            List of slow query metrics
        """
        return [
            m for m in self._statement_metrics
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
        self._start_time = datetime.now()

    @property
    def statement_metrics(self) -> list[StatementMetrics]:
        """Get all statement metrics.
        
        Returns:
            List of all statement metrics
        """
        return self._statement_metrics 