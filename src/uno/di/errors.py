"""
Error classes for the uno DI system.

This module contains all error classes used by the DI system, including their error codes.
"""

from typing import Any, Final

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError

__all__ = [
    "DIError",
    "DuplicateRegistrationError",
    "ScopeError",
    "ServiceCreationError",
    "ServiceNotRegisteredError",
    "SyncInAsyncContextError",
    "TypeMismatchError",
]


ERROR_CODE_PREFIX: Final[str] = "DI"


class DIError(UnoError):
    """Base class for all DI-related errors."""

    def __init__(
        self, message: str, error_code: str | None = None, **details: Any
    ) -> None:
        """Initialize a DI error."""
        super().__init__(
            message=message,
            error_code=error_code or f"{ERROR_CODE_PREFIX}_ERROR",
            category=ErrorCategory.DI,
            severity=ErrorSeverity.ERROR,
            **details,
        )


class ServiceCreationError(DIError):
    """Raised when a service cannot be created."""

    def __init__(self, interface: type, error: Exception) -> None:
        """Initialize a service creation error."""
        details = {"interface": interface.__name__, "error_type": type(error).__name__}
        super().__init__(
            message=f"Failed to create service {interface.__name__}: {error}",
            error_code=f"{ERROR_CODE_PREFIX}_SERVICE_CREATION",
            **details,
        )


class TypeMismatchError(DIError):
    """Raised when a service instance doesn't match its expected interface."""

    def __init__(self, interface: type, actual_type: type) -> None:
        """Initialize a type mismatch error."""
        details = {
            "expected_type": interface.__name__,
            "actual_type": actual_type.__name__,
        }
        super().__init__(
            message=f"Expected {interface.__name__}, got {actual_type.__name__}",
            error_code=f"{ERROR_CODE_PREFIX}_TYPE_MISMATCH",
            severity=ErrorSeverity.ERROR,
            **details,
        )


class ServiceNotRegisteredError(DIError):
    """Raised when trying to resolve a service that hasn't been registered."""

    def __init__(self, interface: type) -> None:
        """Initialize a service not registered error."""
        super().__init__(
            message=f"Service {interface.__name__} is not registered",
            error_code=f"{ERROR_CODE_PREFIX}_SERVICE_NOT_REGISTERED",
            interface_name=interface.__name__,
        )


class DuplicateRegistrationError(DIError):
    """Raised when trying to register a service that is already registered."""

    def __init__(self, interface: type) -> None:
        """Initialize a duplicate registration error."""
        super().__init__(
            message=f"Service {interface.__name__} is already registered",
            error_code=f"{ERROR_CODE_PREFIX}_DUPLICATE_REGISTRATION",
            interface_name=interface.__name__,
        )


class SyncInAsyncContextError(DIError):
    """Raised when a sync DI API is called from an async context (event loop running)."""

    def __init__(self, method: str) -> None:
        super().__init__(
            message=f"{method} cannot be called from an async context. Use the async version instead.",
            error_code=f"{ERROR_CODE_PREFIX}_SYNC_IN_ASYNC_CONTEXT",
            method=method,
        )


class ScopeError(DIError):
    """Raised when there's an error related to scopes."""

    def __init__(self, message: str) -> None:
        """Initialize a scope error."""
        super().__init__(
            message=message,
            error_code=f"{ERROR_CODE_PREFIX}_SCOPE_ERROR",
        )

    @classmethod
    def outside_scope(cls, interface: type) -> "ScopeError":
        """Create a scope error for resolving a scoped service outside a scope."""
        error = cls(
            f"Cannot resolve scoped service {interface.__name__} outside a scope"
        )
        error.with_detail("interface_name", interface.__name__)
        return error

    @classmethod
    def already_in_scope(cls) -> "ScopeError":
        """Create a scope error for creating a scope when already in one."""
        return cls("Cannot create a scope when already in one")

    @classmethod
    def not_in_scope(cls) -> "ScopeError":
        """Create a scope error for resolving a scoped service when not in a scope."""
        return cls("Not in a scope")
