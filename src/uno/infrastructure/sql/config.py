# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""Configuration for SQL generation and execution."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Table

if TYPE_CHECKING:
    from uno.infrastructure.sql.engine import SyncEngineFactory
    from uno.infrastructure.sql.interfaces import ConnectionConfigProtocol


class ConnectionConfig(BaseModel):
    """
    Modernized configuration for database connections in Uno.
    All values must be provided explicitly or via dependency injection/config system.
    No legacy uno_settings dependency.
    """

    db_role: str
    db_name: str
    db_user_pw: str
    db_host: str
    db_port: int
    db_driver: str
    db_schema: str | None = None
    pool_size: int | None = 5
    max_overflow: int | None = 0
    pool_timeout: int | None = 30
    pool_recycle: int | None = 90
    connect_args: dict[str, Any] | None = None

    model_config = ConfigDict(frozen=True)

    def get_uri(self) -> str:
        """
        Construct a SQLAlchemy database URI from connection config.
        Returns:
            str: SQLAlchemy connection URI string
        """
        import urllib.parse

        driver = self.db_driver
        if driver.startswith("postgresql+"):
            driver = driver.replace("postgresql+", "")
        encoded_pw = urllib.parse.quote_plus(self.db_user_pw)
        if "psycopg" in driver or "postgresql" in driver:
            uri = f"postgresql+{driver}://{self.db_role}:{encoded_pw}@{self.db_host}:{self.db_port}/{self.db_name}"
            return uri
        else:
            uri = f"{driver}://{self.db_role}:{encoded_pw}@{self.db_host}:{self.db_port}/{self.db_name}"
            return uri


from uno.infrastructure.sql.registry import SQLConfigRegistry
from uno.core.errors.result import Failure, Result, Success
from uno.infrastructure.sql.interfaces import EngineFactoryProtocol


class SQLConfig(BaseModel):
    """Configuration for SQL generation and execution for a table.

    This class manages SQL emitters for specific tables or database operations.
    It maintains a registry of all SQLConfig subclasses for dynamic registration
    and discovery.

    Attributes:
        default_emitters: Default emitters to use for this config
        table: Table for which SQL is being generated
        connection_config: Connection configuration
        engine_factory: Engine factory for creating connections
        emitters: Emitter instances
    """

    # Default emitters to use for this config
    default_emitters: ClassVar[list[type["SQLEmitter"]]] = []  # type: ignore

    # The table for which SQL is being generated
    table: ClassVar[Table | None] = None

    # Connection configuration
    connection_config: ConnectionConfigProtocol | None = (
        None  # DI: injected, type-hinted with Protocol for extensibility
    )

    # Engine factory for creating connections
    engine_factory: EngineFactoryProtocol | None = (
        None  # Injected by DI, type-hinted with Protocol for extensibility
    )

    # Emitter instances
    emitters: list["SQLEmitter"] = []  # type: ignore

    model_config = {"arbitrary_types_allowed": True}

    def __init_subclass__(cls, **kwargs) -> None:
        """Register the SQLConfig subclass in the registry.

        Args:
            **kwargs: Additional keyword arguments

        Raises:
            FrameworkError: If a subclass with the same name already exists in the registry
        """
        super().__init_subclass__(**kwargs)
        if cls is not SQLConfig:  # Don't register the base class
            SQLConfigRegistry.register(cls)

    def __init__(self, **kwargs):
        """Initialize the SQLConfig with default emitters if none provided.

        Args:
            **kwargs: Initialization parameters
        """
        super().__init__(**kwargs)

        # If no emitters were provided, create them from default_emitters
        if not self.emitters and self.__class__.default_emitters:
            self.emitters = [
                emitter_cls(
                    table=self.__class__.table,
                    connection_config=self.connection_config,
                    engine_factory=self.engine_factory,
                )
                for emitter_cls in self.__class__.default_emitters
            ]

    def emit_sql(self, connection: Connection | None = None) -> None:
        """Emit SQL for all registered emitters.

        Args:
            connection: Optional existing connection to use. If not provided,
                       a new connection will be created using the engine factory.

        Raises:
            FrameworkError: If SQL emission fails
        """
        should_create_connection = connection is None

        try:
            if should_create_connection:
                raise RuntimeError(
                    "SQLConfig.emit_sql requires engine_factory (DI) and connection to be provided externally. Do not construct engine or connection in config."
                )
            else:
                self._emit_sql_internal(connection)
        except SQLAlchemyError as e:
            logging.error(f"Error emitting SQL: {e}")
            raise FrameworkError(f"Failed to emit SQL: {e}", "SQL_EMISSION_ERROR")

    def _emit_sql_internal(self, connection: Connection) -> None:
        """Internal method to emit SQL statements.

        Args:
            connection: Database connection
        """
        for emitter in self.emitters:
            logging.info(f"Emitting SQL for {emitter.__class__.__name__}")
            emitter.emit_sql(connection)
