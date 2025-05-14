"""
SQL transaction management.
"""

from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from uno.persistence.sql.interfaces import TransactionManagerProtocol
from uno.persistence.sql.config import SQLConfig


class TransactionConfig(BaseModel):
    """SQL transaction configuration."""

    isolation_level: str = Field(
        default="READ COMMITTED", description="Transaction isolation level"
    )
    read_only: bool = Field(
        default=False, description="Whether transaction is read-only"
    )
    deferrable: bool = Field(
        default=False, description="Whether transaction is deferrable"
    )


class TransactionManager:
    """Manages database transactions."""

    def __init__(self, config: SQLConfig) -> None:
        """Initialize transaction manager.

        Args:
            config: SQL configuration
        """
        self._config = config
        self._current_transaction: AsyncSession | None = None

    async def begin_transaction(self, session: AsyncSession) -> None:
        """Begin a new transaction.

        Args:
            session: Database session

        Raises:
            ValueError: If in read-only mode.
            Exception: If transaction cannot be started.
        """
        if self._config.DB_READ_ONLY:
            raise ValueError("Cannot begin transaction in read-only mode")
        try:
            self._current_transaction = session
        except Exception as e:
            raise RuntimeError(f"Failed to begin transaction: {str(e)}") from e

    async def commit_transaction(self, session: AsyncSession) -> None:
        """Commit the current transaction.

        Args:
            session: Database session

        Raises:
            ValueError: If no active transaction.
            Exception: If commit fails.
        """
        if not self._current_transaction:
            raise ValueError("No active transaction")
        try:
            await session.commit()
            self._current_transaction = None
        except Exception as e:
            raise RuntimeError(f"Failed to commit transaction: {str(e)}") from e

    async def rollback_transaction(self, session: AsyncSession) -> None:
        """Rollback the current transaction.

        Args:
            session: Database session

        Raises:
            ValueError: If no active transaction.
            Exception: If rollback fails.
        """
        if not self._current_transaction:
            raise ValueError("No active transaction")
        try:
            await session.rollback()
            self._current_transaction = None
        except Exception as e:
            raise RuntimeError(f"Failed to rollback transaction: {str(e)}") from e

    @property
    def current_transaction(self) -> AsyncSession | None:
        """Get current transaction.

        Returns:
            Current transaction or None if no transaction is active
        """
        return self._current_transaction
