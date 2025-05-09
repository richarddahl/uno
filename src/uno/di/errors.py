"""
Error classes for the Uno DI system.

This module contains specialized error classes for the dependency injection system,
providing detailed error messages and context for DI-related failures.
"""

from __future__ import annotations

from typing import Any, Final, Optional, Type, TypeVar

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError

# Prefix for all DI error codes
ERROR_CODE_PREFIX: Final[str] = "DI"


class DIError(UnoError):
    """Base class for all DI-related errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **context: Any,
    ) -> None:
        """Initialize a DI error.

        Args:
            message: Human-readable error message
            error_code: Error code without prefix (will be prefixed with DI_)
            severity: How severe this error is
            **context: Additional context information
        """
        super().__init__(
            message=message,
            error_code=(
                f"{ERROR_CODE_PREFIX}_{error_code}"
                if error_code
                else f"{ERROR_CODE_PREFIX}_ERROR"
            ),
            category=ErrorCategory.DI,
            severity=severity,
            **context,
        )


class ServiceCreationError(DIError):
    """Raised when a service cannot be created."""

    def __init__(self, interface: Type[Any], error: Exception, **context: Any) -> None:
        """Initialize a service creation error.

        Args:
            interface: The service interface that failed to create
            error: The original exception that caused the failure
            **context: Additional context information
        """
        details = {
            "interface": interface.__name__,
            "error_type": type(error).__name__,
            **context,
        }
        super().__init__(
            message=f"Failed to create service {interface.__name__}: {error}",
            error_code="SERVICE_CREATION",
            **details,
        )
        self.__cause__ = error


class TypeMismatchError(DIError):
    """Raised when a service instance doesn't match its expected interface."""

    def __init__(
        self, interface: Type[Any], actual_type: Type[Any], **context: Any
    ) -> None:
        """Initialize a type mismatch error.

        Args:
            interface: The expected interface type
            actual_type: The actual type provided
            **context: Additional context information
        """
        details = {
            "expected_type": interface.__name__,
            "actual_type": actual_type.__name__,
            **context,
        }
        super().__init__(
            message=f"Expected {interface.__name__}, got {actual_type.__name__}",
            error_code="TYPE_MISMATCH",
            **details,
        )


class ServiceNotRegisteredError(DIError):
    """Raised when trying to resolve a service that hasn't been registered."""

    def __init__(self, interface: Type[Any], **context: Any) -> None:
        """Initialize a service not registered error.

        Args:
            interface: The service interface that wasn't registered
            **context: Additional context information
        """
        super().__init__(
            message=f"Service {interface.__name__} is not registered",
            error_code="SERVICE_NOT_REGISTERED",
            interface_name=interface.__name__,
            **context,
        )


class DuplicateRegistrationError(DIError):
    """Raised when trying to register a service that is already registered."""

    def __init__(self, interface: Type[Any], **context: Any) -> None:
        """Initialize a duplicate registration error.

        Args:
            interface: The service interface that was already registered
            **context: Additional context information
        """
        super().__init__(
            message=f"Service {interface.__name__} is already registered",
            error_code="DUPLICATE_REGISTRATION",
            interface_name=interface.__name__,
            **context,
        )


class SyncInAsyncContextError(DIError):
    """Raised when a sync DI API is called from an async context (event loop running)."""

    def __init__(self, method: str, **context: Any) -> None:
        """Initialize a sync in async context error.

        Args:
            method: The method name that was incorrectly called
            **context: Additional context information
        """
        super().__init__(
            message=f"{method} cannot be called from an async context. Use the async version instead.",
            error_code="SYNC_IN_ASYNC_CONTEXT",
            method=method,
            **context,
        )


class ScopeError(DIError):
    """Raised when there's an error related to scopes."""

    def __init__(
        self, message: str, error_code: Optional[str] = None, **context: Any
    ) -> None:
        """Initialize a scope error.

        Args:
            message: Human-readable error message
            error_code: Error code without prefix
            **context: Additional context information
        """
        super().__init__(
            message=message, error_code=error_code or "SCOPE_ERROR", **context
        )

    @classmethod
    def outside_scope(cls, interface: Type[Any]) -> ScopeError:
        """Create a scope error for resolving a scoped service outside a scope.

        Args:
            interface: The scoped service interface

        Returns:
            A ScopeError with appropriate context
        """
        error = cls(
            f"Cannot resolve scoped service {interface.__name__} outside a scope",
            error_code="OUTSIDE_SCOPE",
        )
        error.add_context("interface_name", interface.__name__)
        return error

    @classmethod
    def container_disposed(cls) -> ScopeError:
        """Create a scope error for operations on a disposed container.

        Returns:
            A ScopeError with appropriate context
        """
        return cls("Container has been disposed", error_code="CONTAINER_DISPOSED")

    @classmethod
    def scope_disposed(cls) -> ScopeError:
        """Create a scope error for operations on a disposed scope.

        Returns:
            A ScopeError with appropriate context
        """
        return cls("Scope has been disposed", error_code="SCOPE_DISPOSED")
