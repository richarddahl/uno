# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Error definitions for the SQL module.

This module defines error types, error codes, and error catalog entries
specific to the SQL functionality.
"""

from typing import Any



class UnoError(BaseException):
    """Base class for all Uno framework errors."""

    def __init__(self, message: str, error_code: str, **context: Any) -> None:
        """Initialize a Uno error."""
        super().__init__(message)
        self.error_code = error_code
        self.context = context


# SQL error codes
class SQLErrorCode:
    """SQL-specific error codes."""

    # SQL statement errors
    SQL_STATEMENT_INVALID = "SQL-0001"
    SQL_STATEMENT_EXECUTION_FAILED = "SQL-0002"
    SQL_STATEMENT_SYNTAX_ERROR = "SQL-0003"

    # SQL emitter errors
    SQL_EMITTER_ERROR = "SQL-0101"
    SQL_EMITTER_INVALID_CONFIG = "SQL-0102"
    SQL_EMITTER_ALREADY_APPLIED = "SQL-0103"

    # SQL registry errors
    SQL_REGISTRY_CLASS_NOT_FOUND = "SQL-0201"
    SQL_REGISTRY_CLASS_ALREADY_EXISTS = "SQL-0202"
    SQL_REGISTRY_INITIALIZATION_FAILED = "SQL-0203"

    # SQL configuration errors
    SQL_CONFIG_ERROR = "SQL-0301"
    SQL_CONFIG_INVALID = "SQL-0302"
    SQL_CONFIG_EXTENSION_MISSING = "SQL-0303"

    # SQL connection errors
    SQL_CONNECTION_ERROR = "SQL-0401"
    SQL_CONNECTION_TIMEOUT = "SQL-0402"
    SQL_CONNECTION_FAILED = "SQL-0403"

    # General errors
    SQL_OPERATION_FAILED = "SQL-0901"


# SQL statement errors
class SQLStatementError(UnoError):
    """Error raised when there is an issue with a SQL statement."""

    def __init__(
        self,
        reason: str,
        statement: str | None = None,
        message: str | None = None,
        **context: Any,
    ):
        ctx = context.copy()
        if statement:
            ctx["statement"] = statement

        message = message or f"SQL statement error: {reason}"
        super().__init__(
            message=message,
            error_code=SQLErrorCode.SQL_STATEMENT_INVALID,
            reason=reason,
            **ctx,
        )


class SQLExecutionError(UnoError):
    """Error raised when SQL execution fails."""

    def __init__(
        self,
        reason: str,
        statement_type: str | None = None,
        message: str | None = None,
        **context: Any,
    ):
        ctx = context.copy()
        if statement_type:
            ctx["statement_type"] = statement_type

        message = message or f"SQL execution failed: {reason}"
        super().__init__(
            message=message,
            error_code=SQLErrorCode.SQL_STATEMENT_EXECUTION_FAILED,
            reason=reason,
            **ctx,
        )


class SQLSyntaxError(UnoError):
    """Error raised when a SQL statement has a syntax error."""

    def __init__(
        self,
        reason: str,
        statement: str | None = None,
        message: str | None = None,
        **context: Any,
    ):
        ctx = context.copy()
        if statement:
            ctx["statement"] = statement

        message = message or f"SQL syntax error: {reason}"
        super().__init__(
            message=message,
            error_code=SQLErrorCode.SQL_STATEMENT_SYNTAX_ERROR,
            reason=reason,
            **ctx,
        )


# SQL emitter errors
class SQLEmitterError(UnoError):
    """Error raised when there is an issue with a SQL emitter."""

    def __init__(
        self,
        reason: str,
        emitter: str | None = None,
        message: str | None = None,
        **context: Any,
    ):
        ctx = context.copy()
        if emitter:
            ctx["emitter"] = emitter

        message = message or f"SQL emitter error: {reason}"
        super().__init__(
            message=message,
            error_code=SQLErrorCode.SQL_EMITTER_ERROR,
            reason=reason,
            **ctx,
        )


class SQLEmitterInvalidConfigError(UnoError):
    """Error raised when a SQL emitter has an invalid configuration."""

    def __init__(
        self,
        reason: str,
        emitter: str | None = None,
        config_name: str | None = None,
        message: str | None = None,
        **context: Any,
    ):
        ctx = context.copy()
        if emitter:
            ctx["emitter"] = emitter
        if config_name:
            ctx["config_name"] = config_name

        message = message or f"Invalid SQL emitter configuration: {reason}"
        super().__init__(
            message=message,
            error_code=SQLErrorCode.SQL_EMITTER_INVALID_CONFIG,
            reason=reason,
            **ctx,
        )


# SQL registry errors
class SQLRegistryClassNotFoundError(UnoError):
    """Error raised when a SQL registry class is not found."""

    def __init__(self, class_name: str, message: str | None = None, **context: Any):
        message = message or f"SQL registry class '{class_name}' not found"
        super().__init__(
            message=message,
            error_code=SQLErrorCode.SQL_REGISTRY_CLASS_NOT_FOUND,
            class_name=class_name,
            **context,
        )


class SQLRegistryClassAlreadyExistsError(UnoError):
    """Error raised when a SQL registry class already exists."""

    def __init__(self, class_name: str, message: str | None = None, **context: Any):
        message = message or f"SQL registry class '{class_name}' already exists"
        super().__init__(
            message=message,
            error_code=SQLErrorCode.SQL_REGISTRY_CLASS_ALREADY_EXISTS,
            class_name=class_name,
            **context,
        )


# SQL configuration errors
class SQLConfigError(UnoError):
    """Error raised when there is an issue with SQL configuration."""

    def __init__(
        self,
        reason: str,
        config_name: str | None = None,
        message: str | None = None,
        **context: Any,
    ):
        ctx = context.copy()
        if config_name:
            ctx["config_name"] = config_name

        message = message or f"SQL configuration error: {reason}"
        super().__init__(
            message=message,
            error_code=SQLErrorCode.SQL_CONFIG_ERROR,
            reason=reason,
            **ctx,
        )


class SQLConfigInvalidError(UnoError):
    """Error raised when SQL configuration is invalid."""

    def __init__(
        self,
        reason: str,
        config_name: str | None = None,
        message: str | None = None,
        **context: Any,
    ):
        ctx = context.copy()
        if config_name:
            ctx["config_name"] = config_name

        message = message or f"Invalid SQL configuration: {reason}"
        super().__init__(
            message=message,
            error_code=SQLErrorCode.SQL_CONFIG_INVALID,
            reason=reason,
            **ctx,
        )


