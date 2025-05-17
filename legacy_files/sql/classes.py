# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Backwards compatibility module for SQL classes.

This module re-exports classes from the new modular structure to maintain
backward compatibility. New code should import directly from the appropriate
modules.
"""

import warnings

from uno.persistance.sql.builders import SQLFunctionBuilder, SQLTriggerBuilder
from uno.persistance.sql.config import SQLConfig
from uno.persistance.sql.emitter import SQLEmitter, SQLExecutor, SQLGenerator
from uno.persistance.sql.observers import LoggingSQLObserver, SQLObserver

# Re-export from new modular structure
from uno.persistance.sql.registry import SQLConfigRegistry
from uno.persistance.sql.statement import SQLStatement, SQLStatementType

# Show deprecation warning
warnings.warn(
    "Importing from uno.persistence.sql.classes is deprecated. "
    "Import from the appropriate modules instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "LoggingSQLObserver",
    "SQLConfig",
    "SQLConfigRegistry",
    "SQLEmitter",
    "SQLExecutor",
    "SQLFunctionBuilder",
    "SQLGenerator",
    "SQLObserver",
    "SQLStatement",
    "SQLStatementType",
    "SQLTriggerBuilder",
]
