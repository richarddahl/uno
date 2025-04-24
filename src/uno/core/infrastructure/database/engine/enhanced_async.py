# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Enhanced async database engine with improved cancellation handling.

This module extends the base async database engine with:
- Improved cancellation handling
- Integration with the task management system
- Structured concurrency for database operations
- Enhanced connection retry logic
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager
from typing import Any, TypeVar

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from uno.core.async_utils import (
    AsyncContextGroup,
    AsyncExitStack,
    AsyncLock,
    Limiter,
    TaskGroup,
    timeout,
)
from typing import TYPE_CHECKING
from uno.infrastructure.database.config import ConnectionConfig
from uno.infrastructure.database.engine.asynceng import AsyncEngineFactory

if TYPE_CHECKING:
    from uno.core.logging.logger import LoggerService

T = TypeVar("T")


class EnhancedAsyncEngineFactory(AsyncEngineFactory):
    """
    Enhanced factory for asynchronous database engines with better concurrency control.

    This factory extends AsyncEngineFactory with:
    - Connection pooling limits to prevent connection exhaustion
    - Instrumentation for monitoring connection usage
    - Integration with the task management system
    """

    def __init__(
        self,
        logger_service: "LoggerService",
        connection_limiter: Limiter | None = None,
    ):
        """
        Initialize the enhanced async engine factory.

        Args:
            logger_service: DI-injected LoggerService
            connection_limiter: Optional limiter to control the number of concurrent connections
        """
        super().__init__(logger_service=logger_service)
        self.connection_limiter = connection_limiter or Limiter(
            max_concurrent=10, name="db_connection_limiter"
        )
        self._connection_locks = {}  # Per-connection config locks

    def get_connection_lock(self, config: ConnectionConfig) -> AsyncLock:
        """
        Get a lock for a specific connection configuration.

        This ensures that connection attempts for the same configuration
        are properly serialized to avoid race conditions.

        Args:
            config: The connection configuration

        Returns:
            An async lock for this connection configuration
        """
        # Create a key from connection details
        conn_key = f"{config.db_role}@{config.db_host}/{config.db_name}"

        # Create a lock if one doesn't exist
        if conn_key not in self._connection_locks:
            self._connection_locks[conn_key] = AsyncLock(name=f"conn_lock_{conn_key}")

        return self._connection_locks[conn_key]


async def connect_with_retry(
    config: ConnectionConfig,
    logger_service: "LoggerService",
    factory: EnhancedAsyncEngineFactory | None = None,
    max_retries: int = 3,
    base_retry_delay: float = 1.0,
    isolation_level: str = "AUTOCOMMIT",
) -> AsyncConnection:
    """
    Connect to the database with retry logic and timeout.

    Args:
        config: Connection configuration
        factory: Optional engine factory
        max_retries: Maximum number of connection attempts
        base_retry_delay: Base delay between retries (will be multiplied by attempt number)
        isolation_level: SQL transaction isolation level
        logger: Optional logger instance

    Returns:
        An open database connection

    Raises:
        SQLAlchemyError: If connection failed after all retries
    """
    # Use provided factory or create a new one
    engine_factory = factory or EnhancedAsyncEngineFactory(logger_service=logger_service)
    log = logger_service.get_logger(__name__)

    # Get or create the connection lock for this config
    conn_lock = engine_factory.get_connection_lock(config)

    # Get the connection limiter
    conn_limiter = engine_factory.connection_limiter

    attempt = 0
    last_error = None
    engine = None
    connection = None

    # Try to acquire the connection lock first
    async with conn_lock:
        # Then try to acquire a connection slot from the limiter
        async with conn_limiter:
            while attempt < max_retries:
                try:
                    # Create engine with proper timeouts
                    engine = engine_factory.create_engine(config)

                    # Attempt to connect with timeout
                    async with timeout(10.0, "Database connection timeout"):
                        connection = await engine.connect()

                    # Set isolation level
                    await connection.execution_options(isolation_level=isolation_level)

                    # Execute callbacks on successful connection
                    engine_factory.execute_callbacks(connection)

                    # Log successful connection
                    log.debug(
                        f"Connected to {config.db_role}@{config.db_host}/{config.db_name} "
                        f"(attempt {attempt+1}/{max_retries})"
                    )

                    # Return the open connection
                    return connection

                except (TimeoutError, SQLAlchemyError) as e:
                    last_error = e
                    attempt += 1

                    # Dispose of the engine if created
                    if engine is not None:
                        await engine.dispose()
                        engine = None

                    # Close the connection if created
                    if connection is not None:
                        await connection.close()
                        connection = None

                    # If we have more attempts, wait and retry
                    if attempt < max_retries:
                        # Exponential backoff with jitter
                        delay = base_retry_delay * (2 ** (attempt - 1))
                        # Add some randomness to avoid thundering herd
                        jitter = asyncio.Task.current_task().get_name()[-1:]
                        delay += float(ord(jitter[0]) % 10) / 10 if jitter else 0

                        log.warning(
                            f"Database connection attempt {attempt}/{max_retries} "
                            f"failed. Retrying in {delay:.2f}s... Error: {e!s}"
                        )
                        await asyncio.sleep(delay)
                    else:
                        log.error(
                            f"Failed to connect after {max_retries} attempts. "
                            f"Last error: {e!s}"
                        )

    # If we've exhausted all attempts, raise the last error
    if last_error is not None:
        raise last_error

    # This should never happen, but added for type safety
    raise RuntimeError("Failed to connect to database for unknown reason")


class AsyncConnectionContext(AbstractAsyncContextManager[AsyncConnection]):
    """
    Enhanced async connection context manager with improved error handling.

    This context manager provides:
    - Automatic connection retry
    - Proper connection disposal on errors
    - Integration with the task management system
    """

    def __init__(
        self,
        db_role: str,
        logger_service: "LoggerService",
        db_name: str | None = None,
        db_host: str | None = None,
        db_user_pw: str | None = None,
        db_driver: str | None = None,
        db_port: int | None = None,
        config: ConnectionConfig | None = None,
        isolation_level: str = "AUTOCOMMIT",
        factory: EnhancedAsyncEngineFactory | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs: Any,
    ):
        self.db_role = db_role
        self.logger_service = logger_service
        self.db_name = db_name
        self.db_host = db_host
        self.db_user_pw = db_user_pw
        self.db_driver = db_driver
        self.db_port = db_port
        self.config = config
        self.isolation_level = isolation_level
        self.factory = factory
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logger_service.get_logger(__name__)
        self.kwargs = kwargs
        self.engine = None
        self.connection = None

    async def __aenter__(self) -> AsyncConnection:
        """Enter the async context, returning a database connection."""
        try:
            # Connect with retry logic
            self.connection = await connect_with_retry(
                config=self.config,
                logger_service=self.logger_service,
                factory=self.factory,
                max_retries=self.max_retries,
                base_retry_delay=self.retry_delay,
                isolation_level=self.isolation_level,
            )

            # Store the engine for cleanup
            self.engine = self.connection.engine

            return self.connection

        except Exception as e:
            # Clean up any resources on error
            await self.__aexit__(type(e), e, e.__traceback__)
            raise

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the async context, closing the connection and disposing of the engine."""
        # Close the connection if open
        if self.connection is not None:
            try:
                await self.connection.close()
            except Exception as e:
                self.logger.warning(f"Error closing connection: {e!s}")
            finally:
                self.connection = None

        # Dispose of the engine if created
        if self.engine is not None:
            try:
                await self.engine.dispose()
            except Exception as e:
                self.logger.warning(f"Error disposing engine: {e!s}")
            finally:
                self.engine = None


async def enhanced_async_connection(
    db_role: str,
    logger_service: "LoggerService",
    db_name: str | None = None,
    db_host: str | None = None,
    db_user_pw: str | None = None,
    db_driver: str | None = None,
    db_port: int | None = None,
    config: ConnectionConfig | None = None,
    isolation_level: str = "AUTOCOMMIT",
    factory: EnhancedAsyncEngineFactory | None = None,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    **kwargs: Any,
) -> AsyncIterator[AsyncConnection]:
    """
    Enhanced context manager for asynchronous database connections.

    This function provides:
    - Improved connection retry logic
    - Better resource cleanup
    - Integration with the task management system

    Args:
        db_role: Database role/username
        db_name: Database name
        db_host: Database host
        db_user_pw: Database password
        db_driver: Database driver (e.g., 'postgresql+asyncpg')
        db_port: Database port
        config: Optional pre-configured ConnectionConfig
        isolation_level: SQL transaction isolation level
        factory: Optional engine factory
        max_retries: Maximum connection attempts
        retry_delay: Base delay between retries
        logger: Optional logger
        **kwargs: Additional connection parameters

    Yields:
        AsyncConnection: An open database connection
    """
    # Create and use the connection context
    context = AsyncConnectionContext(
        db_role=db_role,
        logger_service=logger_service,
        db_name=db_name,
        db_host=db_host,
        db_user_pw=db_user_pw,
        db_driver=db_driver,
        db_port=db_port,
        config=config,
        isolation_level=isolation_level,
        factory=factory,
        max_retries=max_retries,
        retry_delay=retry_delay,
        **kwargs,
    )

    async with context as connection:
        yield connection


class DatabaseOperationGroup:
    """
    Group for coordinating multiple database operations.

    This class provides:
    - Coordination of multiple connections/sessions
    - Proper cleanup even if operations are cancelled
    - Automatic transaction management
    """

    def __init__(
        self,
        logger_service: "LoggerService",
        name: str | None = None,
    ):
        """
        Initialize a database operation group.

        Args:
            logger_service: DI-injected LoggerService
            name: Optional name for the group (for logging)
        """
        self.name = name or f"db_op_group_{id(self):x}"
        self.logger = logger_service.get_logger(__name__)
        self.task_group = TaskGroup(name=self.name, logger=self.logger)
        self.context_group = AsyncContextGroup()
        self.exit_stack = AsyncExitStack()

    async def __aenter__(self) -> "DatabaseOperationGroup":
        """Enter the database operation group context."""
        await self.exit_stack.__aenter__()
        await self.exit_stack.enter_async_context(self.task_group)
        await self.exit_stack.enter_async_context(self.context_group)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the database operation group context, cleaning up all resources."""
        await self.exit_stack.__aexit__(exc_type, exc_val, exc_tb)

    async def execute_in_transaction(
        self,
        session: AsyncSession,
        operations: list[Callable[[AsyncSession], Any]],
    ) -> list[Any]:
        """
        Execute multiple operations in a single database transaction.

        Args:
            session: The async database session
            operations: List of callables that take a session and return a coroutine

        Returns:
            List of results from each operation
        """
        results = []
        async with session.begin():
            for operation in operations:
                result = await operation(session)
                results.append(result)
        return results

    async def run_operation(
        self,
        operation: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Run a database operation in the task group.

        Args:
            operation: The async operation to run
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            The result of the operation
        """
        return await self.task_group.create_task(
            operation(*args, **kwargs),
            name=f"{self.name}_{operation.__name__}",
        )
