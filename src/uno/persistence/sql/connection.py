"""
SQL connection management.
"""

from __future__ import annotations
from typing import Any, Optional
import asyncio
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from uno.errors import UnoError
from uno.persistence.sql.errors import SQLErrorCode
from uno.persistence.sql.interfaces import ConnectionManagerProtocol
from uno.persistence.sql.config import SQLConfig
from uno.logging.protocols import LoggerProtocol


class ConnectionHealth(BaseModel):
    """Connection health status."""

    is_healthy: bool
    last_check: datetime
    error_count: int
    latency_ms: float
    pool_size: int
    available_connections: int


class ConnectionManager:
    """Manages database connections with connection pooling."""

    def __init__(
        self,
        config: SQLConfig,
        logger: LoggerProtocol,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        health_check_interval: float = 30.0,
    ) -> None:
        """Initialize connection manager.

        Args:
            config: SQL configuration
            logger: Logger service
            max_retries: Maximum number of connection retries
            retry_delay: Delay between retries in seconds
            health_check_interval: Health check interval in seconds
        """
        self._config = config
        self._logger = logger
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._health_check_interval = health_check_interval
        self._engine: AsyncEngine | None = None
        self._session_factory: sessionmaker[AsyncSession] = None
        self._health_status = ConnectionHealth(
            is_healthy=False,
            last_check=datetime.now(),
            error_count=0,
            latency_ms=0.0,
            pool_size=0,
            available_connections=0,
        )
        self._health_check_task: asyncio.Task | None = None
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Initialize connection pool with retry logic."""
        for attempt in range(self._max_retries):
            try:
                self._engine = create_async_engine(
                    self._config.get_connection_url(),
                    **self._config.get_engine_options(),
                )
                self._session_factory = sessionmaker(
                    self._engine, class_=AsyncSession, expire_on_commit=False
                )
                self._start_health_check()
                return
            except Exception as e:
                self._logger.structured_log(
                    "ERROR",
                    f"Failed to initialize connection pool (attempt {attempt + 1}/{self._max_retries}): {str(e)}",
                    name="uno.sql.connection",
                    error=e,
                    attempt=attempt + 1,
                )
                if attempt < self._max_retries - 1:
                    asyncio.sleep(self._retry_delay)
                else:
                    raise ConnectionError(
                        f"Failed to initialize connection pool after {self._max_retries} attempts: {str(e)}"
                    )

    def _start_health_check(self) -> None:
        """Start periodic health check task."""

        async def health_check_loop() -> None:
            while True:
                try:
                    await self._check_health()
                    await asyncio.sleep(self._health_check_interval)
                except Exception as e:
                    self._logger.structured_log(
                        "ERROR",
                        f"Health check failed: {str(e)}",
                        name="uno.sql.connection",
                        error=e,
                    )
                    await asyncio.sleep(self._retry_delay)

        self._health_check_task = asyncio.create_task(health_check_loop())

    async def _check_health(self) -> None:
        """Check connection health."""
        start_time = datetime.now()
        try:
            async with self._engine.connect() as conn:
                # Execute a simple query to check connection
                await conn.execute(text("SELECT 1"))

                # Get pool status
                pool = self._engine.pool
                self._health_status = ConnectionHealth(
                    is_healthy=True,
                    last_check=datetime.now(),
                    error_count=0,
                    latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                    pool_size=pool.size(),
                    available_connections=pool.checkedin(),
                )

                self._logger.structured_log(
                    "DEBUG",
                    "Connection health check passed",
                    name="uno.sql.connection",
                    latency_ms=self._health_status.latency_ms,
                    pool_size=self._health_status.pool_size,
                    available_connections=self._health_status.available_connections,
                )
        except Exception as e:
            self._health_status.error_count += 1
            self._health_status.is_healthy = False
            self._logger.structured_log(
                "ERROR",
                f"Connection health check failed: {str(e)}",
                name="uno.sql.connection",
                error=e,
                error_count=self._health_status.error_count,
            )
            raise

    async def get_connection(self) -> AsyncSession:
        """Get a database connection with retry logic.

        Returns:
            AsyncSession: The database session

        Raises:
            UnoError: if connection cannot be obtained
        """
        for attempt in range(self._max_retries):
            try:
                if not self._session_factory:
                    raise UnoError(
                        message="Connection pool not initialized",
                        error_code=SQLErrorCode.SQL_CONNECTION_ERROR,
                        reason="Connection pool not initialized"
                    )
                if not self._health_status.is_healthy:
                    raise UnoError(
                        message="Connection pool is unhealthy",
                        error_code=SQLErrorCode.SQL_CONNECTION_ERROR,
                        reason="Connection pool is unhealthy"
                    )
                session = self._session_factory()
                return session
            except Exception as e:
                self._logger.structured_log(
                    "ERROR",
                    f"Failed to get connection (attempt {attempt + 1}/{self._max_retries}): {str(e)}",
                    name="uno.sql.connection",
                    error=e,
                    attempt=attempt + 1,
                )
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay)
                else:
                    raise UnoError(
                        message=f"Failed to get connection after {self._max_retries} attempts",
                        error_code=SQLErrorCode.SQL_CONNECTION_ERROR,
                        reason=str(e)
                    )
    async def release_connection(self, session: AsyncSession) -> None:
        """Release a database connection.

        Args:
            session: Database session to release

        Raises:
            UnoError: if connection cannot be released
        """
        try:
            await session.close()
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to release connection: {str(e)}",
                name="uno.sql.connection",
                error=e,
            )
            raise UnoError(
                message="Failed to release connection",
                error_code=SQLErrorCode.SQL_CONNECTION_ERROR,
                reason=str(e)
            )

    async def close(self) -> None:
        """Close all connections in the pool.

        Raises:
            UnoError: if connection pool cannot be closed
        """
        try:
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            if self._engine:
                await self._engine.dispose()
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to close connection pool: {str(e)}",
                name="uno.sql.connection",
                error=e,
            )
            raise UnoError(
                message="Failed to close connection pool",
                error_code=SQLErrorCode.SQL_CONNECTION_ERROR,
                reason=str(e)
            )

    @property
    def engine(self) -> AsyncEngine:
        """Get the SQLAlchemy engine.

        Returns:
            AsyncEngine: The SQLAlchemy engine

        Raises:
            UnoError: if engine is not initialized
        """
        if not self._engine:
            raise UnoError(
                message="Engine not initialized",
                error_code=SQLErrorCode.SQL_CONNECTION_ERROR,
                reason="Engine not initialized"
            )
        return self._engine

    @property
    def health_status(self) -> ConnectionHealth:
        """Get current connection health status.

        Returns:
            Current connection health status
        """
        return self._health_status
