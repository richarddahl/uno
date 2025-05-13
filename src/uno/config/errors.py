# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Configuration-specific error classes for the Uno framework.

This module defines errors related to configuration operations, including
file handling, parsing, validation, and environment issues.
"""

from __future__ import annotations

from typing import Any

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError

# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigError(UnoError):
    """Base class for all configuration-related errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a configuration error.

        Args:
            message: Human-readable error message
            code: Error code without prefix (will be prefixed automatically)
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys (will be merged with context)
        """
        # Combine explicit context dict with any additional kwargs
        full_context = context or {}
        full_context.update(kwargs)

        super().__init__(
            message=message,
            code=f"CONFIG_{code}" if code else "CONFIG_ERROR",
            category=ErrorCategory.CONFIG,
            severity=severity,
            context=full_context,
        )


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_value: Any | None = None,
        code: str | None = "VALIDATION_ERROR",
        **context: Any,
    ) -> None:
        ctx = {}
        if config_key:
            ctx["config_key"] = config_key
        if config_value is not None:
            ctx["config_value"] = str(config_value)
        # Add any additional context
        ctx.update(context)

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            context=ctx,
        )


class ConfigFileNotFoundError(ConfigError):
    """Raised when a configuration file is not found."""

    def __init__(
        self,
        file_path: str,
        message: str | None = None,
        code: str | None = "FILE_NOT_FOUND",
        **context: Any,
    ) -> None:
        message = message or f"Configuration file not found: {file_path}"

        ctx = {"file_path": file_path}
        ctx.update(context)

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            context=ctx,
        )


class ConfigParseError(ConfigError):
    """Raised when parsing a configuration file fails."""

    def __init__(
        self,
        file_path: str,
        reason: str,
        line_number: int | None = None,
        code: str | None = "PARSE_ERROR",
        **context: Any,
    ) -> None:
        ctx = {
            "file_path": file_path,
            "reason": reason,
        }
        if line_number is not None:
            ctx["line_number"] = line_number
        # Add any additional context
        ctx.update(context)

        message = f"Failed to parse configuration file {file_path}: {reason}"
        if line_number is not None:
            message += f" at line {line_number}"

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            context=ctx,
        )


class ConfigMissingKeyError(ConfigError):
    """Raised when a required configuration key is missing."""

    def __init__(
        self,
        key: str,
        message: str | None = None,
        code: str | None = "MISSING_KEY",
        **context: Any,
    ) -> None:
        message = message or f"Required configuration key missing: {key}"

        ctx = {"key": key}
        ctx.update(context)

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            context=ctx,
        )


class ConfigEnvironmentError(ConfigError):
    """Raised when there's an issue with the environment configuration."""

    def __init__(
        self,
        message: str,
        environment: str | None = None,
        code: str | None = "ENVIRONMENT_ERROR",
        **context: Any,
    ) -> None:
        ctx = {}
        if environment:
            ctx["environment"] = environment
        # Add any additional context
        ctx.update(context)

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            context=ctx,
        )


class SecureValueError(ConfigError):
    """Base class for secure value related errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **context: Any,
    ) -> None:
        """Initialize a secure value error.

        Args:
            message: Human-readable error message
            code: Error code without prefix
            severity: ErrorSeverity for the error (default: ERROR)
            **context: Additional context information
        """
        super().__init__(
            message=message,
            code=f"SECURE_{code}" if code else "SECURE_ERROR",
            severity=severity,
            context=context,
        )
