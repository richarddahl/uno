# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Backwards compatibility module for SQL classes.

This module re-exports classes from the new modular structure to maintain
backward compatibility. New code should import directly from the appropriate
modules.
"""

import warnings

# Re-export from new modular structure
from uno.infrastructure.sql.registry import SQLConfigRegistry
from uno.infrastructure.sql.config import SQLConfig
from uno.infrastructure.sql.emitter import SQLEmitter, SQLGenerator, SQLExecutor
from uno.infrastructure.sql.statement import SQLStatement, SQLStatementType
from uno.infrastructure.sql.observers import SQLObserver, LoggingSQLObserver
from uno.infrastructure.sql.builders import SQLFunctionBuilder, SQLTriggerBuilder

# Show deprecation warning
warnings.warn(
    "Importing from uno.infrastructure.sql.classes is deprecated. "
    "Import from the appropriate modules instead.",
    DeprecationWarning,
    stacklevel=2,
)

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
]
