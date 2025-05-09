"""
Error classes for the Uno DI system.

This module contains specialized error classes for the dependency injection system,
providing detailed error messages and context for DI-related failures.
"""

from __future__ import annotations

import inspect
import logging
import threading
import traceback
from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError

if TYPE_CHECKING:
    from collections.abc import Iterator

# Prefix for all DI error codes
ERROR_CODE_PREFIX: Final[str] = "DI"


# =============================================================================
# Container and Scope Protocols
# =============================================================================

T = TypeVar("T")
TContainer = TypeVar("TContainer", bound="ContainerProtocol")
TScope = TypeVar("TScope", bound="ScopeProtocol")


@runtime_checkable
class ScopeProtocol(Protocol):
    """Protocol defining the minimal interface for a DI scope."""

    @property
    def id(self) -> str:
        """Get the unique identifier for this scope."""
        ...

    @property
    def parent(self) -> ScopeProtocol | None:
        """Get the parent scope, or None if this is a root scope."""
        ...

    def get_service_keys(self) -> list[str]:
        """Get the service keys available in this scope."""
        ...


@runtime_checkable
class ContainerProtocol(Protocol):
    """Protocol defining the minimal interface for a DI container."""

    @property
    def current_scope(self) -> ScopeProtocol | None:
        """Get the current active scope, or None if no scope is active."""
        ...

    def get_registration_keys(self) -> list[str]:
        """Get all registered service keys."""
        ...

    def get_scope_chain(self) -> list[ScopeProtocol]:
        """Get the chain of scopes from current to root."""
        ...


class DIError(UnoError):
    """Base class for all DI-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
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


# =============================================================================
# Container-aware errors
# =============================================================================


class DIContainerError(DIError):
    """Base class for errors that capture container state.

    This error class is used when a container instance is available and should
    be able to capture relevant container state for diagnostics.
    """

    # Thread-local storage for the current container
    _current_container: ClassVar[dict[int, ContainerProtocol]] = {}

    def __init__(
        self,
        message: str,
        container: ContainerProtocol | None = None,
        capture_container_state: bool = True,
        error_code: str | None = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **context: Any,
    ):
        """Initialize the DI container error.

        Args:
            message: The error message
            container: The DI container to capture state from
            capture_container_state: Whether to capture container state
            error_code: The error code
            severity: The error severity
            **context: Additional context to include
        """
        # Get the container from the thread-local storage if not provided
        thread_id = threading.get_ident()
        if container is None and thread_id in self._current_container:
            container = self._current_container[thread_id]

        # Initialize the base class
        super().__init__(
            message=message,
            error_code=error_code or "CONTAINER_ERROR",
            severity=severity,
            **context,
        )

        # Capture container state if requested and a container is available
        if capture_container_state and container is not None:
            self._capture_container_state(container)

    def _capture_container_state(self, container: ContainerProtocol) -> None:
        """Capture the state of the container.

        Args:
            container: The DI container to capture state from
        """
        try:
            # Add container registrations
            self.add_context(
                "container_registrations", container.get_registration_keys()
            )

            # Add current scope information if available
            current_scope = container.current_scope
            if current_scope:
                self.add_context("current_scope_id", current_scope.id)
                self.add_context(
                    "current_scope_services", current_scope.get_service_keys()
                )

                # Add scope chain
                scope_chain = container.get_scope_chain()
                if scope_chain:
                    scope_ids = [scope.id for scope in scope_chain]
                    self.add_context("scope_chain", scope_ids)
        except Exception as e:
            # If capturing container state fails, add that as context
            self.add_context("container_state_capture_error", str(e))
            logging.exception("Error capturing container state")

    @classmethod
    @contextmanager
    def using_container(cls, container: ContainerProtocol) -> Iterator[None]:
        """Set the current container for the current thread.

        This context manager sets the current container for the current thread,
        which will be used by any DIContainerError instances created within
        the context manager's scope that don't have a container explicitly provided.

        Args:
            container: The container to use

        Yields:
            None
        """
        thread_id = threading.get_ident()
        previous = cls._current_container.get(thread_id)
        cls._current_container[thread_id] = container
        try:
            yield
        except Exception:
            logging.exception("Error during container usage")
            raise
        finally:
            if previous is not None:
                cls._current_container[thread_id] = previous
            else:
                del cls._current_container[thread_id]


class ServiceCreationError(DIError):
    """Raised when a service cannot be created."""

    def __init__(self, interface: type[Any], error: Exception, **context: Any) -> None:
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


class DIServiceCreationError(DIContainerError):
    """Enhanced error raised when a service cannot be created.

    This error is raised when the container encounters an error while creating
    a service instance. It captures container state and dependency chain information.
    """

    def __init__(
        self,
        service_type: type[T],
        original_error: Exception,
        container: ContainerProtocol | None = None,
        service_key: str | None = None,
        dependency_chain: list[str] | None = None,
        error_code: str | None = None,
        **context: Any,
    ):
        """Initialize the service creation error.

        Args:
            service_type: The type of service that could not be created
            original_error: The original error that occurred during creation
            container: The DI container to capture state from
            service_key: The service key that was requested, if different from the type name
            dependency_chain: The chain of dependencies being resolved
            error_code: The error code
            **context: Additional context to include
        """
        # Get the service type name
        type_name = getattr(service_type, "__name__", str(service_type))
        service_key = service_key or type_name

        # Create the error message
        message = f"Error creating service '{service_key}': {original_error!s}"

        # Add service and error information to context
        context["service_type"] = type_name
        context["service_key"] = service_key
        context["original_error_type"] = type(original_error).__name__
        context["original_error_message"] = f"{original_error!s}"

        # Add dependency chain if available
        if dependency_chain:
            context["dependency_chain"] = dependency_chain

        # Add stack trace of the original error
        if hasattr(original_error, "__traceback__") and original_error.__traceback__:
            tb_lines = traceback.format_tb(original_error.__traceback__)
            context["original_error_traceback"] = "".join(tb_lines)

        # Capture constructor parameters for better debugging
        try:
            if hasattr(service_type, "__init__"):
                signature = inspect.signature(service_type.__init__)
                context["constructor_parameters"] = str(signature)
        except Exception:
            pass

        # Initialize the base class
        super().__init__(
            message=message,
            container=container,
            error_code=error_code or "SERVICE_CREATION",
            severity=ErrorSeverity.ERROR,
            **context,
        )

        # Set the original error as the cause
        self.__cause__ = original_error


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
            error_code="TYPE_MISMATCH",
            **details,
        )


class ServiceNotRegisteredError(DIError):
    """Raised when trying to resolve a service that hasn't been registered."""

    def __init__(self, interface: type[Any], **context: Any) -> None:
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


class DIServiceNotFoundError(DIContainerError):
    """Enhanced error raised when a service is not found in the container.

    This error is raised when a service is requested from the container but
    is not registered or cannot be resolved. It captures container state.
    """

    def __init__(
        self,
        service_type: type[T],
        container: ContainerProtocol | None = None,
        service_key: str | None = None,
        error_code: str | None = None,
        **context: Any,
    ):
        """Initialize the service not found error.

        Args:
            service_type: The type of service that was requested
            container: The DI container to capture state from
            service_key: The service key that was requested, if different from the type name
            error_code: The error code
            **context: Additional context to include
        """
        # Get the service type name
        type_name = getattr(service_type, "__name__", str(service_type))
        service_key = service_key or type_name

        # Create the error message
        message = f"Service not found: {service_key}"

        # Add service type information to context
        context["service_type"] = type_name
        context["service_key"] = service_key

        # Handle the case where the service type is a Protocol
        if hasattr(service_type, "__protocol_attrs__"):
            context["is_protocol"] = True
            # Add the protocol attrs to help with debugging
            try:
                protocol_attrs = getattr(service_type, "__protocol_attrs__", [])
                context["protocol_attributes"] = protocol_attrs
            except Exception:
                pass

        # Initialize the base class
        super().__init__(
            message=message,
            container=container,
            error_code=error_code or "SERVICE_NOT_FOUND",
            severity=ErrorSeverity.ERROR,
            **context,
        )


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
            error_code="DUPLICATE_REGISTRATION",
            interface_name=interface.__name__,
            **context,
        )


class DICircularDependencyError(DIContainerError):
    """Error raised when a circular dependency is detected.

    This error is raised when the container detects a circular dependency
    during service resolution. It captures the dependency chain and container state.
    """

    def __init__(
        self,
        dependency_chain: list[str],
        container: ContainerProtocol | None = None,
        error_code: str | None = None,
        **context: Any,
    ):
        """Initialize the circular dependency error.

        Args:
            dependency_chain: The chain of dependencies that formed the circle
            container: The DI container to capture state from
            error_code: The error code
            **context: Additional context to include
        """
        # Create the error message
        circle_start_index = 0
        for i, service in enumerate(dependency_chain[:-1]):
            if service == dependency_chain[-1]:
                circle_start_index = i
                break

        # Format the circular dependency chain
        circle = " -> ".join(dependency_chain[circle_start_index:])
        message = f"Circular dependency detected: {circle}"

        # Add dependency chain to context
        context["dependency_chain"] = dependency_chain
        context["circular_dependency"] = dependency_chain[circle_start_index:]

        # Initialize the base class
        super().__init__(
            message=message,
            container=container,
            error_code=error_code or "CIRCULAR_DEPENDENCY",
            severity=ErrorSeverity.ERROR,
            **context,
        )


class SyncInAsyncContextError(DIContainerError):
    """Raised when a sync DI API is called from an async context (event loop running)."""

    def __init__(
        self,
        message: str | None = None,
        method: str | None = None,
        method_name: str | None = None,
        container: ContainerProtocol | None = None,
        **context: Any,
    ) -> None:
        """Initialize a sync in async context error.

        Args:
            message: Optional custom error message
            method: The method name that was incorrectly called (alternative to method_name)
            method_name: The method name that was incorrectly called
            container: The DI container to capture state from
            **context: Additional context information
        """
        # Generate the appropriate message based on the parameters
        if message:
            error_message = message
        elif method_name:
            error_message = (
                f"Synchronous API '{method_name}' called from asynchronous context"
            )
            context["method_name"] = method_name
        elif method:
            error_message = f"{method} cannot be called from an async context. Use the async version instead."
        else:
            error_message = "Synchronous API called from asynchronous context"

        super().__init__(
            message=error_message,
            error_code="SYNC_IN_ASYNC_CONTEXT",
            container=container,
            **context,
        )


class ScopeError(DIError):
    """Raised when there's an error related to scopes."""

    def __init__(
        self, message: str, error_code: str | None = None, **context: Any
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
    def outside_scope(cls, interface: type[Any]) -> ScopeError:
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


class DIContainerDisposedError(DIContainerError):
    """Enhanced error raised when an operation is attempted on a disposed container.

    This error is raised when an operation is attempted on a container that has
    been disposed, such as requesting a service or creating a scope. It captures
    information about the attempted operation and container state.
    """

    def __init__(
        self,
        operation: str | None = None,
        operation_name: str | None = None,
        message: str | None = None,
        container: ContainerProtocol | None = None,
        error_code: str | None = None,
        **context: Any,
    ):
        """Initialize the container disposed error.

        Args:
            operation: The operation that was attempted
            operation_name: Alternative name for the operation (for backward compatibility)
            message: Optional custom error message
            container: The DI container to capture state from
            error_code: The error code
            **context: Additional context to include
        """
        # Determine the operation
        op = operation or operation_name or "unknown"

        # Create the error message
        if message:
            error_message = message
        elif operation_name:
            error_message = (
                f"Operation '{operation_name}' attempted on disposed container"
            )
        else:
            error_message = "Operation attempted on disposed container"

        # Add operation to context
        if operation_name:
            context["operation_name"] = operation_name
        elif operation:
            context["operation"] = operation

        # Initialize the base class
        super().__init__(
            message=error_message,
            container=container,
            error_code=error_code or "CONTAINER_DISPOSED",
            severity=ErrorSeverity.ERROR,
            **context,
        )


class DIScopeDisposedError(DIContainerError):
    """Enhanced error raised when an operation is attempted on a disposed scope.

    This error is raised when an operation is attempted on a scope that has
    been disposed, such as requesting a service or creating a child scope. It
    captures information about the attempted operation, scope ID, and container state.
    """

    def __init__(
        self,
        operation: str | None = None,
        operation_name: str | None = None,
        scope_id: str | None = None,
        scope: ScopeProtocol | None = None,
        message: str | None = None,
        container: ContainerProtocol | None = None,
        error_code: str | None = None,
        **context: Any,
    ):
        """Initialize the scope disposed error.

        Args:
            operation: The operation that was attempted
            operation_name: Alternative name for the operation (for backward compatibility)
            scope_id: The ID of the disposed scope
            scope: The scope object (from which ID will be extracted if scope_id not provided)
            message: Optional custom error message
            container: The DI container to capture state from
            error_code: The error code
            **context: Additional context to include
        """
        # Extract scope ID if not provided but scope is
        if scope_id is None and scope is not None:
            scope_id = scope.id
        elif scope_id is None:
            scope_id = "unknown"

        # Determine the operation
        op = operation or operation_name or "unknown"

        # Create the error message
        if message:
            error_message = message
        elif operation_name:
            error_message = f"Operation '{operation_name}' attempted on disposed scope"
            if scope_id:
                context["scope_id"] = scope_id
        else:
            error_message = "Operation attempted on disposed scope"
            if scope_id:
                context["scope_id"] = scope_id

        # Add operation to context
        if operation_name:
            context["operation_name"] = operation_name
        elif operation:
            context["operation"] = operation

        # Initialize the base class
        super().__init__(
            message=error_message,
            container=container,
            error_code=error_code or "SCOPE_DISPOSED",
            severity=ErrorSeverity.ERROR,
            **context,
        )


# =============================================================================
# Error factory functions
# =============================================================================


def service_not_found_error(
    service_type: type[T],
    container: ContainerProtocol | None = None,
    service_key: str | None = None,
    **context: Any,
) -> DIServiceNotFoundError:
    """Create a DIServiceNotFoundError.

    Args:
        service_type: The type of service that was requested
        container: The DI container to capture state from
        service_key: The service key that was requested, if different from the type name
        **context: Additional context to include

    Returns:
        A new DIServiceNotFoundError instance
    """
    return DIServiceNotFoundError(
        service_type=service_type,
        container=container,
        service_key=service_key,
        **context,
    )


def circular_dependency_error(
    dependency_chain: list[str],
    container: ContainerProtocol | None = None,
    **context: Any,
) -> DICircularDependencyError:
    """Create a DICircularDependencyError.

    Args:
        dependency_chain: The chain of dependencies that formed the circle
        container: The DI container to capture state from
        **context: Additional context to include

    Returns:
        A new DICircularDependencyError instance
    """
    return DICircularDependencyError(
        dependency_chain=dependency_chain,
        container=container,
        **context,
    )


def service_creation_error(
    service_type: type[T],
    original_error: Exception,
    container: ContainerProtocol | None = None,
    service_key: str | None = None,
    dependency_chain: list[str] | None = None,
    **context: Any,
) -> DIServiceCreationError:
    """Create a DIServiceCreationError.

    Args:
        service_type: The type of service that could not be created
        original_error: The original error that occurred during creation
        container: The DI container to capture state from
        service_key: The service key that was requested, if different from the type name
        dependency_chain: The chain of dependencies being resolved
        **context: Additional context to include

    Returns:
        A new DIServiceCreationError instance
    """
    return DIServiceCreationError(
        service_type=service_type,
        original_error=original_error,
        container=container,
        service_key=service_key,
        dependency_chain=dependency_chain,
        **context,
    )


def container_disposed_error(
    operation: str,
    container: ContainerProtocol | None = None,
    **context: Any,
) -> DIContainerDisposedError:
    """Create a DIContainerDisposedError.

    Args:
        operation: The operation that was attempted
        container: The DI container to capture state from
        **context: Additional context to include

    Returns:
        A new DIContainerDisposedError instance
    """
    return DIContainerDisposedError(
        operation=operation,
        container=container,
        **context,
    )


def scope_disposed_error(
    operation: str,
    scope_id: str,
    container: ContainerProtocol | None = None,
    **context: Any,
) -> DIScopeDisposedError:
    """Create a DIScopeDisposedError.

    Args:
        operation: The operation that was attempted
        scope_id: The ID of the disposed scope
        container: The DI container to capture state from
        **context: Additional context to include

    Returns:
        A new DIScopeDisposedError instance
    """
    return DIScopeDisposedError(
        operation=operation,
        scope_id=scope_id,
        container=container,
        **context,
    )
