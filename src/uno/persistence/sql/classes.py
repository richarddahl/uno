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

from uno.persistence.sql.builders import SQLFunctionBuilder, SQLTriggerBuilder
from uno.persistence.sql.config import SQLConfig
from uno.persistence.sql.emitter import SQLEmitter, SQLExecutor, SQLGenerator
from uno.persistence.sql.observers import LoggingSQLObserver, SQLObserver

# Re-export from new modular structure
from uno.persistence.sql.registry import SQLConfigRegistry
from uno.persistence.sql.statement import SQLStatement, SQLStatementType

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
