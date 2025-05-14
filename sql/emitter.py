# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""Base class and protocols for SQL emitters.

SQL emitters are responsible for generating and executing SQL statements for various
operations like creating tables, functions, triggers, etc. They use modern Python
type hints, protocols, and error handling to ensure type safety and robustness.
"""

from __future__ import annotations

from typing import Any, TypeVar, TYPE_CHECKING
from typing_extensions import Self

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy.engine import Connection
from sqlalchemy.sql import text

from uno.errors import UnoError
from uno.persistence.sql.errors import (
    SQLErrorCode,
    SQLExecutionError,
    SQLSyntaxError,
)
from uno.persistence.sql.interfaces import (
    ConfigProtocol,
    ConnectionConfigProtocol,
    EngineFactoryProtocol,
)
from uno.logging import LoggerProtocol
from uno.persistence.sql.observers import BaseObserver, SQLObserver
from uno.persistence.sql.statement import SQLStatement, SQLStatementType
from uno.persistence.sql.config import ConnectionConfig
from uno.persistence.sql.engine import SyncEngineFactory, sync_connection

if TYPE_CHECKING:
    from uno.persistence.sql.engine import SyncEngineFactory

T = TypeVar("T", bound="SQLEmitter")


class SQLEmitter(BaseModel):
    """Base class for SQL emitters.

    This class provides common functionality for generating and executing SQL
    statements. It implements the SQLGenerator and SQLExecutor protocols.

    Attributes:
        config: Configuration object (must implement ConfigProtocol)
        connection_config: Database connection configuration
        observers: List of SQLObserver instances
    """

    config: ConfigProtocol
    connection_config: ConnectionConfigProtocol | None = None
    observers: list[BaseObserver] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="before")
    @classmethod
    def initialize_connection_config(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Initialize connection configuration.

        This validator ensures that the connection_config and config objects
        implement the required protocols before initialization.

        Args:
            values: Dictionary of field values

        Returns:
            Updated dictionary of field values

        Raises:
            TypeError: If connection_config or config does not implement required protocol attributes/methods
        """
        connection_config = values.get("connection_config")
        config = values.get("config")

        # Check protocol compliance for connection_config
        if connection_config is not None and not isinstance(
            connection_config, ConnectionConfigProtocol
        ):
            raise TypeError("connection_config must implement ConnectionConfigProtocol")

        # Check protocol compliance for config
        if config is not None and not isinstance(config, ConfigProtocol):
            raise TypeError("config must implement ConfigProtocol")

        return values

    def __init__(
        self, *, logger: LoggerProtocol, config: ConfigProtocol, **data: Any
    ) -> None:
        """Initialize the SQLEmitter with configuration and logger (DI required).

        Args:
            logger: Logger instance (must be provided via DI)
            config: Configuration object (must implement ConfigProtocol)
            **data: Additional keyword arguments

        Raises:
            ValueError: If required configuration or logger is missing
        """
        if logger is None:
            raise ValueError("LoggerProtocol instance must be provided via DI.")
        if config is None:
            raise ValueError("ConfigProtocol instance must be provided via DI.")
        super().__init__(logger=logger, config=config, **data)

    def generate_sql(self) -> list[SQLStatement]:
        """Generate SQL statements.

        This method must be implemented by subclasses to generate the appropriate
        SQL statements for their specific operation.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass
        """
        raise NotImplementedError("Subclasses must implement generate_sql")

    def get_function_builder(self) -> SQLFunctionBuilder:
        """Get a pre-configured SQLFunctionBuilder with the correct database name set.

        Returns:
            SQLFunctionBuilder: A function builder with database name set.

        Raises:
            UnoError: If database configuration is missing.
        """
        builder = SQLFunctionBuilder()
        if self.connection_config and self.connection_config.db_name:
            builder = builder.with_db_name(self.connection_config.db_name)
        elif self.config and hasattr(self.config, "DB_NAME"):
            builder = builder.with_db_name(self.config.DB_NAME)
        else:
            raise UnoError(
                "Database name must be provided in configuration.",
                SQLErrorCode.SQL_CONFIG_MISSING,
            )
        return builder

    def execute_sql(
        self, connection: Connection, statements: list[SQLStatement]
    ) -> None:
        """Execute the generated SQL statements.

        Args:
            connection: Database connection
            statements: List of SQL statements to execute

        Raises:
            UnoError: If database configuration is missing
            SQLExecutionError: If SQL execution fails
        """
        if not self.config:
            raise UnoError(
                "DB config must be provided via DI/config injection.",
                SQLErrorCode.SQL_CONFIG_MISSING,
            )

        db_name = getattr(self.config, "DB_NAME", None)
        if not db_name:
            raise UnoError(
                "Database name must be provided in configuration.",
                SQLErrorCode.SQL_CONFIG_INVALID,
            )

        if db_name and self.__class__.__name__ != "DropDatabaseAndRoles":
            admin_role = f"{db_name}_admin"
            connection.execute(text(f"SET ROLE {admin_role};"))
            await self.logger.debug(f"Set role to {admin_role}")

        for stmt in statements:
            try:
                connection.execute(text(stmt.sql))
                await self.logger.info(
                    f"Executed SQL statement: {stmt.sql}\nMetadata: {stmt.metadata}"
                )
            except Exception as e:
                raise SQLExecutionError(
                    f"Failed to execute SQL statement: {stmt.sql}",
                    SQLErrorCode.SQL_EXECUTION_FAILED,
                    stmt,
                    e,
                ) from e
        await self.logger.info("All SQL statements executed successfully")

    def emit_with_connection(
        self,
        dry_run: bool = False,
        factory: EngineFactoryProtocol | None = None,
        config: ConnectionConfig | None = None,
        isolation_level: str = "AUTOCOMMIT",
    ) -> list[SQLStatement] | None:
        """Execute SQL with a new connection from the factory."""
        engine_factory = factory or SyncEngineFactory(logger=self.logger)
        conn_config = config or self.connection_config
        if conn_config is None:
            raise ValueError("No connection configuration provided.")
        with engine_factory.connect(
            conn_config, isolation_level=isolation_level
        ) as conn:
            return self.emit_sql(conn, dry_run=dry_run)

    def format_sql_template(self, template: str, **kwargs: Any) -> str:
        """Format an SQL template with variables."""
        try:
            format_args: dict[str, str] = {}
            if self.connection_config:
                format_args.update(
                    {
                        "schema_name": self.connection_config.db_schema,
                        "db_name": self.connection_config.db_name,
                        "admin_role": self.connection_config.admin_role,
                        "writer_role": self.connection_config.writer_role,
                        "reader_role": self.connection_config.reader_role,
                    }
                )
            elif self.config:
                format_args.update(
                    {
                        "schema_name": self.config.DB_SCHEMA,
                        "db_name": self.config.DB_NAME,
                        "admin_role": f"{self.config.DB_NAME}_admin",
                        "writer_role": f"{self.config.DB_NAME}_writer",
                        "reader_role": f"{self.config.DB_NAME}_reader",
                    }
                )
            format_args.update(kwargs)
            return template.format(**format_args)
        except (KeyError, ValueError) as e:
            await self.logger.error(f"Error formatting SQL template: {e}")
            raise SQLSyntaxError(
                f"Error formatting SQL template: {e}",
                SQLErrorCode.SQL_TEMPLATE_FORMATTING_FAILED,
            ) from e

    @staticmethod
    def _verify_protocol_compliance() -> None:
        """Verify that SQLEmitter complies with the SQLGenerator and SQLExecutor protocols.

        This method ensures that SQLEmitter implements all required methods from the
        SQLGenerator and SQLExecutor protocols. It's called during class initialization
        to ensure protocol compliance at runtime.
        """
        emitter: SQLEmitter = SQLEmitter()
        generator: SQLGenerator = emitter  # Will raise type error if incompatible
        executor: SQLExecutor = emitter  # Will raise type error if incompatible
