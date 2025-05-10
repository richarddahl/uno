# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Protocols for Uno SQL infrastructure DI/extension points.
"""
from __future__ import annotations


from typing import Protocol, Any, runtime_checkable


class EngineFactoryProtocol(Protocol):
    """Protocol for DI engine factory (sync or async)."""

    def get_engine(self) -> Any: ...


@runtime_checkable
class ConnectionConfigProtocol(Protocol):
    """
    Protocol for Uno SQL connection configuration.
    Defines the minimal interface required by engine factories and emitters.
    """

    db_name: str
    db_user_pw: str
    db_driver: str
    db_role: str
    db_host: str
    db_port: int
    db_schema: str | None
    pool_size: int | None
    max_overflow: int | None
    pool_timeout: int | None
    pool_recycle: int | None
    connect_args: dict[str, Any] | None

    def get_uri(self) -> str: ...


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection
    from uno.persistence.sql.statement import SQLStatement


class SQLEmitterProtocol(Protocol):
    """
    Protocol for Uno SQL emitters.
    Defines the minimal interface required for DI/type-hinting in factories, registries, and services.
    """

    def generate_sql(self) -> list["SQLStatement"]: ...

    def emit_sql(
        self, connection: "Connection", dry_run: bool = False
    ) -> list["SQLStatement"] | None: ...


"""
SQL infrastructure interfaces and protocols.
"""

from typing import Any, Protocol, TypeVar, runtime_checkable, Generic


@runtime_checkable
class ConfigProtocol(Protocol):
    """Protocol for configuration providers."""

    def get(self, key: str, default: Any = None) -> Any: ...
    def get_bool(self, key: str, default: bool = False) -> bool: ...
    def get_int(self, key: str, default: int = 0) -> int: ...
    def get_float(self, key: str, default: float = 0.0) -> float: ...
    def get_list(self, key: str, default: list[Any] = None) -> list[Any]: ...


T = TypeVar("T")


@runtime_checkable
class UnitOfWorkProtocol(Protocol):
    """Protocol for unit of work implementations."""

    def __enter__(self) -> "UnitOfWorkProtocol": ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


@runtime_checkable
class RepositoryProtocol(Protocol, Generic[T]):
    """Protocol for repository interfaces."""

    def add(self, entity: T) -> None: ...
    def get(self, entity_id: str) -> T | None: ...
    def remove(self, entity: T) -> None: ...
    def list(self) -> list[T]: ...


@runtime_checkable
class SQLEmitterFactoryProtocol(Protocol):
    def create(self, emitter_type: str, **kwargs: Any) -> Any: ...


class DBManagerProtocol(Protocol):
    """
    DBManagerProtocol: Protocol for database manager services (sync).
    """

    def execute_ddl(self, ddl: str) -> None: ...
    def execute_script(self, script: str) -> None: ...
    def execute_from_emitter(self, emitter: Any) -> None: ...
    def execute_from_emitters(self, emitters: list[Any]) -> None: ...
    def create_schema(self, schema_name: str) -> None: ...
    def drop_schema(self, schema_name: str, cascade: bool = False) -> None: ...
    def create_extension(
        self, extension_name: str, schema: str | None = None
    ) -> None: ...
    def table_exists(self, table_name: str, schema: str | None = None) -> bool: ...
    def function_exists(
        self, function_name: str, schema: str | None = None
    ) -> bool: ...
    def type_exists(self, type_name: str, schema: str | None = None) -> bool: ...
    def trigger_exists(
        self, trigger_name: str, table_name: str, schema: str | None = None
    ) -> bool: ...
    def policy_exists(
        self, policy_name: str, table_name: str, schema: str | None = None
    ) -> bool: ...


class SQLExecutionServiceProtocol(Protocol):
    """
    SQLExecutionProtocol: Protocol for SQL execution services.
    """

    def execute_ddl(self, ddl: str) -> None: ...
    def execute_script(self, script: str) -> None: ...
    def execute_emitter(self, emitter: Any, dry_run: bool = False) -> list[Any]: ...


from uno.errors import UnoError
from uno.persistence.sql.errors import (
    SQLErrorCode,
    SQLStatementError,
    SQLExecutionError,
    SQLSyntaxError,
    SQLEmitterError,
    SQLEmitterInvalidConfigError,
    SQLRegistryClassNotFoundError,
    SQLRegistryClassAlreadyExistsError,
    SQLConfigError,
    SQLConfigInvalidError,
)

T = TypeVar("T")


@runtime_checkable
class ConnectionManagerProtocol(Protocol):
    """Protocol for managing database connections."""

    async def get_connection(self, isolation_level: str = "AUTOCOMMIT") -> Any:
        """Get a database connection."""
        ...

    async def release_connection(self, connection: Any) -> None:
        """Release a database connection."""
        ...


@runtime_checkable
class TransactionManagerProtocol(Protocol):
    """Protocol for managing database transactions."""

    async def begin_transaction(self, connection: Any) -> None:
        """Begin a new transaction."""
        ...

    async def commit_transaction(self, connection: Any) -> None:
        """Commit the current transaction."""
        ...

    async def rollback_transaction(self, connection: Any) -> None:
        """Rollback the current transaction."""
        ...


@runtime_checkable
class SQLValidatorProtocol(Protocol):
    """Protocol for validating SQL statements."""

    def validate_statement(self, statement: Any) -> None:
        """
        Validate a SQL statement.
        Raises:
            UnoError: if validation fails
        """
        """Validate a SQL statement."""
        ...

    def validate_dependencies(self, statements: list[Any]) -> None:
        """
        Validate SQL statement dependencies.
        Raises:
            UnoError: if dependency validation fails
        """
        """Validate statement dependencies."""
        ...


@runtime_checkable
class PerformanceMonitorProtocol(Protocol):
    """Protocol for monitoring SQL performance."""

    def record_execution_time(self, statement: Any, duration: float) -> None:
        """Record statement execution time."""
        ...

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics."""
        ...


@runtime_checkable
class SecurityManagerProtocol(Protocol):
    """Protocol for managing SQL security."""

    def sanitize_statement(self, statement: Any) -> Any:
        """Sanitize SQL statement to prevent injection."""
        ...

    def validate_permissions(self, statement: Any) -> None:
        """
        Validate SQL statement permissions.
        Raises:
            UnoError: if permission validation fails
        """
        """Validate user permissions for statement."""
        ...


@runtime_checkable
class MockHelperProtocol(Protocol):
    """Protocol for SQL mock helpers."""

    def setup_mock_database(self) -> None:
        """Set up mock database."""
        ...

    def cleanup_mock_database(self) -> None:
        """Clean up mock database."""
        ...

    def create_mock_tables(self, tables: list[dict[str, Any]]) -> None:
        """Create mock tables.

        Args:
            tables: List of table definitions
        """
        ...

    def cleanup_mock_tables(self) -> None:
        """Clean up mock tables."""
        ...


@runtime_checkable
class DocumentationGeneratorProtocol(Protocol):
    """Protocol for generating SQL documentation."""

    def generate_schema_docs(self) -> str:
        """Generate schema documentation."""
        ...

    def generate_function_docs(self) -> str:
        """Generate function documentation."""
        ...


@runtime_checkable
class MigrationManagerProtocol(Protocol):
    """Protocol for managing SQL migrations."""

    def create_migration(self, name: str) -> None:
        """Create a new migration."""
        ...

    def apply_migrations(self) -> None:
        """
        Apply database migrations.
        Raises:
            UnoError: if migration fails
        """
        """Apply pending migrations."""
        ...


@runtime_checkable
class ConfigManagerProtocol(Protocol):
    """Protocol for managing SQL configuration."""

    def load_config(self, path: str) -> None:
        """
        Load configuration from the given path.
        Raises:
            UnoError: if loading fails
        """
        """Load configuration from file."""
        ...

    def validate_config(self) -> None:
        """
        Validate loaded configuration.
        Raises:
            UnoError: if config is invalid
        """
        """Validate configuration."""
        ...


@runtime_checkable
class SQLLoggerProtocol(Protocol):
    """Protocol for logging SQL operations."""

    def log_statement(self, statement: Any) -> None:
        """Log SQL statement."""
        ...

    def log_error(self, error: Exception) -> None:
        """Log SQL error."""
        ...
