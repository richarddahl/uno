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
        **context: Any,
    ) -> None:
        """Initialize a configuration error.

        Args:
            message: Human-readable error message
            code: Error code without prefix (will be prefixed automatically)
            severity: How severe this error is
            **context: Additional context information
        """
        super().__init__(
            message=message,
            code=f"CONFIG_{code}" if code else "CONFIG_ERROR",
            category=ErrorCategory.CONFIG,
            severity=severity,
            **context,
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
        ctx = context.copy()
        if config_key:
            ctx["config_key"] = config_key
        if config_value is not None:
            ctx["config_value"] = str(config_value)

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
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

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            file_path=file_path,
            **context,
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
        ctx = context.copy()
        if line_number is not None:
            ctx["line_number"] = line_number

        message = f"Failed to parse configuration file {file_path}: {reason}"
        if line_number is not None:
            message += f" at line {line_number}"

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            file_path=file_path,
            reason=reason,
            **ctx,
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

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            key=key,
            **context,
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
        ctx = context.copy()
        if environment:
            ctx["environment"] = environment

        super().__init__(
            message=message,
            code=code,
            severity=ErrorSeverity.ERROR,
            **ctx,
        )
