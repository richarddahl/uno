# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""SQL emitter implementations.

This package provides concrete implementations of SQL emitters for
common database operations.
"""

from uno.sql.emitters.grants import AlterGrants
from uno.sql.emitters.table import TableMergeFunction
from uno.sql.emitters.triggers import InsertMetaRecordTrigger, RecordUserAuditFunction
from uno.sql.emitters.vector import VectorIntegrationEmitter, VectorSQLEmitter

__all__ = [
    "AlterGrants",
    "InsertMetaRecordTrigger",
    "RecordUserAuditFunction",
    "TableMergeFunction",
    "VectorIntegrationEmitter",
    "VectorSQLEmitter",
]
