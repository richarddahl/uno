# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""Configuration for SQL generation and execution."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Optional
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import Table
from pydantic_settings import BaseSettings
from uno.infrastructure.config.base import ProdSettingsConfigDict
from uno.infrastructure.sql.interfaces import ConfigManagerProtocol

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


class SQLConfig(BaseSettings):
    """SQL configuration."""
    
    # Connection settings
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_NAME: str = Field(default="uno_db")
    DB_USER: str = Field(default="uno_user")
    DB_PASSWORD: str = Field(default="uno_password")
    
    # SQLAlchemy settings
    DB_POOL_SIZE: int = Field(default=5)
    DB_MAX_OVERFLOW: int = Field(default=10)
    DB_POOL_TIMEOUT: float = Field(default=30.0)
    DB_POOL_RECYCLE: int = Field(default=1800)
    DB_ECHO: bool = Field(default=False)
    DB_ECHO_POOL: bool = Field(default=False)
    
    # Transaction settings
    DB_ISOLATION_LEVEL: str = Field(default="READ COMMITTED")
    DB_READ_ONLY: bool = Field(default=False)
    
    # Validation settings
    DB_VALIDATE_SYNTAX: bool = Field(default=True)
    DB_VALIDATE_DEPENDENCIES: bool = Field(default=True)
    DB_CHECK_PERMISSIONS: bool = Field(default=True)
    
    # Security settings
    DB_CHECK_SQL_INJECTION: bool = Field(default=True)
    DB_AUDIT_LOGGING: bool = Field(default=True)
    
    model_config = ConfigDict(
        env_prefix="DB_",
        extra="forbid"
    )
    
    # Performance settings
    DB_LOG_PERFORMANCE: bool = Field(default=True, description="Log performance metrics")
    DB_SLOW_QUERY_THRESHOLD: float = Field(default=1.0, description="Slow query threshold in seconds")
    
    # Testing settings
    DB_TEST_DATABASE: str = Field(default="test_db", description="Test database name")
    DB_TEST_USER: str = Field(default="test_user", description="Test database user")
    DB_TEST_PASSWORD: str = Field(default="test_password", description="Test database password")
    
    # Documentation settings
    DB_DOCS_INCLUDE_SCHEMAS: bool = Field(default=True, description="Include schema documentation")
    DB_DOCS_INCLUDE_TABLES: bool = Field(default=True, description="Include table documentation")
    DB_DOCS_INCLUDE_VIEWS: bool = Field(default=True, description="Include view documentation")
    DB_DOCS_INCLUDE_FUNCTIONS: bool = Field(default=True, description="Include function documentation")
    DB_DOCS_INCLUDE_TRIGGERS: bool = Field(default=True, description="Include trigger documentation")
    
    # Migration settings
    DB_MIGRATIONS_DIR: Path = Field(default=Path("migrations"), description="Migrations directory")
    DB_MIGRATIONS_TABLE: str = Field(default="schema_versions", description="Schema versions table")
    
    # Logging settings
    DB_LOG_SQL: bool = Field(default=True, description="Log SQL statements")
    DB_LOG_ERRORS: bool = Field(default=True, description="Log SQL errors")
    DB_LOG_PERFORMANCE: bool = Field(default=True, description="Log performance metrics")
    
    def get_connection_url(self) -> str:
        """Get SQLAlchemy connection URL."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    def get_engine_options(self) -> dict[str, Any]:
        """Get SQLAlchemy engine options."""
        return {
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW,
            "pool_timeout": self.DB_POOL_TIMEOUT,
            "pool_recycle": self.DB_POOL_RECYCLE,
            "echo": self.DB_ECHO,
            "echo_pool": self.DB_ECHO_POOL,
            "isolation_level": self.DB_ISOLATION_LEVEL,
        }


# Create default SQL configuration instance
sql_config = SQLConfig()


class ConfigManager:
    """Manages SQL configuration."""

    def __init__(self) -> None:
        """Initialize config manager."""
        self._config: Optional[SQLConfig] = None

    def load_config(self, config_path: str) -> Result[None, str]:
        """Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Result indicating success or failure
        """
        try:
            # TODO: Implement configuration loading
            # This would typically load from a YAML or JSON file
            return Success(None)
        except Exception as e:
            return Failure(str(e))

    def validate_config(self) -> Result[None, str]:
        """Validate configuration.
        
        Returns:
            Result indicating success or failure
        """
        try:
            if not self._config:
                return Failure("Configuration not loaded")
            # TODO: Implement configuration validation
            return Success(None)
        except Exception as e:
            return Failure(str(e))

    def _parse_config_file(self, config_path: str) -> dict[str, Any]:
        """Parse configuration file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        # TODO: Implement configuration file parsing
        return {}

    def _validate_connection_config(self) -> None:
        """Validate connection configuration."""
        if not self._config:
            raise ValueError("Configuration not loaded")
        # TODO: Implement connection validation

    def _validate_transaction_config(self) -> None:
        """Validate transaction configuration."""
        if not self._config:
            raise ValueError("Configuration not loaded")
        # TODO: Implement transaction validation

    def _validate_validation_config(self) -> None:
        """Validate validation configuration."""
        if not self._config:
            raise ValueError("Configuration not loaded")
        # TODO: Implement validation configuration

    def _validate_security_config(self) -> None:
        """Validate security configuration."""
        if not self._config:
            raise ValueError("Configuration not loaded")
        # TODO: Implement security validation

    def _validate_migration_config(self) -> None:
        """Validate migration configuration."""
        if not self._config:
            raise ValueError("Configuration not loaded")
        # TODO: Implement migration validation

    def _validate_documentation_config(self) -> None:
        """Validate documentation configuration."""
        if not self._config:
            raise ValueError("Configuration not loaded")
        # TODO: Implement documentation validation
