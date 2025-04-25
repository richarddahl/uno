# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""SQL generation and execution for database operations.

This package provides tools for generating and executing SQL statements
for database operations including creating tables, functions, triggers,
and other database objects.
"""

# Core SQL generation and execution components
# SQL builders for functions and triggers
from uno.sql.builders.function import SQLFunctionBuilder
from uno.sql.builders.trigger import SQLTriggerBuilder
from uno.sql.config import SQLConfig
from uno.sql.emitter import SQLEmitter, SQLExecutor, SQLGenerator

# Common SQL emitters
from uno.sql.emitters import (
    AlterGrants,
    InsertMetaRecordTrigger,
    RecordUserAuditFunction,
)

# Error types
from uno.sql.errors import (
    SQLConfigError,
    SQLConfigInvalidError,
    SQLEmitterError,
    SQLEmitterInvalidConfigError,
    SQLErrorCode,
    SQLExecutionError,
    SQLRegistryClassAlreadyExistsError,
    SQLRegistryClassNotFoundError,
    SQLStatementError,
    SQLSyntaxError,
    register_sql_errors,
)
from uno.sql.observers import LoggingSQLObserver, SQLObserver
from uno.sql.registry import SQLConfigRegistry
from uno.sql.statement import SQLStatement, SQLStatementType

# Register SQL errors
register_sql_errors()

__all__ = [
    # Legacy components
    "SQLConfigRegistry",
    "SQLConfig",
    "SQLEmitter",
    "SQLGenerator",
    "SQLExecutor",
    "SQLStatement",
    "SQLStatementType",
    "SQLObserver",
    "LoggingSQLObserver",
    "SQLFunctionBuilder",
    "SQLTriggerBuilder",
    "AlterGrants",
    "RecordUserAuditFunction",
    "InsertMetaRecordTrigger",
    # Error types
    "SQLErrorCode",
    "SQLStatementError",
    "SQLExecutionError",
    "SQLSyntaxError",
    "SQLEmitterError",
    "SQLEmitterInvalidConfigError",
    "SQLRegistryClassNotFoundError",
    "SQLRegistryClassAlreadyExistsError",
    "SQLConfigError",
    "SQLConfigInvalidError",
    # Domain entities
    "SQLStatementId",
    "SQLEmitterId",
    "SQLConfigId",
    "SQLTransactionIsolationLevel",
    "SQLFunctionVolatility",
    "SQLFunctionLanguage",
    "SQLFunction",
    "SQLTrigger",
    "DatabaseConnectionInfo",
    "SQLConfiguration",
    # Domain repositories
    "SQLStatementRepositoryProtocol",
    "SQLEmitterRepositoryProtocol",
    "SQLConfigurationRepositoryProtocol",
    "SQLFunctionRepositoryProtocol",
    "SQLTriggerRepositoryProtocol",
    "SQLConnectionManagerProtocol",
    "InMemorySQLStatementRepository",
    "InMemorySQLEmitterRepository",
    "InMemorySQLConfigurationRepository",
    "InMemorySQLFunctionRepository",
    "InMemorySQLTriggerRepository",
    # Domain services
    "SQLStatementServiceProtocol",
    "SQLEmitterServiceProtocol",
    "SQLConfigurationServiceProtocol",
    "SQLFunctionServiceProtocol",
    "SQLTriggerServiceProtocol",
    "SQLConnectionServiceProtocol",
    "SQLStatementService",
    "SQLEmitterService",
    "SQLConfigurationService",
    "SQLFunctionService",
    "SQLTriggerService",
    "SQLConnectionService",
    # Domain provider
    "configure_sql_dependencies",
    "get_sql_statement_service",
    "get_sql_emitter_service",
    "get_sql_configuration_service",
    "get_sql_function_service",
    "get_sql_trigger_service",
    "get_sql_connection_service",
    "create_sql_statement",
    "execute_sql_statement",
    "create_sql_function",
    "create_sql_trigger",
    "create_database_connection",
    "execute_sql",
    "get_sql_dependencies",
]
