"""
Error classes for the Uno DI system.

This module contains specialized error classes for the dependency injection system,
providing detailed error messages and context for DI-related failures.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, ClassVar, Final, TypeVar

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from uno.di.protocols import ContainerProtocol, ScopeProtocol

# Prefix for all DI error codes
ERROR_CODE_PREFIX: Final[str] = "DI"

T = TypeVar("T")
TContainer = TypeVar("TContainer", bound="ContainerProtocol")
TScope = TypeVar("TScope", bound="ScopeProtocol")


class DIError(UnoError):
    """Base class for all DI-related errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **context: Any,
    ) -> None:
        """Initialize a DI error.

        Args:
            message: Human-readable error message
            code: Error code without prefix (will be prefixed with DI_)
            severity: How severe this error is
            **context: Additional context information
        """
        super().__init__(
            code=(
                f"{ERROR_CODE_PREFIX}_{code}" if code else f"{ERROR_CODE_PREFIX}_ERROR"
            ),
            message=message,
            category=ErrorCategory.DI,
            severity=severity,
            context=context or {},
        )


# =============================================================================
# Container-aware errors
# =============================================================================


class ContainerError(DIError):
    """Base class for errors that capture container state (async-only).

    This error class is used when a container instance is available and should
    be able to capture relevant container state for diagnostics. Only async
    initialization and state capture is supported.
    """

    _current_container: ClassVar[dict[int, "ContainerProtocol"]] = {}

    def __init__(self, *args: Any, **kwargs: Any):
        raise TypeError(
            "ContainerError and subclasses must be constructed using the async_init() classmethod (async-only)."
        )

    @classmethod
    async def async_init(
        cls,
        message: str,
        container: "ContainerProtocol" | None = None,
        capture_container_state: bool = True,
        code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **context: Any,
    ) -> "ContainerError":
        """Async factory for ContainerError and subclasses. Captures container state asynchronously."""
        # Get the container from the thread-local storage if not provided
        thread_id = threading.get_ident()
        if container is None and thread_id in cls._current_container:
            container = cls._current_container[thread_id]

        # Create instance using Exception.__new__ instead of object.__new__
        instance = Exception.__new__(cls)

        # Initialize the DIError base class
        DIError.__init__(
            instance,
            code=code or "CONTAINER_ERROR",
            message=message,
            severity=severity,
            context=context or {},
        )

        # Capture container state asynchronously if requested
        if capture_container_state and container is not None:
            await instance._capture_container_state_async(container)
        return instance

    async def _capture_container_state_async(
        self, container: "ContainerProtocol"
    ) -> None:
        """Capture the state of the container asynchronously. Override in subclasses if needed."""
        # Example: Add container registrations
        try:
            if hasattr(container, "get_registration_keys"):
                self.add_context(
                    "container_registrations", await container.get_registration_keys()
                )
        except Exception as e:
            self.add_context("container_state_capture_error", str(e))

    @classmethod
    @contextmanager
    def using_container(cls, container: "ContainerProtocol") -> "Iterator[None]":
        thread_id = threading.get_ident()
        previous = cls._current_container.get(thread_id)
        cls._current_container[thread_id] = container
        try:
            yield
        finally:
            if previous is not None:
                cls._current_container[thread_id] = previous
            else:
                del cls._current_container[thread_id]

    async def _capture_container_state(self, container: ContainerProtocol) -> None:
        """Capture the state of the container asynchronously.

        Args:
            container: The DI container to capture state from
        """
        # This logic must be moved to the async _capture_container_state_async method.
        # If synchronous context is needed, call this method from an event loop.
        raise NotImplementedError(
            "Use async _capture_container_state_async for container state capture."
        )


# =============================================================================
class DIServiceCreationError(ContainerError):
    """Raised when the container cannot create a service instance (Uno idiom).

    Captures container state, dependency chain, constructor signature, and error metadata for debugging.
    """

    @classmethod
    async def async_init(
        cls,
        service_type: type[T],
        original_error: Exception,
        container: ContainerProtocol | None = None,
        service_key: str | None = None,
        dependency_chain: list[str] | None = None,
        code: str | None = None,
        **context: Any,
    ) -> "DIServiceCreationError":
        """Async factory for creating service creation errors.

        Args:
            service_type: The type of service that could not be created
            original_error: The original error that occurred during creation
            container: The DI container to capture state from
            service_key: The service key that was requested, if different from the type name
            dependency_chain: The chain of dependencies being resolved
            code: The error code
            **context: Additional context to include

        Returns:
            An initialized DIServiceCreationError instance
        """
        service_type_name = getattr(service_type, "__name__", str(service_type))
        context["service_type_name"] = service_type_name
        context["error_type"] = type(original_error).__name__
        if container is not None:
            context["container_id"] = id(container)
        if service_key is not None:
            context["service_key"] = service_key
        if dependency_chain is not None:
            context["dependency_chain"] = dependency_chain
        # Capture constructor parameters for better debugging
        try:
            if hasattr(service_type, "__init__"):
                import inspect

                signature = inspect.signature(service_type.__init__)
                context["constructor_parameters"] = str(signature)
        except Exception:
            pass
        message = f"Failed to create service {service_type_name}: {original_error}"
        instance = await super().async_init(
            message=message,
            container=container,
            code=code or "SERVICE_CREATION",
            severity=ErrorSeverity.ERROR,
            **context,
        )
        instance.__cause__ = original_error
        return instance


# Alias for backward compatibility - remove this once tests are updated
DIDIServiceCreationError = DIServiceCreationError


# =============================================================================
class TypeMismatchError(DIError):
    """Raised when a service instance doesn't match its expected interface."""

    def __init__(
        self, interface: type[Any], actual_type: type[Any], **context: Any
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
            code="TYPE_MISMATCH",
            **details,
        )


# =============================================================================
class DIServiceNotFoundError(ContainerError):
    """Raised when a requested service is not registered or cannot be resolved (Uno idiom).

    Captures container state, service type, and protocol/debug metadata for full traceability.
    """

    @classmethod
    async def async_init(
        cls,
        service_type: type[T],
        container: ContainerProtocol | None = None,
        service_key: str | None = None,
        code: str | None = None,
        dependency_chain: list[str] | None = None,
        **context: Any,
    ) -> "DIServiceNotFoundError":
        """Async factory for DIServiceNotFoundError with full context propagation.

        Args:
            service_type: The type of service that was requested
            container: The DI container to capture state from
            service_key: The service key that was requested, if different from the type name
            code: The error code
            dependency_chain: The chain of dependencies being resolved
            **context: Additional context to include

        Returns:
            An initialized DIServiceNotFoundError instance
        """
        service_type_name = getattr(service_type, "__name__", str(service_type))
        context["service_type_name"] = service_type_name
        if container is not None:
            context["container_id"] = id(container)
        if service_key is not None:
            context["service_key"] = service_key
        if dependency_chain is not None:
            context["dependency_chain"] = dependency_chain
        if hasattr(service_type, "__protocol_attrs__"):
            context["is_protocol"] = True
            try:
                protocol_attrs = getattr(service_type, "__protocol_attrs__", [])
                context["protocol_attributes"] = protocol_attrs
            except Exception:
                pass
        message = f"Service not found: {service_type_name}"
        return await super().async_init(
            message=message,
            container=container,
            code=code or "SERVICE_NOT_FOUND",
            severity=ErrorSeverity.ERROR,
            **context,
        )


# Alias for backward compatibility with existing tests
ServiceNotRegisteredError = DIServiceNotFoundError


class DuplicateRegistrationError(DIError):
    """Raised when trying to register a service that is already registered."""

    def __init__(self, interface: type[Any], **context: Any) -> None:
        """Initialize a duplicate registration error.

        Args:
            interface: The service interface that was already registered
            **context: Additional context information
        """
        super().__init__(
            message=f"Service {interface.__name__} is already registered",
            code="DUPLICATE_REGISTRATION",
            interface_name=interface.__name__,
            **context,
        )


class DICircularDependencyError(ContainerError):
    """Error raised when a circular dependency is detected.

    This error is raised when the container detects a circular dependency
    during service resolution. It captures the dependency chain and container state.
    """

    @classmethod
    async def async_init(
        cls,
        message: str | None = None,
        container: "ContainerProtocol" | None = None,
        capture_container_state: bool = True,
        code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        dependency_chain: list[str] | None = None,
        **context: Any,
    ) -> "DICircularDependencyError":
        """Async factory for creating circular dependency errors.

        Args:
            message: Custom error message (optional, will be generated from dependency_chain if not provided)
            container: The DI container to capture state from
            capture_container_state: Whether to capture container state
            code: The error code
            severity: The error severity
            dependency_chain: The chain of dependencies that formed the circle
            **context: Additional context to include

        Returns:
            An initialized DICircularDependencyError instance
        """
        # If dependency_chain is in context, extract it
        if dependency_chain is None and "dependency_chain" in context:
            dependency_chain = context.pop("dependency_chain")

        # If we don't have a dependency chain, we can't proceed
        if dependency_chain is None:
            raise ValueError(
                "dependency_chain is required for DICircularDependencyError"
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

        # Add dependency chain to context
        circle_start_index = 0
        for i, service in enumerate(dependency_chain[:-1]):
            if service == dependency_chain[-1]:
                circle_start_index = i
                break

        context["dependency_chain"] = dependency_chain
        context["circular_dependency"] = dependency_chain[circle_start_index:]

        # Use the parent class's async_init to create and initialize the instance
        return await super().async_init(
            message=message,
            container=container,
            capture_container_state=capture_container_state,
            code=code or "CIRCULAR_DEPENDENCY",
            severity=severity,
            **context,
        )


class SyncInAsyncContextError(ContainerError):
    """Raised when a sync DI API is called from an async context (event loop running)."""

    @classmethod
    async def async_init(
        cls,
        message: str | None = None,
        container: "ContainerProtocol" | None = None,
        capture_container_state: bool = True,
        code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        method: str | None = None,
        method_name: str | None = None,
        **context: Any,
    ) -> "SyncInAsyncContextError":
        """Async factory for creating sync-in-async context errors.

        Args:
            message: Optional custom error message
            container: The DI container to capture state from
            capture_container_state: Whether to capture container state
            code: The error code
            severity: The error severity
            method: The method name that was incorrectly called (alternative to method_name)
            method_name: The method name that was incorrectly called
            **context: Additional context to include

        Returns:
            An initialized SyncInAsyncContextError instance
        """
        # Generate the appropriate message based on the parameters
        if message:
            pass  # Use the provided message
        elif method_name:
            message = (
                f"Synchronous API '{method_name}' called from asynchronous context"
            )
            context["method_name"] = method_name
        elif method:
            message = f"{method} cannot be called from an async context. Use the async version instead."
            context["method"] = method
        else:
            message = "Synchronous API called from asynchronous context"

        return await super().async_init(
            message=message,
            container=container,
            capture_container_state=capture_container_state,
            code=code or "SYNC_IN_ASYNC_CONTEXT",
            severity=severity,
            **context,
        )


class ScopeError(UnoError):
    """Error raised when there is an issue with the scope of a dependency."""

    def __init__(
        self,
        message: str,
        code: str = "SCOPE_ERROR",
        category: ErrorCategory = ErrorCategory.DI,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a new ScopeError instance.

        Args:
            message: Error message
            code: Error code
            category: Error category
            severity: Error severity
            context: Additional context information
            **kwargs: Additional keyword arguments
        """
        super().__init__(
            message=message,
            code=code,
            category=category,
            severity=severity,
            context=context,
            **kwargs,
        )

    def with_context(self, context: dict[str, Any]) -> ScopeError:
        """Create a new error with additional context.

        Args:
            context: The additional context to add

        Returns:
            ScopeError: A new error instance with the combined context
        """
        new_context = {**(self.context or {}), **context}
        return self.__class__(
            message=self.message,
            code=self.code,
            category=self.category,
            severity=self.severity,
            context=new_context,
            **{
                k: v
                for k, v in self.__dict__.items()
                if k not in ["message", "code", "category", "severity", "context"]
            },
        )

    @classmethod
    def outside_scope(cls, interface: type) -> ScopeError:
        """Create an error for when a dependency is accessed outside its scope.

        Args:
            interface: The interface that was requested outside its scope

        Returns:
            ScopeError: The error instance
        """
        message = f"Dependency for {interface.__name__} was accessed outside its defined scope"
        error = cls(message)
        # Add the interface name to the context
        return error.with_context({"interface_name": interface.__name__})


class ContainerDisposedError(ContainerError):
    """Error raised when trying to use a disposed container."""

    @classmethod
    async def async_init(
        cls,
        message: str | None = None,
        container: "ContainerProtocol" | None = None,
        capture_container_state: bool = True,
        code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        operation: str | None = None,
        **context: Any,
    ) -> "ContainerDisposedError":
        """Async factory for creating container disposed errors.

        Args:
            message: Optional custom error message
            container: The DI container to capture state from
            capture_container_state: Whether to capture container state
            code: The error code
            severity: The error severity
            operation: The operation that was attempted
            **context: Additional context to include

        Returns:
            An initialized ContainerDisposedError instance
        """
        # Generate the appropriate message based on the parameters
        if message:
            pass  # Use the provided message
        elif operation:
            message = f"Container has been disposed and cannot perform: {operation}"
            context["operation"] = operation
        else:
            message = "Container has been disposed and cannot be used"

        return await super().async_init(
            message=message,
            container=container,
            capture_container_state=capture_container_state,
            code=code or "CONTAINER_DISPOSED",
            severity=severity,
            **context,
        )


class DIScopeDisposedError(ContainerError):
    """Enhanced error raised when an operation is attempted on a disposed scope.

    This error is raised when an operation is attempted on a scope that has
    been disposed, such as requesting a service or creating a child scope. It
    captures information about the attempted operation, scope ID, and container state.
    """

    @classmethod
    async def async_init(
        cls,
        message: str | None = None,
        container: "ContainerProtocol" | None = None,
        capture_container_state: bool = True,
        code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        operation: str | None = None,
        operation_name: str | None = None,
        scope_id: str | None = None,
        scope: "ScopeProtocol" | None = None,
        **context: Any,
    ) -> "DIScopeDisposedError":
        """Async factory for creating scope disposed errors.

        Args:
            message: Optional custom error message
            container: The DI container to capture state from
            capture_container_state: Whether to capture container state
            code: The error code
            severity: The error severity
            operation: The operation that was attempted
            operation_name: Alternative name for the operation (for backward compatibility)
            scope_id: The ID of the disposed scope
            scope: The scope object (from which ID will be extracted if scope_id not provided)
            **context: Additional context to include

        Returns:
            An initialized DIScopeDisposedError instance
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

        # Create the error message
        if message:
            pass  # Use the provided message
        elif operation_name:
            message = f"Operation '{operation_name}' attempted on disposed scope"
            context["scope_id"] = scope_id
        else:
            message = f"Operation '{op}' attempted on disposed scope"
            context["scope_id"] = scope_id

        # Add operation to context
        if operation_name:
            context["operation_name"] = operation_name
        elif operation:
            context["operation"] = operation

        # Use the parent class's async_init to create and initialize the instance
        return await super().async_init(
            message=message,
            container=container,
            capture_container_state=capture_container_state,
            code=code or "SCOPE_DISPOSED",
            severity=severity,
            **context,
        )
