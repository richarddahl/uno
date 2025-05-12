# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
PostgreSQL unit of work implementation.
"""

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, AsyncTransaction

from uno.uow.protocols import UnitOfWork
from uno.persistence.event_sourcing.protocols import EventStoreProtocol
from uno.uow.errors import UnitOfWorkCommitError, UnitOfWorkRollbackError
from uno.logging.logger import LoggerProtocol


class PostgresUnitOfWork(UnitOfWork):
    """
    PostgreSQL implementation of the Unit of Work pattern.

    This implementation provides real transactional guarantees using
    PostgreSQL's transaction support.
    """

    def __init__(
        self,
        event_store: EventStoreProtocol,
        session: AsyncSession,
        transaction: AsyncTransaction,
        logger_factory: Callable[..., LoggerProtocol] | None = None,
    ):
        """
        Initialize the PostgreSQL unit of work.

        Args:
            event_store: The event store to use
            session: The database session
            transaction: The database transaction
            logger_factory: Optional factory for creating loggers
        """
        self.event_store = event_store
        self.session = session
        self.transaction = transaction

        # Use provided logger factory or create a default logger
        if logger_factory:
            self.logger = logger_factory("uow_postgres")
        else:
            self.logger: LoggerProtocol | None = None  # Inject via DI or set externally

    async def commit(self) -> None:
        """
        Commit the current unit of work.

        Raises:
            UnitOfWorkCommitError: If the commit fails.
        """
        try:
            await self.transaction.commit()
            self.logger.structured_log(
                "DEBUG", "PostgreSQL unit of work committed", name="uno.uow.postgres"
            )
        except Exception as exc:
            self.logger.structured_log(
                "ERROR",
                f"Failed to commit PostgreSQL unit of work: {exc}",
                name="uno.uow.postgres",
                error=exc,
            )
            raise UnitOfWorkCommitError(f"Commit failed: {exc}")

    async def rollback(self) -> None:
        """
        Rollback the current unit of work.

        Raises:
            UnitOfWorkRollbackError: If the rollback fails.
        """
        try:
            await self.transaction.rollback()
            self.logger.structured_log(
                "DEBUG", "PostgreSQL unit of work rolled back", name="uno.uow.postgres"
            )
        except Exception as exc:
            self.logger.structured_log(
                "ERROR",
                f"Failed to rollback PostgreSQL unit of work: {exc}",
                name="uno.uow.postgres",
                error=exc,
            )
            raise UnitOfWorkRollbackError(f"Rollback failed: {exc}")

    @classmethod
    @asynccontextmanager
    async def begin(
        cls,
        event_store: EventStoreProtocol,
        session_factory: Callable[..., AsyncSession],
        logger_factory: Callable[..., LoggerProtocol] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator["PostgresUnitOfWork", None]:
        """
        Begin a new PostgreSQL unit of work.

        Args:
            event_store: The event store to use
            session_factory: Factory function for creating database sessions
            logger_factory: Optional factory for creating loggers
            **kwargs: Additional arguments to pass to the session factory

        Yields:
            A new PostgresUnitOfWork instance
        """
        async with session_factory() as session:
            async with session.begin() as transaction:
                uow = cls(event_store, session, transaction, logger_factory)

                try:
                    yield uow
                    # Transaction is automatically committed by the session.begin() context
                except Exception as e:
                    if logger_factory:
                        logger = logger_factory("uow_postgres")
                    else:
                        logger: LoggerProtocol | None = None  # Inject via DI or set externally

                    logger.structured_log(
                        "ERROR",
                        f"Error in PostgreSQL unit of work: {e}",
                        name="uno.uow.postgres",
                        error=e,
                    )
                    # Transaction is automatically rolled back on exception
                    raise
