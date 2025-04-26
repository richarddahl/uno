"""
Event store manager for managing the event store schema.

This module provides a manager for creating and managing the event store schema
that leverages Uno's SQL generation capabilities for consistent database management.
"""

from __future__ import annotations

# Standard library imports
from typing import Any, Protocol

# Attempt to import optional dependencies
# This allows the core modules to be imported even if SQL components aren't installed
SQLStatementMissing = False
SQLEmittersMissing = False

# Try to import the settings - could be optional in testing environments
try:
    from uno.core.config.settings import uno_settings
except ImportError:
    # For testing - provide a dummy settings object
    class Settings:
        DB_NAME = "test_db"
        DB_HOST = "localhost"
        DB_PORT = 5432
        DB_USER_PW = "test_password"
        DB_SYNC_DRIVER = "psycopg"
        DB_SCHEMA = "public"
    
    uno_settings = Settings()

# Import the logger - should be available in all environments
from uno.core.logging.logger import LoggerService  # noqa: E402

# Try to import SQL components - they may not be available in all environments
try:
    from uno.sql.emitters.event_store import (
        CreateDomainEventsTable,
        CreateEventProcessorsTable,
    )
    from uno.sql.statement import SQLStatement
except ImportError:
    SQLEmittersMissing = True
    SQLStatementMissing = True
    
    # Create stub classes for testing/type checking
    class SQLStatement(Protocol):
        name: str
        sql: str
        
    class SQLEmitter(Protocol):
        def generate_sql(self) -> list[SQLStatement]:
            ...
        
    class CreateDomainEventsTable:
        def __init__(self, config: Any) -> None:
            self.config = config
            
        def generate_sql(self) -> list[SQLStatement]:
            return []
            
    class CreateEventProcessorsTable:
        def __init__(self, config: Any) -> None:
            self.config = config
            
        def generate_sql(self) -> list[SQLStatement]:
            return []


class EventStoreManager:
    """
    Manager for creating and managing the event store schema.

    This class works with the SQLEmitters to generate and execute SQL for
    setting up the event store database objects.
    """

    def __init__(self, logger: LoggerService):
        """
        Initialize the event store manager.

        Args:
            logger: DI-injected LoggerService instance
        """
        self.logger = logger
        self.config = uno_settings

    def create_event_store_schema(self) -> None:
        """
        Create the event store schema in the database.

        This method generates and executes the SQL for creating the event store
        tables, functions, triggers, and grants needed for the event sourcing system.
        """
        self.logger.info("Creating event store schema...")

        # Collect all SQL statements
        statements = self._generate_event_store_sql()
        
        # If there are no statements (due to missing dependencies), exit early
        if not statements:
            self.logger.warning("No SQL statements to execute. Event store schema creation skipped.")
            return
            
        # Try to import database components - they may not be available
        try:
            # Use a synchronous connection instead of async
            import psycopg  # noqa: E402
            from uno.database.config import ConnectionConfig  # noqa: E402
        except ImportError:
            self.logger.error(
                "Database modules not available. Cannot create event store schema."
                " Make sure psycopg and uno.database are installed."
            )
            return

        try:
            # Create connection configuration
            conn_config = ConnectionConfig(
                db_role=f"{self.config.DB_NAME}_admin",  # Use admin role
                db_name=self.config.DB_NAME,
                db_host=self.config.DB_HOST,
                db_port=self.config.DB_PORT,
                db_user_pw=self.config.DB_USER_PW,
                db_driver=self.config.DB_SYNC_DRIVER,
                db_schema=self.config.DB_SCHEMA,
            )

            # Create direct connection string
            conn_string = (
                f"host={conn_config.db_host} "
                f"port={conn_config.db_port} "
                f"dbname={conn_config.db_name} "
                f"user={conn_config.db_role} "
                f"password={conn_config.db_user_pw}"
            )

            # Connect with autocommit for DDL statements
            with psycopg.connect(conn_string, autocommit=True) as conn:
                cursor = conn.cursor()

                # Execute each statement
                for statement in statements:
                    self.logger.debug(f"Executing SQL: {statement.name}")
                    cursor.execute(statement.sql)

            self.logger.info("Event store schema created successfully")

        except Exception as e:
            self.logger.error(f"Error creating event store schema: {e}")
            # Don't raise the exception in tests/development
            if not SQLEmittersMissing:
                raise

    def _generate_event_store_sql(self) -> list[SQLStatement]:
        """
        Generate SQL statements for creating the event store schema.

        Returns:
            List of SQL statements to execute
        """
        # Check if required dependencies are available
        if SQLEmittersMissing or SQLStatementMissing:
            self.logger.warning(
                "SQL emitters or SQL statement modules not available. "
                "Event store schema creation is disabled."
            )
            return []
            
        statements = []

        # Create emitters
        emitters = [
            CreateDomainEventsTable(self.config),
            CreateEventProcessorsTable(self.config),
        ]

        # Generate SQL from each emitter
        for emitter in emitters:
            statements.extend(emitter.generate_sql())

        return statements
