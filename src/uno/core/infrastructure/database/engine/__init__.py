# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import logging
from logging import Logger
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine

from uno.core.logging.logger import get_logger
from uno.infrastructure.database.engine.asynceng import AsyncEngineFactory

# Import engine-specific modules
from uno.infrastructure.database.engine.sync import SyncEngineFactory, sync_connection

# Use string type annotations for session imports to break circular dependencies
__all__ = [
    "AsyncEngine",
    "AsyncEngineFactory",
    "DatabaseFactory",
    "SyncEngineFactory",
    "sync_connection",
]


class DatabaseFactory:
    """
    Unified factory for all database connection types.

    Provides central access to sync and async database functionality.
    """

    def __init__(self, logger: Logger | None = None):
        """Initialize all component factories."""
        self.logger = logger or get_logger(__name__)

        # Initialize specialized factories
        self.sync_engine_factory = SyncEngineFactory(logger=self.logger)
        self.async_engine_factory = AsyncEngineFactory(logger=self.logger)

        # Dynamically import AsyncSessionFactory to avoid circular imports
        from uno.infrastructure.database.session import AsyncSessionFactory

        self.async_session_factory = AsyncSessionFactory(
            engine_factory=self.async_engine_factory, logger=self.logger
        )

    # Factory accessors
    def get_sync_engine_factory(self) -> SyncEngineFactory:
        """Get the synchronous engine factory."""
        return self.sync_engine_factory

    def get_async_engine_factory(self) -> AsyncEngineFactory:
        """Get the asynchronous engine factory."""
        return self.async_engine_factory

    def get_async_session_factory(self):
        """Get the asynchronous session factory."""
        return self.async_session_factory
