"""
Error classes for the uno DI system.

This module contains all error classes used by the DI system, including their error codes.
"""

from typing import Final

from uno.errors.base import UnoError

__all__ = [
    "DIError",
    "DuplicateRegistrationError",
    "ScopeError",
    "ServiceNotRegisteredError",
    "SyncInAsyncContextError",
    "TypeMismatchError",
]


ERROR_CODE_PREFIX: Final[str] = "DI"


class DIError(UnoError):
    """Base class for all DI-related errors."""

    def __init__(self, message: str, error_code: str | None = None) -> None:
        """Initialize a DI error."""
        super().__init__(message, error_code or f"{ERROR_CODE_PREFIX}_ERROR")


class ServiceCreationError(DIError):
    """Raised when a service cannot be created."""

    def __init__(self, interface: type, error: Exception) -> None:
        """Initialize a service creation error."""
        super().__init__(
            f"Failed to create service {interface.__name__}: {error}",
            f"{ERROR_CODE_PREFIX}_SERVICE_CREATION",
        )


class TypeMismatchError(DIError):
    """Raised when a service instance doesn't match its expected interface."""

    def __init__(self, interface: type, actual_type: type) -> None:
        """Initialize a type mismatch error."""
        super().__init__(
            f"Expected {interface.__name__}, got {actual_type.__name__}",
            f"{ERROR_CODE_PREFIX}_TYPE_MISMATCH",
        )


class ServiceNotRegisteredError(DIError):
    """Raised when trying to resolve a service that hasn't been registered."""

    def __init__(self, interface: type) -> None:
        """Initialize a service not registered error."""
        super().__init__(
            f"Service {interface.__name__} is not registered",
            f"{ERROR_CODE_PREFIX}_SERVICE_NOT_REGISTERED",
        )


class DuplicateRegistrationError(DIError):
    """Raised when trying to register a service that is already registered."""

    def __init__(self, interface: type) -> None:
        """Initialize a duplicate registration error."""
        super().__init__(
            f"Service {interface.__name__} is already registered",
            f"{ERROR_CODE_PREFIX}_DUPLICATE_REGISTRATION",
        )


class SyncInAsyncContextError(DIError):
    """Raised when a sync DI API is called from an async context (event loop running)."""

    def __init__(self, method: str) -> None:
        super().__init__(
            f"{method} cannot be called from an async context. Use the async version instead.",
            f"{ERROR_CODE_PREFIX}_SYNC_IN_ASYNC_CONTEXT",
        )


class ScopeError(DIError):
    """Raised when there's an error related to scopes."""

    def __init__(self, message: str) -> None:
        """Initialize a scope error."""
        super().__init__(
            message,
            f"{ERROR_CODE_PREFIX}_SCOPE_ERROR",
        )

    @classmethod
    def outside_scope(cls, interface: type) -> "ScopeError":
        """Create a scope error for resolving a scoped service outside a scope."""
        return cls(
            f"Cannot resolve scoped service {interface.__name__} outside a scope"
        )

    @classmethod
    def already_in_scope(cls) -> "ScopeError":
        """Create a scope error for creating a scope when already in one."""
        return cls("Cannot create a scope when already in one")

    @classmethod
    def not_in_scope(cls) -> "ScopeError":
        """Create a scope error for resolving a scoped service when not in a scope."""
        return cls("Not in a scope")
