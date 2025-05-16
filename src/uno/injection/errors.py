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
INJECTION: Final = ErrorCategory.get_or_create("INJECTION")
INJECTION_ERROR: Final = ErrorCode.get_or_create("INJECTION_ERROR", INJECTION)
INJECTION_SERVICE_CREATION: Final = ErrorCode.get_or_create(
    "INJECTION_SERVICE_CREATION", INJECTION
)
INJECTION_SERVICE_NOT_FOUND: Final = ErrorCode.get_or_create(
    "INJECTION_SERVICE_NOT_FOUND", INJECTION
)
INJECTION_DUPLICATE_REGISTRATION: Final = ErrorCode.get_or_create(
    "INJECTION_DUPLICATE_REGISTRATION", INJECTION
)
INJECTION_CIRCULAR_DEPENDENCY: Final = ErrorCode.get_or_create(
    "INJECTION_CIRCULAR_DEPENDENCY", INJECTION
)
INJECTION_SYNC_IN_ASYNC: Final = ErrorCode.get_or_create(
    "INJECTION_SYNC_IN_ASYNC", INJECTION
)
INJECTION_DISPOSAL: Final = ErrorCode.get_or_create("INJECTION_DISPOSAL", INJECTION)

CONTAINER: Final = ErrorCategory.get_or_create("CONTAINER", parent=INJECTION)
CONTAINER_ERROR: Final = ErrorCode.get_or_create("CONTAINER_ERROR", CONTAINER)
CONTAINER_DISPOSED: Final = ErrorCode.get_or_create("CONTAINER_DISPOSED", CONTAINER)

SCOPE: Final = ErrorCategory.get_or_create("SCOPE", parent=INJECTION)
SCOPE_ERROR: Final = ErrorCode.get_or_create("SCOPE_ERROR", SCOPE)
SCOPE_DISPOSAL_ERROR: Final = ErrorCode.get_or_create("SCOPE_DISPOSAL_ERROR", SCOPE)


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
        # Accept both ErrorCode and str for code
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )

    @classmethod
    async def async_init(
        cls,
        message: str | None = None,
        code: ErrorCode = INJECTION_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> "InjectionError":
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
        # Compose a default message if not provided
        if message is None:
            message = "An injection error occurred"
        # Merge context and kwargs
        merged_context = dict(context or {})
        merged_context.update(kwargs)
        return cls(
            message=message,
            code=code,
            severity=severity,
            context=merged_context,
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
        # Accept both ErrorCode and str for code
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


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
        # Accept both ErrorCode and str for code
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
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

    @classmethod
    async def async_init(
        cls,
        message: str | None = None,
        service_type: type[Any] | None = None,
        original_error: Exception | None = None,
        service_key: str | None = None,
        dependency_chain: list[str] | None = None,
        container: "ContainerProtocol | None" = None,
        code: ErrorCode = INJECTION_SERVICE_CREATION,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> "ServiceCreationError":
        """
        Async factory for ServiceCreationError that can capture container state.
        """
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
        # Compose message if not provided
        if message is None:
            if service_type is not None:
                service_type_name = getattr(service_type, "__name__", str(service_type))
                message = f"Failed to create service: {service_type_name}"
            else:
                message = "Failed to create service"
        # Optionally capture container state
        if container is not None:
            try:
                from uno.injection.diagnostics import ContainerStateCapture

                error = cls(
                    message=message,
                    service_type=service_type,
                    original_error=original_error,
                    service_key=service_key,
                    dependency_chain=dependency_chain,
                    code=code,
                    severity=severity,
                    context=context,
                    **kwargs,
                )
                await ContainerStateCapture.capture_service_creation_state(
                    error,
                    service_type or object,
                    container,
                    service_key,
                    dependency_chain,
                )
                return error
            except Exception:
                pass
        return cls(
            message=message,
            service_type=service_type,
            original_error=original_error,
            service_key=service_key,
            dependency_chain=dependency_chain,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
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
        # Accept both ErrorCode and str for code
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
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
        # Accept both ErrorCode and str for code
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
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

    @classmethod
    async def async_init(
        cls,
        message: str | None = None,
        service_type: type[Any] | None = None,
        service_key: str | None = None,
        dependency_chain: list[str] | None = None,
        container: "ContainerProtocol | None" = None,
        code: ErrorCode = INJECTION_SERVICE_NOT_FOUND,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> "ServiceNotFoundError":
        """
        Async factory for ServiceNotFoundError that can capture container state.
        """
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
        if message is None:
            if service_type is not None:
                service_type_name = getattr(service_type, "__name__", str(service_type))
                message = f"Service not found: {service_type_name}"
            else:
                message = "Service not found"
        # Optionally capture container state
        if container is not None:
            try:
                from uno.injection.diagnostics import ContainerStateCapture

                error = cls(
                    message=message,
                    service_type=service_type,
                    service_key=service_key,
                    dependency_chain=dependency_chain,
                    code=code,
                    severity=severity,
                    context=context,
                    **kwargs,
                )
                await ContainerStateCapture.capture_state(error, container)
                return error
            except Exception:
                pass
        return cls(
            message=message,
            service_type=service_type,
            service_key=service_key,
            dependency_chain=dependency_chain,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
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
        # Accept both ErrorCode and str for code
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
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
        # Accept both ErrorCode and str for code
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
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

    @classmethod
    async def async_init(
        cls,
        message: str | None = None,
        dependency_chain: list[str] | None = None,
        container: "ContainerProtocol | None" = None,
        code: ErrorCode = INJECTION_CIRCULAR_DEPENDENCY,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> "CircularDependencyError":
        """
        Async factory for CircularDependencyError that can capture container state.
        """
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
        # Compose message if not provided
        if dependency_chain is None and "dependency_chain" in kwargs:
            dependency_chain = kwargs.pop("dependency_chain")
        if dependency_chain is None:
            raise ValueError("dependency_chain is required for CircularDependencyError")
        if message is None:
            # Find where the cycle starts
            circle_start_index = 0
            for i, service in enumerate(dependency_chain[:-1]):
                if service == dependency_chain[-1]:
                    circle_start_index = i
                    break
            circle = " -> ".join(dependency_chain[circle_start_index:])
            message = f"Circular dependency detected: {circle}"
        # Optionally capture container state
        if container is not None:
            try:
                from uno.injection.diagnostics import ContainerStateCapture

                error = cls(
                    message=message,
                    dependency_chain=dependency_chain,
                    code=code,
                    severity=severity,
                    context=context,
                    **kwargs,
                )
                await ContainerStateCapture.capture_state(error, container)
                return error
            except Exception:
                pass
        return cls(
            message=message,
            dependency_chain=dependency_chain,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
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
        # Accept both ErrorCode and str for code
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
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
        # Accept both ErrorCode and str for code
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
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
        # Accept both ErrorCode and str for code
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
        ctx = kwargs.copy()

        # Always set operation in context if provided or can be inferred
        op = operation
        if (
            not op
            and message
            and message != "Container has been disposed and cannot be used"
        ):
            # Try to infer operation from message if possible
            if "cannot perform:" in message:
                op = message.split("cannot perform:")[-1].strip()
        if not op and message:
            # If message is just the operation name (e.g., "resolve"), use it
            op = message.strip()
        if op:
            ctx["operation"] = op

        # Generate the appropriate message based on the parameters
        if message:
            pass  # Use the provided message
        elif operation:
            message = f"Container has been disposed and cannot perform: {operation}"
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
        code: ErrorCode = SCOPE_DISPOSAL_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        # Accept both ErrorCode and str for code
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
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

    @classmethod
    async def async_init(
        cls,
        message: str | None = None,
        operation: str | None = None,
        operation_name: str | None = None,
        scope_id: str | None = None,
        scope: "ScopeProtocol | None" = None,
        code: ErrorCode = SCOPE_DISPOSAL_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> "ScopeDisposedError":
        """
        Async factory for ScopeDisposedError.
        """
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
        return cls(
            message=message,
            operation=operation,
            operation_name=operation_name,
            scope_id=scope_id,
            scope=scope,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )


class DisposalError(InjectionError):
    """Error raised when container disposal fails."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = INJECTION_DISPOSAL,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        # Accept both ErrorCode and str for code
        if isinstance(code, str):
            code = ErrorCode.get_by_code(code)
        super().__init__(
            message,
            code=code,
            severity=severity,
            context=context,
            **kwargs,
        )
