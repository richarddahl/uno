# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Database-specific error classes for the Uno framework.

This module defines errors related to database operations, including
connection issues, query failures, migrations, and constraints.
"""

from __future__ import annotations

import re
from typing import Any

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError

# =============================================================================
# Database Errors
# =============================================================================


class DBError(UnoError):
    """Base class for all database-related errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **context: Any,
    ) -> None:
        """Initialize a database error.

        Args:
            message: Human-readable error message
            code: Error code without prefix (will be prefixed automatically)
            severity: How severe this error is
            **context: Additional context information
        """
        super().__init__(
            message=message,
            code=f"DB_{code}" if code else "DB_ERROR",
            category=ErrorCategory.DB,
            severity=severity,
            **context,
        )


class DBConnectionError(DBError):
    """Raised when a database connection fails."""

    def __init__(
        self,
        message: str = "Failed to connect to database",
        connection_string: str | None = None,
        code: str | None = "CONNECTION_ERROR",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if connection_string:
            # Sanitize connection string to remove credentials
            sanitized = self._sanitize_connection_string(connection_string)
            ctx["connection_string"] = sanitized

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )

    @staticmethod
    def _sanitize_connection_string(conn_str: str) -> str:
        """Sanitize a connection string to remove sensitive information."""
        # Basic implementation - in real code, this would be more sophisticated
        return re.sub(
            r"password=([^;]*)", "password=***", conn_str, flags=re.IGNORECASE
        )


class DBQueryError(DBError):
    """Raised when a database query fails."""

    def __init__(
        self,
        message: str,
        query: str | None = None,
        params: dict[str, Any] | None = None,
        code: str | None = "QUERY_ERROR",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if query:
            ctx["query"] = query
        if params:
            # Sanitize params to avoid logging sensitive data
            ctx["params"] = {
                k: "***" if k.lower() in ["password", "secret", "token"] else v
                for k, v in params.items()
            }

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class DBMigrationError(DBError):
    """Raised when a database migration fails."""

    def __init__(
        self,
        message: str,
        migration_version: str | None = None,
        migration_name: str | None = None,
        code: str | None = "MIGRATION_ERROR",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if migration_version:
            ctx["migration_version"] = migration_version
        if migration_name:
            ctx["migration_name"] = migration_name

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class DBConstraintViolationError(DBError):
    """Raised when a database constraint is violated."""

    def __init__(
        self,
        message: str,
        constraint_name: str | None = None,
        table_name: str | None = None,
        code: str | None = "CONSTRAINT_VIOLATION",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if constraint_name:
            ctx["constraint_name"] = constraint_name
        if table_name:
            ctx["table_name"] = table_name

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )


class DBDeadlockError(DBError):
    """Raised when a database deadlock is detected."""

    def __init__(
        self,
        message: str = "Database deadlock detected",
        transaction_id: str | None = None,
        code: str | None = "DEADLOCK",
        **context: Any,
    ) -> None:
        ctx = context.copy()
        if transaction_id:
            ctx["transaction_id"] = transaction_id

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )
