"""
Centralized DI-based database provider for Uno.
Supports Postgres, in-memory, and file-based backends via uno.infrastructure.config.
"""

from typing import Any
from uno.infrastructure.sql.interfaces import ConfigProtocol
from uno.infrastructure.config import get_config
from uno.infrastructure.config.database import DatabaseConfig
from uno.infrastructure.di import (
    ServiceCollection,
    ServiceProvider,
    ServiceScope,
)
# NOTE: Strict DI mode: All dependencies must be passed explicitly. Do not use service locator patterns.
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

_DB_ENGINE_KEY = "db_engine"
_DB_SESSION_KEY = "db_session"

# NOTE: Strict DI: No module-level singleton caches allowed. All state must be managed via DI or explicit arguments.


def db_engine_factory(config: DatabaseConfig) -> AsyncEngine:
    """
    Strict DI: Factory for creating a database engine from config.
    Args:
        config: Database configuration object
    Returns:
        AsyncEngine: The SQLAlchemy async engine instance.
    """
    if config.DB_ASYNC_DRIVER.startswith("sqlite"):
        dsn = f"{config.DB_ASYNC_DRIVER}:///" + config.DB_NAME
    else:
        dsn = f"{config.DB_ASYNC_DRIVER}://{config.DB_USER}:{config.DB_USER_PW}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    return create_async_engine(dsn, pool_size=5)


def db_session_factory(engine: AsyncEngine) -> AsyncSession:
    """
    Strict DI: Factory for creating an AsyncSession from an engine.
    Args:
        engine: AsyncEngine instance
    Returns:
        AsyncSession: New async session
    """
    SessionLocal = sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession
    )
    return SessionLocal()


def register_database_services(services: ServiceCollection, config: DatabaseConfig) -> None:
    """
    Strict DI: Register db_engine and db_session providers with the DI container.
    Args:
        services: The DI service collection
        config: The database configuration dictionary
    Call this during application or test setup.
    """
    engine = db_engine_factory(config)
    services.add_instance(AsyncEngine, engine)
    services.add_service(
        AsyncSession,
        lambda: db_session_factory(engine),
        scope=ServiceScope.TRANSIENT
    )
