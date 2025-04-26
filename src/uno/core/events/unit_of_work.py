"""
Unit of Work pattern implementation for event sourcing.

This module provides a Unit of Work (UoW) pattern implementation that coordinates
event persistence and publishing within transactional boundaries.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, AsyncTransaction

from uno.core.errors.result import Failure, Result, Success
from uno.core.events.event_store import EventStore
from uno.core.logging.logger import LoggerService
from uno.core.logging.logger import LoggingConfig


T = TypeVar('T')


class UnitOfWork(ABC):
    """
    Unit of Work abstract base class.
    
    The Unit of Work pattern provides a way to group operations into a single
    transactional unit, ensuring that they either all succeed or all fail.
    """
    
    @abstractmethod
    async def commit(self) -> Result[None, Exception]:
        """
        Commit all changes made within this unit of work.
        
        Returns:
            Result with None on success, or an error
        """
        ...
    
    @abstractmethod
    async def rollback(self) -> Result[None, Exception]:
        """
        Roll back all changes made within this unit of work.
        
        Returns:
            Result with None on success, or an error
        """
        ...
    
    @classmethod
    @abstractmethod
    @asynccontextmanager
    async def begin(cls, *args: Any, **kwargs: Any) -> AsyncGenerator["UnitOfWork", None]:
        """
        Begin a new unit of work.
        
        Yields:
            A new UnitOfWork instance
        """
        yield None


class InMemoryUnitOfWork(UnitOfWork):
    """
    In-memory implementation of the Unit of Work pattern.
    
    This implementation doesn't actually provide transactional guarantees,
    but it follows the same interface for testing and development.
    """
    
    def __init__(self, event_store: EventStore, logger_factory: Callable[..., LoggerService] | None = None):
        """
        Initialize the in-memory unit of work.
        
        Args:
            event_store: The event store to use
            logger_factory: Optional factory for creating loggers
        """
        self.event_store = event_store
        
        # Use provided logger factory or create a default logger
        if logger_factory:
            self.logger = logger_factory("uow_inmem")
        else:
            self.logger = LoggerService(LoggingConfig())

        self._committed = False
    
    async def commit(self) -> Result[None, Exception]:
        """
        Mark the unit of work as committed.
        
        In memory, there's nothing to actually commit, but we track the state
        for consistency with the interface.
        
        Returns:
            Result with None on success
        """
        try:
            self._committed = True
            self.logger.structured_log(
                "DEBUG",
                "In-memory unit of work committed",
                name="uno.events.uow"
            )
            return Success(None)
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error committing in-memory unit of work: {e}",
                name="uno.events.uow",
                error=e
            )
            return Failure(e)
    
    async def rollback(self) -> Result[None, Exception]:
        """
        Mark the unit of work as rolled back.
        
        In memory, there's nothing to actually roll back, but we track the state
        for consistency with the interface.
        
        Returns:
            Result with None on success
        """
        try:
            self._committed = False
            self.logger.structured_log(
                "DEBUG",
                "In-memory unit of work rolled back",
                name="uno.events.uow"
            )
            return Success(None)
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error rolling back in-memory unit of work: {e}",
                name="uno.events.uow",
                error=e
            )
            return Failure(e)
    
    @classmethod
    @asynccontextmanager
    async def begin(
        cls, 
        event_store: EventStore, 
        logger_factory: Callable[..., LoggerService] | None = None
    ) -> AsyncGenerator["InMemoryUnitOfWork", None]:
        """
        Begin a new in-memory unit of work.
        
        Args:
            event_store: The event store to use
            logger_factory: Optional factory for creating loggers
            
        Yields:
            A new InMemoryUnitOfWork instance
        """
        uow = cls(event_store, logger_factory)
        
        try:
            yield uow
            await uow.commit()
        except Exception as e:
            if logger_factory:
                logger = logger_factory("uow_inmem")
            else:
                logger = LoggerService(LoggingConfig())

            logger.structured_log(
                "ERROR",
                f"Error in unit of work: {e}",
                name="uno.events.uow",
                error=e
            )
            await uow.rollback()
            raise


class PostgresUnitOfWork(UnitOfWork):
    """
    PostgreSQL implementation of the Unit of Work pattern.
    
    This implementation provides real transactional guarantees using
    PostgreSQL's transaction support.
    """
    
    def __init__(
        self, 
        event_store: EventStore, 
        session: AsyncSession,
        transaction: AsyncTransaction,
        logger_factory: Callable[..., LoggerService] | None = None
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
            self.logger = LoggerService(LoggingConfig())

    async def commit(self) -> Result[None, Exception]:
        """
        Commit the transaction.
        
        Returns:
            Result with None on success, or an error
        """
        try:
            await self.transaction.commit()
            self.logger.structured_log(
                "DEBUG",
                "PostgreSQL unit of work committed",
                name="uno.events.uow"
            )
            return Success(None)
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error committing PostgreSQL unit of work: {e}",
                name="uno.events.uow",
                error=e
            )
            return Failure(e)
    
    async def rollback(self) -> Result[None, Exception]:
        """
        Roll back the transaction.
        
        Returns:
            Result with None on success, or an error
        """
        try:
            await self.transaction.rollback()
            self.logger.structured_log(
                "DEBUG",
                "PostgreSQL unit of work rolled back",
                name="uno.events.uow"
            )
            return Success(None)
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error rolling back PostgreSQL unit of work: {e}",
                name="uno.events.uow",
                error=e
            )
            return Failure(e)
    
    @classmethod
    @asynccontextmanager
    async def begin(
        cls, 
        event_store: EventStore, 
        session_factory: Callable[..., AsyncSession],
        logger_factory: Callable[..., LoggerService] | None = None
    ) -> AsyncGenerator["PostgresUnitOfWork", None]:
        """
        Begin a new PostgreSQL unit of work.
        
        Args:
            event_store: The event store to use
            session_factory: Factory function for creating database sessions
            logger_factory: Optional factory for creating loggers
            
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
                        logger = LoggerService(LoggingConfig())

                    logger.structured_log(
                        "ERROR",
                        f"Error in PostgreSQL unit of work: {e}",
                        name="uno.events.uow",
                        error=e
                    )
                    # Transaction is automatically rolled back by the session.begin() context
                    raise


async def execute_in_transaction(
    uow: UnitOfWork,
    func: Callable[..., AsyncGenerator[T, None]],
    *args: Any,
    **kwargs: Any
) -> Result[T, Exception]:
    """
    Execute an operation within a transaction.
    
    Args:
        uow: The unit of work to use
        func: The function to execute
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Result with the function's return value on success, or an error
    """
    try:
        result = await func(uow, *args, **kwargs)
        return Success(result)
    except Exception as e:
        return Failure(e)


async def execute_operations(
    uow: UnitOfWork,
    operations: list[Callable[[UnitOfWork], AsyncGenerator[Result[T, Exception], None]]],
) -> Result[list[T], Exception]:
    """
    Execute multiple operations within a single transaction.
    
    Args:
        uow: The unit of work to use
        operations: The operations to execute
        
    Returns:
        Result with a list of the operations' return values on success, or an error
    """
    results = []
    
    try:
        for operation in operations:
            result = await operation(uow)
            if result.is_failure:
                return Failure(result.error)
            results.append(result.value)
        
        return Success(results)
    except Exception as e:
        return Failure(e)
