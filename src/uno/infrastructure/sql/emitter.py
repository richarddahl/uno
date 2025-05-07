# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""Base class and protocols for SQL emitters."""

from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import Table
from sqlalchemy.engine import Connection
from sqlalchemy.sql import text

from uno.core.errors import FrameworkError
from uno.infrastructure.sql.interfaces import ConfigProtocol
from uno.infrastructure.logging import LoggerService
from uno.infrastructure.sql.interfaces import (
    EngineFactoryProtocol,
)  # DI protocol for engine factories

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

    from uno.infrastructure.sql.engine import SyncEngineFactory
from uno.infrastructure.sql.interfaces import ConnectionConfigProtocol
from uno.infrastructure.sql.observers import BaseObserver, SQLObserver
from uno.infrastructure.sql.statement import SQLStatement, SQLStatementType


class SQLGenerator(Protocol):
    """Protocol for objects that can generate SQL statements."""

    def generate_sql(self) -> list[SQLStatement]:
        """Generate SQL statements.

        Returns:
            List of SQL statements with metadata
        """
        ...


class SQLExecutor(Protocol):
    """Protocol for objects that can execute SQL statements."""

    def execute_sql(
        self, connection: "Connection", statements: list["SQLStatement"]
    ) -> None:
        """
        Execute SQL statements on a connection.

        Args:
            connection: Database connection (must be provided via DI)
            statements: List of SQL statements to execute
        """
        ...


class SQLEmitter(BaseModel):
    """Base class for SQL emitters that generate and execute SQL statements.

    SQL emitters generate SQL statements for various database operations like
    creating tables, functions, triggers, etc. Each property in the model
    can represent a separate SQL statement to be executed.

    Attributes:
        exclude_fields: Fields excluded when dumping the model
        table: Table for which SQL is being generated
        connection_config: Database configuration
        config: Configuration settings
        logger: Logger for this emitter
        engine_factory: Engine factory for creating connections
        observers: Observers for SQL operations
    """

    # Fields excluded when serializing the model
    exclude_fields: ClassVar[list[str]] = [
        "table",
        "config",
        "logger",
        "connection_config",
        "observers",
        "engine_factory",
    ]

    # The table for which SQL is being generated
    table: Table | None = None

    # Database configuration
    connection_config: object | None = (
        None  # DI: must be injected; runtime-checked for protocol compliance (see validator)
    )
    # Configuration settings
    config: object | None = (
        None  # DI: must be injected; runtime-checked for protocol compliance (see validator)
    )

    # Logger for this emitter
    logger: Any

    # Engine factory for creating connections
    engine_factory: object | None = (
        None  # DI: injected; runtime-checked for protocol compliance (see validator)
    )
    # Observers for SQL operations - using BaseObserver which is a concrete class
    observers: list[BaseObserver] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **data):
        logger = data.pop("logger", None) or LoggerService().get_logger(__name__)
        config = data.pop("config", None)
        if config is None:
            raise ValueError("ConfigProtocol instance must be provided via DI.")
        super().__init__(logger=logger, config=config, **data)

    @model_validator(mode="before")
    def initialize_connection_config(cls, values: dict) -> dict:
        """Initialize connection_config and config if not provided and check protocol compliance at runtime.

        Args:
            values: Dictionary of field values

        Returns:
            Updated dictionary of field values
        Raises:
            TypeError: If connection_config or config does not implement required protocol attributes/methods
        """
        conn = values.get("connection_config")
        if conn is not None:
            # Duck-type check for minimal protocol compliance
            required_attrs = [
                "get_uri",
                "db_name",
                "db_user_pw",
                "db_driver",
                "db_role",
                "db_host",
                "db_port",
            ]
            for attr in required_attrs:
                if not hasattr(conn, attr):
                    raise TypeError(
                        f"connection_config must implement '{attr}' (protocol check failed)"
                    )
        config = values.get("config")
        if config is not None:
            required_config_attrs = [
                "DB_NAME",
                "DB_USER_PW",
                "DB_SYNC_DRIVER",
                "DB_SCHEMA",
            ]
            for attr in required_config_attrs:
                if not hasattr(config, attr):
                    raise TypeError(
                        f"config must implement '{attr}' (protocol check failed)"
                    )
        engine_factory = values.get("engine_factory")
        if engine_factory is not None:
            required_factory_attrs = ["create_engine"]
            for attr in required_factory_attrs:
                if not hasattr(engine_factory, attr):
                    raise TypeError(
                        f"engine_factory must implement '{attr}' (protocol check failed)"
                    )
        return values

    def generate_sql(self) -> list[SQLStatement]:
        """Generate SQL statements based on emitter configuration.

        This method converts properties of the model to SQL statements with
        appropriate metadata.

        Returns:
            List of SQL statements with metadata
        """
        statements = []

        # Convert properties to SQL statements with metadata
        for property_name, value in self.model_dump(
            exclude=self.exclude_fields
        ).items():
            if value is None or (
                isinstance(value, (str, list, dict)) and not value
            ):  # Skip empty/None properties
                continue

            # Determine statement type from property name
            statement_type = None
            for type_enum in SQLStatementType:
                if type_enum.value in property_name.lower():
                    statement_type = type_enum
                    break

            # Default to function if type can't be determined
            if statement_type is None:
                statement_type = SQLStatementType.FUNCTION

            statements.append(
                SQLStatement(name=property_name, type=statement_type, sql=value)
            )

        return statements

    def execute_sql(
        self, connection: Connection, statements: list[SQLStatement]
    ) -> None:
        """Execute the generated SQL statements.

        Args:
            connection: Database connection
            statements: List of SQL statements to execute
        """
        db_name = getattr(self.config, "DB_NAME", None)
        if db_name is None:
            raise FrameworkError(
                "DB config must be provided via DI/config injection.", "CONFIG_ERROR"
            )

        if db_name and self.__class__.__name__ != "DropDatabaseAndRoles":
            admin_role = f"{db_name}_admin"
            connection.execute(text(f"SET ROLE {admin_role};"))
            self.logger.debug(f"Set role to {admin_role}")

        for statement in statements:
            self.logger.debug(f"Executing SQL statement: {statement.name}")
            connection.execute(text(statement.sql))

    def emit_sql(
        self, connection: Connection, dry_run: bool = False
    ) -> list[SQLStatement] | None:
        """Generate and optionally execute SQL statements.

        Args:
            connection: Database connection
            dry_run: If True, return statements without executing

        Returns:
            List of SQL statements if dry_run is True, None otherwise

        Raises:
            FrameworkError: If SQL execution fails
        """
        statements = []
        try:
            # Generate SQL statements
            statements = self.generate_sql()

            # Notify observers
            for observer in self.observers:
                observer.on_sql_generated(self.__class__.__name__, statements)

            if dry_run:
                return statements

            # Execute statements
            start_time = time.monotonic()
            self.execute_sql(connection, statements)
            duration = time.monotonic() - start_time

            # Notify observers
            for observer in self.observers:
                observer.on_sql_executed(self.__class__.__name__, statements, duration)

            return None
        except Exception as e:
            # Notify observers of error
            for observer in self.observers:
                observer.on_sql_error(self.__class__.__name__, statements, e)
            raise FrameworkError(f"Failed to execute SQL: {e}", "SQL_EXECUTION_ERROR")

    def emit_with_connection(
        self,
        dry_run: bool = False,
        factory: EngineFactoryProtocol
        | None = None,  # DI: injected, type-hinted with Protocol for extensibility
        config: "ConnectionConfig | None" = None,
        isolation_level: str = "AUTOCOMMIT",
    ) -> list[SQLStatement] | None:
        """Execute SQL with a new connection from the factory.

        Args:
            dry_run: If True, return statements without executing
            factory: Optional engine factory for creating connections
            config: Optional connection configuration
            isolation_level: Transaction isolation level

        Returns:
            List of SQL statements if dry_run is True, None otherwise

        Raises:
            ValueError: If no connection configuration is provided
            FrameworkError: If SQL execution fails
        """
        # Use provided factory or instance factory or create a new one
        engine_factory = (
            factory or self.engine_factory or SyncEngineFactory(logger=self.logger)
        )

        # Use provided config or instance config
        conn_config = config or self.connection_config
        if not conn_config:
            raise ValueError("No connection configuration provided")

        with sync_connection(
            factory=engine_factory,
            config=conn_config,
            isolation_level=isolation_level,
        ) as conn:
            return self.emit_sql(conn, dry_run)

    @classmethod
    def register_observer(cls, observer: SQLObserver) -> None:
        """Register a new observer for all emitter instances.

        We accept any object that implements the SQLObserver protocol, but
        store it as a BaseObserver for compatibility with Pydantic.

        Args:
            observer: Observer to register
        """
        if not hasattr(cls, "observers"):
            cls.observers = []

        # We only accept objects that implement the SQLObserver protocol
        # but we store them as BaseObserver instances for Pydantic compatibility
        if isinstance(observer, BaseObserver) and observer not in cls.observers:
            cls.observers.append(observer)

    def get_function_builder(self) -> "SQLFunctionBuilder":
        """Get a pre-configured SQL function builder with database name set.

        Returns:
            SQLFunctionBuilder: A function builder with database name set
        """
        from uno.infrastructure.sql.builders.function import SQLFunctionBuilder

        builder = SQLFunctionBuilder()

        if self.connection_config:
            builder.with_db_name(self.connection_config.db_name)
        elif self.config:
            builder.with_db_name(self.config.DB_NAME)

        return builder

    def format_sql_template(self, template: str, **kwargs) -> str:
        """Format an SQL template with variables.

        Args:
            template: SQL template string with placeholders
            **kwargs: Values to substitute into the template

        Returns:
            Formatted SQL string

        Raises:
            ValueError: If template formatting fails
        """
        try:
            # Add default values from DB config
            format_args = {}

            # If we have a connection_config, use its attributes
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
            # Otherwise fall back to config
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

            # Override defaults with provided kwargs
            format_args.update(kwargs)

            # Format the template
            return template.format(**format_args)
        except (KeyError, ValueError) as e:
            self.logger.error(f"Error formatting SQL template: {e}")
            raise ValueError(f"Error formatting SQL template: {e}")


# Type verification function for static type checking
def _verify_protocol_compliance() -> None:
    """Verify that SQLEmitter complies with the SQLGenerator and SQLExecutor protocols.

    This function is never called at runtime but helps with static type checking
    to ensure that SQLEmitter implements all required methods from the protocols.
    """
    emitter: SQLEmitter = SQLEmitter()
    generator: SQLGenerator = emitter  # Will raise type error if incompatible
    executor: SQLExecutor = emitter  # Will raise type error if incompatible
