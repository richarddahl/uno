"""
SQL testing utilities.
"""

from __future__ import annotations
from typing import Any
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import text, MetaData, Table, Column
from sqlalchemy.ext.asyncio import AsyncSession
from uno.persistence.sql.config import SQLConfig
from uno.persistence.sql.connection import ConnectionManager
from uno.logging.protocols import LoggerProtocol


class MockDatabase(BaseModel):
    """Mock database configuration."""

    name: str
    user: str
    password: str
    created_at: datetime
    tables: list[str]


class SQLTestHelper:
    """Manages mock databases and provides testing utilities."""

    def __init__(
        self,
        config: SQLConfig,
        connection_manager: ConnectionManager,
        logger: LoggerProtocol,
    ) -> None:
        """Initialize test helper.

        Args:
            config: SQL configuration
            connection_manager: Connection manager
            logger: Logger service
        """
        self._config = config
        self._connection_manager = connection_manager
        self._logger = logger
        self._mock_databases: dict[str, MockDatabase] = {}

    async def create_mock_database(self, name: str | None = None) -> str:
        """Create a mock database.

        Args:
            name: Optional database name, defaults to mock_db_{timestamp}

        Returns:
            Name of the created database

        Raises:
            ValueError: If database creation fails
        """
        try:
            db_name = name or f"mock_db_{int(datetime.now().timestamp())}"

            async with self._connection_manager.get_connection() as session:
                # Create database
                await session.execute(text(f"CREATE DATABASE {db_name}"))

                # Create mock user if needed
                if self._config.DB_TEST_USER:
                    await session.execute(
                        text(
                            f"CREATE USER {self._config.DB_TEST_USER} "
                            f"WITH PASSWORD '{self._config.DB_TEST_PASSWORD}'"
                        )
                    )
                    await session.execute(
                        text(
                            f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {self._config.DB_TEST_USER}"
                        )
                    )

                self._mock_databases[db_name] = MockDatabase(
                    name=db_name,
                    user=self._config.DB_TEST_USER,
                    password=self._config.DB_TEST_PASSWORD,
                    created_at=datetime.now(),
                    tables=[],
                )

                self._logger.structured_log(
                    "INFO",
                    f"Created mock database {db_name}",
                    name="uno.sql.testing",
                    database=db_name,
                )
                return db_name
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to create mock database: {str(e)}",
                name="uno.sql.testing",
                error=e,
            )
            raise RuntimeError(f"Failed to create mock database: {str(e)}") from e
    async def cleanup_mock_database(self, name: str) -> None:
        """Clean up a mock database.

        Args:
            name: Database name to clean up

        Raises:
            ValueError: If database not found
            Exception: If cleanup fails
        """
        try:
            if name not in self._mock_databases:
                raise ValueError(f"Mock database {name} not found")

            async with self._connection_manager.get_connection() as session:
                # Drop database
                await session.execute(text(f"DROP DATABASE {name}"))

                # Drop mock user if needed
                if self._config.DB_TEST_USER:
                    await session.execute(
                        text(f"DROP USER {self._config.DB_TEST_USER}")
                    )

                del self._mock_databases[name]

                self._logger.structured_log(
                    "INFO",
                    f"Cleaned up mock database {name}",
                    name="uno.sql.testing",
                    database=name,
                )
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to clean up mock database {name}: {str(e)}",
                name="uno.sql.testing",
                error=e,
            )
            raise RuntimeError(f"Failed to clean up mock database: {str(e)}") from e
    async def create_mock_tables(
        self, db_name: str, tables: list[dict[str, Any]]
    ) -> None:
        """Create mock tables in a database.

        Args:
            db_name: Database name
            tables: List of table definitions

        Raises:
            ValueError: If database not found
            Exception: If table creation fails
        """
        try:
            if db_name not in self._mock_databases:
                raise ValueError(f"Mock database {db_name} not found")

            async with self._connection_manager.get_connection() as session:
                metadata = MetaData()

                for table_def in tables:
                    table = Table(
                        table_def["name"],
                        metadata,
                        *[
                            Column(
                                col["name"],
                                col["type"],
                                primary_key=col.get("primary_key", False),
                                nullable=col.get("nullable", True),
                            )
                            for col in table_def["columns"]
                        ],
                    )
                    await session.run_sync(metadata.create_all)
                    self._mock_databases[db_name].tables.append(table_def["name"])

                self._logger.structured_log(
                    "INFO",
                    f"Created mock tables in {db_name}",
                    name="uno.sql.testing",
                    database=db_name,
                    tables=[t["name"] for t in tables],
                )
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to create mock tables in {db_name}: {str(e)}",
                name="uno.sql.testing",
                error=e,
            )
            raise RuntimeError(f"Failed to create mock tables: {str(e)}") from e
    async def cleanup_mock_tables(self, db_name: str) -> None:
        """Clean up mock tables in a database.

        Args:
            db_name: Database name

        Raises:
            ValueError: If database not found
            Exception: If table cleanup fails
        """
        try:
            if db_name not in self._mock_databases:
                raise ValueError(f"Mock database {db_name} not found")

            async with self._connection_manager.get_connection() as session:
                for table in self._mock_databases[db_name].tables:
                    await session.execute(text(f"DROP TABLE IF EXISTS {table}"))

                self._mock_databases[db_name].tables.clear()

                self._logger.structured_log(
                    "INFO",
                    f"Cleaned up mock tables in {db_name}",
                    name="uno.sql.testing",
                    database=db_name,
                )
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to clean up mock tables in {db_name}: {str(e)}",
                name="uno.sql.testing",
                error=e,
            )
            raise RuntimeError(f"Failed to clean up mock tables: {str(e)}") from e
    async def rollback_transaction(self, session: AsyncSession) -> None:
        """Rollback a transaction for testing.

        Args:
            session: Database session

        Raises:
            Exception: If transaction rollback fails
        """
        try:
            await session.rollback()
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to rollback transaction: {str(e)}",
                name="uno.sql.testing",
                error=e,
            )
            raise RuntimeError(f"Failed to rollback transaction: {str(e)}") from e
    @property
    def mock_databases(self) -> dict[str, MockDatabase]:
        """Get all mock databases.

        Returns:
            Dictionary of mock databases
        """
        return self._mock_databases
