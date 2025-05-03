"""
Service implementations for SQL generation (migrated from legacy).

This module provides services for creating and managing SQL emitters
through dependency injection, as part of Uno's infrastructure layer.
"""

import logging
from typing import Any, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from uno.infrastructure.sql.engine import SyncEngineFactory
    from uno.infrastructure.sql.interfaces import (
        ConnectionConfigProtocol,
        SQLEmitterProtocol,
    )
    from sqlalchemy.engine import Connection
    from uno.core.interfaces import (
        DBManagerProtocol,
        ConfigProtocol,
        SQLEmitterFactoryProtocol,
    )
    from uno.infrastructure.sql.emitters.database import (
        CreateRolesAndDatabase,
        CreateSchemasAndExtensions,
        RevokeAndGrantPrivilegesAndSetSearchPaths,
        DropDatabaseAndRoles,
        CreatePGULID,
        CreateTokenSecret,
    )
    from uno.infrastructure.sql.emitters.table import InsertMetaRecordFunction
    from uno.infrastructure.sql.emitters.triggers import RecordUserAuditFunction
    from uno.infrastructure.sql.statement import SQLStatement
    from uno.core.interfaces import SQLEmitterFactoryProtocol

from uno.core.interfaces import SQLEmitterFactoryProtocol
from uno.core.interfaces import ConfigProtocol
from uno.infrastructure.sql.emitter import SQLEmitter
from uno.infrastructure.sql.statement import SQLStatement
from uno.infrastructure.sql.emitters.database import (
    CreateRolesAndDatabase,
    CreateSchemasAndExtensions,
    RevokeAndGrantPrivilegesAndSetSearchPaths,
    DropDatabaseAndRoles,
    CreatePGULID,
    CreateTokenSecret,
)
from uno.infrastructure.sql.emitters.table import InsertMetaRecordFunction
from uno.infrastructure.sql.emitters.triggers import RecordUserAuditFunction
from uno.core.interfaces import DBManagerProtocol

# Use canonical ConfigProtocol import


class SQLEmitterFactoryService(SQLEmitterFactoryProtocol):
    """
    Factory service for creating SQL emitters.
    """

    def __init__(self, config: ConfigProtocol, logger: "logging.Logger | None" = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self._emitter_registry: dict[str, type["SQLEmitterProtocol"]] = {}

    def register_emitter(
        self, name: str, emitter_class: type["SQLEmitterProtocol"]
    ) -> None:
        self.logger.debug(f"Registering SQL emitter: {name}")
        self._emitter_registry[name] = emitter_class

    def get_emitter(
        self, name: str, connection_config: object = None, **kwargs
    ) -> "SQLEmitterProtocol":
        emitter_class = self._emitter_registry.get(name)
        if emitter_class is None:
            raise ValueError(f"No emitter registered with name: {name}")
        return emitter_class(connection_config=connection_config, **kwargs)

    def create_emitter_instance(
        self,
        emitter_class: type["SQLEmitterProtocol"],
        connection_config: object = None,
        **kwargs,
    ) -> "SQLEmitterProtocol":
        if connection_config is None:
            connection_config = self.config.get_value("DB_CONNECTION_CONFIG")
        emitter = emitter_class(
            connection_config=connection_config, logger=self.logger, **kwargs
        )
        return emitter

    def register_core_emitters(self) -> None:
        self.register_emitter("create_roles_and_database", CreateRolesAndDatabase)
        self.register_emitter(
            "create_schemas_and_extensions", CreateSchemasAndExtensions
        )
        self.register_emitter(
            "revoke_and_grant_privileges", RevokeAndGrantPrivilegesAndSetSearchPaths
        )
        self.register_emitter("drop_database_and_roles", DropDatabaseAndRoles)
        self.register_emitter("create_pgulid", CreatePGULID)
        self.register_emitter("create_token_secret", CreateTokenSecret)
        self.register_emitter("insert_meta_record", InsertMetaRecordFunction)
        self.register_emitter("record_user_audit", RecordUserAuditFunction)

    def execute_emitter(
        self, emitter: SQLEmitter, db_manager: DBManagerProtocol, dry_run: bool = False
    ) -> list[SQLStatement] | None:
        if dry_run:
            return emitter.generate_sql()
        db_manager.execute_from_emitter(emitter)
        return None
