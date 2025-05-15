# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""SQL emitter implementations.

This package provides concrete implementations of SQL emitters for
common database operations.
"""

from uno.persistance.sql.emitters.grants import AlterGrants
from .trigger_emitter import CreateTriggerEmitter, DropTriggerEmitter
from .function_emitter import CreateFunctionEmitter, DropFunctionEmitter

__all__ = [
    "CreateTriggerEmitter",
    "DropTriggerEmitter",
    "CreateFunctionEmitter",
    "DropFunctionEmitter",
    "AlterGrants",
]
from uno.persistance.sql.emitters.table import TableMergeFunction
from uno.persistance.sql.emitters.triggers import (
    InsertMetaRecordTrigger,
    RecordUserAuditFunction,
)
from uno.persistance.sql.emitters.vector import (
    VectorIntegrationEmitter,
    VectorSQLEmitter,
)

__all__ = [
    "AlterGrants",
    "InsertMetaRecordTrigger",
    "RecordUserAuditFunction",
    "TableMergeFunction",
    "VectorIntegrationEmitter",
    "VectorSQLEmitter",
]
