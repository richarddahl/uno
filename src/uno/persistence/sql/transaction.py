"""
SQL transaction management.
"""

from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from uno.errors.result import Result, Success, Failure
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
        self._current_transaction:int | NoneAsyncSession] = None

    async def begin_transaction(self, session: AsyncSession) -> Result[None, str]:
        """Begin a new transaction.

        Args:
            session: Database session

        Returns:
            Result indicating success or failure
        """
        try:
            if self._config.DB_READ_ONLY:
                return Failure("Cannot begin transaction in read-only mode")
            self._current_transaction = session
            return Success(None)
        except Exception as e:
            return Failure(f"Failed to begin transaction: {str(e)}")

    async def commit_transaction(self, session: AsyncSession) -> Result[None, str]:
        """Commit the current transaction.

        Args:
            session: Database session

        Returns:
            Result indicating success or failure
        """
        try:
            if not self._current_transaction:
                return Failure("No active transaction")
            await session.commit()
            self._current_transaction = None
            return Success(None)
        except Exception as e:
            return Failure(f"Failed to commit transaction: {str(e)}")

    async def rollback_transaction(self, session: AsyncSession) -> Result[None, str]:
        """Rollback the current transaction.

        Args:
            session: Database session

        Returns:
            Result indicating success or failure
        """
        try:
            if not self._current_transaction:
                return Failure("No active transaction")
            await session.rollback()
            self._current_transaction = None
            return Success(None)
        except Exception as e:
            return Failure(f"Failed to rollback transaction: {str(e)}")

    @property
    def current_transaction(self) ->int | NoneAsyncSession]:
        """Get current transaction.

        Returns:
            Current transaction or None if no transaction is active
        """
        return self._current_transaction
