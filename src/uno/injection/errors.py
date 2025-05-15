# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Error classes for the Uno dependency injection system.

This module contains specialized error classes for the dependency injection system,
providing detailed error messages and context for DI-related failures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final, TypeVar

from uno.errors.base import ErrorCode, ErrorCategory, ErrorSeverity, UnoError

if TYPE_CHECKING:
    from uno.injection.protocols import ContainerProtocol, ScopeProtocol

T = TypeVar("T")
TContainer = TypeVar("TContainer", bound="ContainerProtocol")
TScope = TypeVar("TScope", bound="ScopeProtocol")

# Define error categories and codes
INJECTION: Final = ErrorCategory("INJECTION")
INJECTION_ERROR: Final = ErrorCode("INJECTION_ERROR", INJECTION)
INJECTION_SERVICE_CREATION: Final = ErrorCode("INJECTION_SERVICE_CREATION", INJECTION)
INJECTION_SERVICE_NOT_FOUND: Final = ErrorCode("INJECTION_SERVICE_NOT_FOUND", INJECTION)
INJECTION_DUPLICATE_REGISTRATION: Final = ErrorCode(
    "INJECTION_DUPLICATE_REGISTRATION", INJECTION
)
INJECTION_CIRCULAR_DEPENDENCY: Final = ErrorCode(
    "INJECTION_CIRCULAR_DEPENDENCY", INJECTION
)
INJECTION_SYNC_IN_ASYNC: Final = ErrorCode("INJECTION_SYNC_IN_ASYNC", INJECTION)

CONTAINER: Final = ErrorCategory("CONTAINER", parent=INJECTION)
CONTAINER_ERROR: Final = ErrorCode("CONTAINER_ERROR", CONTAINER)
CONTAINER_DISPOSED: Final = ErrorCode("CONTAINER_DISPOSED", CONTAINER)

SCOPE: Final = ErrorCategory("SCOPE", parent=INJECTION)
SCOPE_ERROR: Final = ErrorCode("SCOPE_ERROR", SCOPE)
SCOPE_DISPOSED: Final = ErrorCode("SCOPE_DISPOSED", SCOPE)


class InjectionError(UnoError):
    """Base class for all DI-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = INJECTION_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a DI error.

        Args:
            message: Human-readable error message
            code: Error code
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys
        """
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


class ContainerError(InjectionError):
    """Base class for errors that capture container state.

    This error class is used when a container instance is available and should
    be able to capture relevant container state for diagnostics.
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = CONTAINER_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a container error.

        Args:
            message: Human-readable error message
            code: Error code
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys
        """
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


# =============================================================================
class ServiceCreationError(ContainerError):
    """Raised when the container cannot create a service instance.

    Captures container state, dependency chain, constructor signature, and error metadata for debugging.
    """

    def __init__(
        self,
        message: str,
        service_type: type[T] | None = None,
        original_error: Exception | None = None,
        service_key: str | None = None,
        dependency_chain: list[str] | None = None,
        code: ErrorCode = INJECTION_SERVICE_CREATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a service creation error.

        Args:
            message: Human-readable error message
            service_type: The type of service that could not be created
            original_error: The original error that occurred during creation
            service_key: The service key that was requested
            dependency_chain: The chain of dependencies being resolved
            code: Error code
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys
        """
        ctx = kwargs.copy()
        if service_type is not None:
            service_type_name = getattr(service_type, "__name__", str(service_type))
            ctx["service_type_name"] = service_type_name

        if original_error is not None:
            ctx["error_type"] = type(original_error).__name__
            ctx["original_error"] = str(original_error)
            # Set original error as __cause__
            self.__cause__ = original_error

        if service_key is not None:
            ctx["service_key"] = service_key

        if dependency_chain is not None:
            ctx["dependency_chain"] = dependency_chain

        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **ctx,
        )


class TypeMismatchError(InjectionError):
    """Raised when a service instance doesn't match its expected interface."""

    def __init__(
        self,
        interface: type[Any],
        actual_type: type[Any],
        code: ErrorCode = INJECTION_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a type mismatch error.

        Args:
            interface: The expected interface type
            actual_type: The actual type provided
            code: Error code
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys
        """
        message = f"Expected {interface.__name__}, got {actual_type.__name__}"

        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            expected_type=interface.__name__,
            actual_type=actual_type.__name__,
            **kwargs,
        )


class ServiceNotFoundError(ContainerError):
    """Raised when a requested service is not registered or cannot be resolved.

    Captures container state, service type, and protocol/debug metadata for full traceability.
    """

    def __init__(
        self,
        message: str,
        service_type: type[T] | None = None,
        service_key: str | None = None,
        dependency_chain: list[str] | None = None,
        code: ErrorCode = INJECTION_SERVICE_NOT_FOUND,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a service not found error.

        Args:
            message: Human-readable error message
            service_type: The type of service that was requested
            service_key: The service key that was requested
            dependency_chain: The chain of dependencies being resolved
            code: Error code
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys
        """
        ctx = kwargs.copy()
        if service_type is not None:
            service_type_name = getattr(service_type, "__name__", str(service_type))
            ctx["service_type_name"] = service_type_name

            # Check for protocol information
            if hasattr(service_type, "__protocol_attrs__"):
                ctx["is_protocol"] = True
                try:
                    protocol_attrs = getattr(service_type, "__protocol_attrs__", [])
                    ctx["protocol_attributes"] = protocol_attrs
                except Exception:
                    pass

        if service_key is not None:
            ctx["service_key"] = service_key

        if dependency_chain is not None:
            ctx["dependency_chain"] = dependency_chain

        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **ctx,
        )


class DuplicateRegistrationError(InjectionError):
    """Raised when trying to register a service that is already registered."""

    def __init__(
        self,
        interface: type[Any],
        code: ErrorCode = INJECTION_DUPLICATE_REGISTRATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a duplicate registration error.

        Args:
            interface: The service interface that was already registered
            code: Error code
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys
        """
        message = f"Service {interface.__name__} is already registered"

        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            interface_name=interface.__name__,
            **kwargs,
        )


class CircularDependencyError(ContainerError):
    """Error raised when a circular dependency is detected.

    This error is raised when the container detects a circular dependency
    during service resolution. It captures the dependency chain and container state.
    """

    def __init__(
        self,
        message: str | None = None,
        dependency_chain: list[str] | None = None,
        code: ErrorCode = INJECTION_CIRCULAR_DEPENDENCY,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a circular dependency error.

        Args:
            message: Custom error message
            dependency_chain: The chain of dependencies that formed the circle
            code: Error code
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys
        """
        # If dependency_chain is in context, extract it
        if dependency_chain is None and "dependency_chain" in kwargs:
            dependency_chain = kwargs.pop("dependency_chain")

        # If we don't have a dependency chain, we can't proceed
        if dependency_chain is None:
            raise ValueError(
                "dependency_chain is required for InjectionCircularDependencyError"
            )

        # Create the error message if not provided
        if message is None:
            # Find where the cycle starts
            circle_start_index = 0
            for i, service in enumerate(dependency_chain[:-1]):
                if service == dependency_chain[-1]:
                    circle_start_index = i
                    break

            # Format the circular dependency chain
            circle = " -> ".join(dependency_chain[circle_start_index:])
            message = f"Circular dependency detected: {circle}"

        ctx = kwargs.copy()
        ctx["dependency_chain"] = dependency_chain

        # Add circular dependency to context
        circle_start_index = 0
        for i, service in enumerate(dependency_chain[:-1]):
            if service == dependency_chain[-1]:
                circle_start_index = i
                break

        ctx["circular_dependency"] = dependency_chain[circle_start_index:]

        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **ctx,
        )


class SyncInAsyncContextError(ContainerError):
    """Raised when a sync Injection API is called from an async context (event loop running)."""

    def __init__(
        self,
        message: str | None = None,
        method: str | None = None,
        method_name: str | None = None,
        code: ErrorCode = INJECTION_SYNC_IN_ASYNC,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a sync-in-async context error.

        Args:
            message: Custom error message
            method: The method name that was incorrectly called
            method_name: Alternative name for the method
            code: Error code
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys
        """
        ctx = kwargs.copy()

        # Generate the appropriate message based on the parameters
        if message:
            pass  # Use the provided message
        elif method_name:
            message = (
                f"Synchronous API '{method_name}' called from asynchronous context"
            )
            ctx["method_name"] = method_name
        elif method:
            message = f"{method} cannot be called from an async context. Use the async version instead."
            ctx["method"] = method
        else:
            message = "Synchronous API called from asynchronous context"

        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **ctx,
        )


class ScopeError(InjectionError):
    """Error raised when there is an issue with the scope of a dependency."""

    def __init__(
        self,
        message: str,
        interface: type | None = None,
        code: ErrorCode = INJECTION_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a scope error.

        Args:
            message: Error message
            interface: The interface with scope issues
            code: Error code
            severity: Error severity
            context: Additional context information
            **kwargs: Additional context keys
        """
        ctx = kwargs.copy()
        if interface is not None:
            ctx["interface_name"] = interface.__name__

        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **ctx,
        )

    @classmethod
    def outside_scope(cls, interface: type) -> ScopeError:
        """Create an error for when a dependency is accessed outside its scope.

        Args:
            interface: The interface that was requested outside its scope

        Returns:
            The error instance
        """
        message = f"Dependency for {interface.__name__} was accessed outside its defined scope"
        return cls(message, interface=interface)


class ContainerDisposedError(ContainerError):
    """Error raised when trying to use a disposed container."""

    def __init__(
        self,
        message: str | None = None,
        operation: str | None = None,
        code: ErrorCode = CONTAINER_DISPOSED,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a container disposed error.

        Args:
            message: Custom error message
            operation: The operation that was attempted
            code: Error code
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys
        """
        ctx = kwargs.copy()

        # Generate the appropriate message based on the parameters
        if message:
            pass  # Use the provided message
        elif operation:
            message = f"Container has been disposed and cannot perform: {operation}"
            ctx["operation"] = operation
        else:
            message = "Container has been disposed and cannot be used"

        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **ctx,
        )


class ScopeDisposedError(ContainerError):
    """Enhanced error raised when an operation is attempted on a disposed scope."""

    def __init__(
        self,
        message: str | None = None,
        operation: str | None = None,
        operation_name: str | None = None,
        scope_id: str | None = None,
        scope: "ScopeProtocol | None" = None,
        code: ErrorCode = SCOPE_DISPOSED,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a scope disposed error.

        Args:
            message: Custom error message
            operation: The operation that was attempted
            operation_name: Alternative name for the operation (backward compatibility)
            scope_id: The ID of the disposed scope
            scope: The scope object (from which ID will be extracted if scope_id not provided)
            code: Error code
            severity: How severe this error is
            context: Additional context information
            **kwargs: Additional context keys
        """
        # Extract scope ID if not provided but scope is
        if scope_id is None and scope is not None:
            scope_id = str(
                id(scope)
            )  # Use the object ID if no explicit ID is available
        elif scope_id is None:
            scope_id = "unknown"

        # Determine the operation
        op = operation or operation_name or "unknown"

        ctx = kwargs.copy()
        ctx["scope_id"] = scope_id

        # Add operation to context
        if operation_name:
            ctx["operation_name"] = operation_name
        elif operation:
            ctx["operation"] = operation

        # Create the error message
        if message:
            pass  # Use the provided message
        elif operation_name:
            message = f"Operation '{operation_name}' attempted on disposed scope"
        else:
            message = f"Operation '{op}' attempted on disposed scope"

        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **ctx,
        )
