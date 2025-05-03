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

from uno.infrastructure.sql.builders import SQLFunctionBuilder, SQLTriggerBuilder
from uno.infrastructure.sql.config import SQLConfig
from uno.infrastructure.sql.emitter import SQLEmitter, SQLExecutor, SQLGenerator
from uno.infrastructure.sql.observers import LoggingSQLObserver, SQLObserver

# Re-export from new modular structure
from uno.infrastructure.sql.registry import SQLConfigRegistry
from uno.infrastructure.sql.statement import SQLStatement, SQLStatementType

# Show deprecation warning
warnings.warn(
    "Importing from uno.sql.classes is deprecated. "
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
