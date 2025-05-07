# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""SQL emitter implementations.

This package provides concrete implementations of SQL emitters for
common database operations.
"""

from uno.infrastructure.sql.emitters.grants import AlterGrants
from .trigger_emitter import CreateTriggerEmitter, DropTriggerEmitter
from .function_emitter import CreateFunctionEmitter, DropFunctionEmitter

__all__ = [
    "CreateTriggerEmitter",
    "DropTriggerEmitter",
    "CreateFunctionEmitter",
    "DropFunctionEmitter",
    "AlterGrants",
]
from uno.infrastructure.sql.emitters.table import TableMergeFunction
from uno.infrastructure.sql.emitters.triggers import (
    InsertMetaRecordTrigger,
    RecordUserAuditFunction,
)
from uno.infrastructure.sql.emitters.vector import (
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
