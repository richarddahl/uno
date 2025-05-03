# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""SQL generation and execution for database operations.

This package provides tools for generating and executing SQL statements
for database operations including creating tables, functions, triggers,
and other database objects.
"""

# Core SQL generation and execution components
from uno.infrastructure.sql.registry import SQLConfigRegistry
from uno.infrastructure.sql.config import SQLConfig
from uno.infrastructure.sql.emitter import SQLEmitter, SQLGenerator, SQLExecutor
from uno.infrastructure.sql.statement import SQLStatement, SQLStatementType
from uno.infrastructure.sql.observers import SQLObserver, LoggingSQLObserver

# SQL builders for functions and triggers
from uno.infrastructure.sql.builders.function import SQLFunctionBuilder
from uno.infrastructure.sql.builders.trigger import SQLTriggerBuilder

# Common SQL emitters
from uno.infrastructure.sql.emitters import (
    AlterGrants,
    RecordUserAuditFunction,
    InsertMetaRecordTrigger,
)

# Error types
from uno.infrastructure.sql.errors import (
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
    register_sql_errors,
)

# Register SQL errors
register_sql_errors()

__all__ = [
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
]
