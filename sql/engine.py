# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Centralized, DI-enabled engine and connection helpers for Uno SQL infrastructure.
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncConnection
from contextlib import contextmanager, asynccontextmanager

# Import ConnectionConfig only for type hints (avoid circular imports)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uno.persistence.sql.interfaces import ConnectionConfigProtocol


class SyncEngineFactory:
    """
    Dependency-injected factory for SQLAlchemy Engine objects (sync).
    """

    def __init__(self, config: "ConnectionConfigProtocol"):
        # DI: injected, type-hinted with Protocol for extensibility
        self.config = config
        self._engine: Engine | None = None

    def get_engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(
                self.config.get_uri(),
                pool_size=self.config.pool_size or 5,
                max_overflow=self.config.max_overflow or 0,
                pool_timeout=self.config.pool_timeout or 30,
                pool_recycle=self.config.pool_recycle or 90,
                connect_args=self.config.connect_args or {},
            )
        return self._engine


@contextmanager
def sync_connection(factory: SyncEngineFactory, *, isolation_level: str = "AUTOCOMMIT"):
    """
    Context manager for acquiring and releasing a sync SQLAlchemy connection.
    """
    engine = factory.get_engine()
    conn = engine.connect()
    conn = conn.execution_options(isolation_level=isolation_level)
    try:
        yield conn
    finally:
        conn.close()


class AsyncEngineFactory:
    """
    Dependency-injected factory for SQLAlchemy AsyncEngine objects (async).
    """

    def __init__(self, config: "ConnectionConfigProtocol"):
        # DI: injected, type-hinted with Protocol for extensibility
        self.config = config
        self._engine: AsyncEngine | None = None

    def get_engine(self) -> AsyncEngine:
        if self._engine is None:
            self._engine = create_async_engine(
                self.config.get_uri(),
                pool_size=self.config.pool_size or 5,
                max_overflow=self.config.max_overflow or 0,
                pool_timeout=self.config.pool_timeout or 30,
                pool_recycle=self.config.pool_recycle or 90,
                connect_args=self.config.connect_args or {},
            )
        return self._engine


@asynccontextmanager
async def async_connection(
    factory: AsyncEngineFactory, *, isolation_level: str = "AUTOCOMMIT"
):
    """
    Async context manager for acquiring and releasing an async SQLAlchemy connection.
    """
    engine = factory.get_engine()
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level=isolation_level)
        yield conn
