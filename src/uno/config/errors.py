# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Configuration-specific error classes for the Uno framework.

This module defines errors related to configuration operations, including
file handling, parsing, validation, and environment issues.
"""

from __future__ import annotations

from typing import Any, Final

from uno.errors.base import ErrorCode, ErrorCategory, ErrorSeverity, UnoError

# Define error category and codes
CONFIG = ErrorCategory("CONFIG")
CFG_ERROR: Final = ErrorCode("CFG_ERROR", CONFIG)
CFG_VALIDATION: Final = ErrorCode("CFG_VALIDATION", CONFIG)
CFG_FILE_NOT_FOUND: Final = ErrorCode("CFG_FILE_NOT_FOUND", CONFIG)
CFG_PARSE: Final = ErrorCode("CFG_PARSE", CONFIG)
CFG_MISSING_KEY: Final = ErrorCode("CFG_MISSING_KEY", CONFIG)
CFG_ENVIRONMENT: Final = ErrorCode("CFG_ENVIRONMENT", CONFIG)
CFG_SECURE: Final = ErrorCode("CFG_SECURE", CONFIG)
CFG_SECURE_VALUE: Final = ErrorCode("CFG_SECURE_VALUE", CONFIG)


class ConfigError(UnoError):
    """Base class for all configuration-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = CFG_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a configuration error.

        Args:
            message: Human-readable error message
            code: Error code
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys (will be merged with context)
        """
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_value: Any | None = None,
        code: ErrorCode = CFG_VALIDATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        # Pass specific parameters as kwargs, UnoError will handle merging them
        validation_kwargs = kwargs.copy()
        if config_key:
            validation_kwargs["config_key"] = config_key
        if config_value is not None:
            validation_kwargs["config_value"] = str(config_value)

        super().__init__(
            message=message,
            code=code,
            severity=severity,
            context=context,
            **validation_kwargs,
        )


class ConfigFileNotFoundError(ConfigError):
    """Raised when a configuration file is not found."""

    def __init__(
        self,
        file_path: str,
        message: str | None = None,
        code: ErrorCode = CFG_FILE_NOT_FOUND,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        message = message or f"Configuration file not found: {file_path}"

        super().__init__(
            message=message,
            code=code,
            severity=severity,
            context=context,
            file_path=file_path,
            **kwargs,
        )


class ConfigParseError(ConfigError):
    """Raised when parsing a configuration file fails."""

    def __init__(
        self,
        file_path: str,
        reason: str,
        line_number: int | None = None,
        code: ErrorCode = CFG_PARSE,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        message = f"Failed to parse configuration file {file_path}: {reason}"
        if line_number is not None:
            message += f" at line {line_number}"

        parse_kwargs = kwargs.copy()
        parse_kwargs["file_path"] = file_path
        parse_kwargs["reason"] = reason
        if line_number is not None:
            parse_kwargs["line_number"] = line_number

        super().__init__(
            message=message,
            code=code,
            severity=severity,
            context=context,
            **parse_kwargs,
        )


class ConfigMissingKeyError(ConfigError):
    """Raised when a required configuration key is missing."""

    def __init__(
        self,
        key: str,
        message: str | None = None,
        code: ErrorCode = CFG_MISSING_KEY,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        message = message or f"Required configuration key missing: {key}"

        super().__init__(
            message=message,
            code=code,
            severity=severity,
            context=context,
            key=key,
            **kwargs,
        )


class ConfigEnvironmentError(ConfigError):
    """Raised when there's an issue with the environment configuration."""

    def __init__(
        self,
        message: str,
        environment: str | None = None,
        code: ErrorCode = CFG_ENVIRONMENT,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        env_kwargs = kwargs.copy()
        if environment:
            env_kwargs["environment"] = environment

        super().__init__(
            message=message,
            code=code,
            severity=severity,
            context=context,
            **env_kwargs,
        )


class SecureConfigError(ConfigError):
    """Base class for secure config related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = CFG_SECURE,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


class SecureValueError(SecureConfigError):
    """Error for invalid secure config values."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = CFG_SECURE_VALUE,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a secure value error.

        Args:
            message: Human-readable error message
            code: Error code
            severity: ErrorSeverity for the error (default: ERROR)
            context: Additional context information
            **kwargs: Additional context keys
        """
        super().__init__(
            message=message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )
