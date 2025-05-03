# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Protocols for Uno SQL infrastructure DI/extension points.
"""
from typing import Protocol, Any

class EngineFactoryProtocol(Protocol):
    """Protocol for DI engine factory (sync or async)."""
    def get_engine(self) -> Any: ...

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
    from uno.infrastructure.sql.statement import SQLStatement

class SQLEmitterProtocol(Protocol):
    """
    Protocol for Uno SQL emitters.
    Defines the minimal interface required for DI/type-hinting in factories, registries, and services.
    """
    def generate_sql(self) -> list['SQLStatement']:
        ...

    def emit_sql(self, connection: 'Connection', dry_run: bool = False) -> list['SQLStatement'] | None:
        ...
