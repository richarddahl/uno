"""
Centralized DI-based database provider for Uno.
Supports Postgres, in-memory, and file-based backends via uno.core.config.
"""
from typing import Any
from uno.core.config import get_config
from uno.core.di import ServiceCollection, ServiceProvider, get_service_provider
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

_DB_ENGINE_KEY = "db_engine"
_DB_SESSION_KEY = "db_session"

# Singleton cache for engines
_engines: dict[str, AsyncEngine] = {}
_sessions: dict[str, sessionmaker] = {}

def _get_db_config() -> dict[str, Any]:
    # Example config keys: DB_BACKEND, DB_DSN, DB_POOL_SIZE, etc.
    return {
        "backend": get_config("DB_BACKEND", default="postgres"),
        "dsn": get_config("DB_DSN", default="postgresql+asyncpg://postgres:postgres@localhost:5432/uno"),
        "pool_size": int(get_config("DB_POOL_SIZE", default="5")),
    }

def get_db_engine() -> AsyncEngine:
    cfg = _get_db_config()
    key = f"{cfg['backend']}:{cfg['dsn']}"
    if key not in _engines:
        if cfg["backend"] == "postgres":
            engine = create_async_engine(cfg["dsn"], pool_size=cfg["pool_size"])
        elif cfg["backend"] == "memory":
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        elif cfg["backend"] == "file":
            db_path = get_config("DB_FILE_PATH", default="uno.db")
            engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        else:
            raise ValueError(f"Unsupported DB_BACKEND: {cfg['backend']}")
        _engines[key] = engine
    return _engines[key]

def get_db_session() -> AsyncSession:
    cfg = _get_db_config()
    key = f"{cfg['backend']}:{cfg['dsn']}"
    if key not in _sessions:
        engine = get_db_engine()
        _sessions[key] = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return _sessions[key]()


def register_database_services(services: ServiceCollection) -> None:
    """
    Register db_engine and db_session providers with the DI container.
    Call this during application or test setup.
    """
    services.add_instance(_DB_ENGINE_KEY, get_db_engine)
    services.add_instance(_DB_SESSION_KEY, get_db_session)
