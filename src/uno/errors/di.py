# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
DI-aware error types for the Uno framework.

This module provides error types that are aware of the DI container and can
capture container state, such as scope information, service registrations,
and dependency chains.
"""

from __future__ import annotations

import inspect
import threading
import traceback
import sys
from contextlib import contextmanager
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    Type,
    TypeVar,
    cast,
    runtime_checkable,
)

# Local imports
from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError
from uno.errors.component_errors import DIError


# =============================================================================
# Type definitions
# =============================================================================

T = TypeVar("T")
TContainer = TypeVar("TContainer", bound="ContainerProtocol")
TScope = TypeVar("TScope", bound="ScopeProtocol")


# =============================================================================
# Container Protocols
# =============================================================================


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


# =============================================================================
# Container-aware errors
# =============================================================================


class ContainerError(DIError):
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
        category: ErrorCategory = ErrorCategory.DI,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **context: Any,
    ) -> None:
        """Initialize the DI container error.

        Args:
            message: The error message
            container: The DI container to capture state from
            capture_container_state: Whether to capture container state
            error_code: The error code
            category: The error category
            severity: The error severity
            **context: Additional context to include
        """
        # Initialize the base class
        super().__init__(
            message=message,
            error_code=error_code or "DI_CONTAINER_ERROR",
            category=category,
            severity=severity,
            **context,
        )

        # Get the container from the thread-local storage if not provided
        thread_id = threading.get_ident()
        if container is None and thread_id in self._current_container:
            container = self._current_container[thread_id]

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

    @classmethod
    @contextmanager
    def using_container(cls, container: ContainerProtocol) -> None:
        """Set the current container for the current thread.

        This context manager sets the current container for the current thread,
        which will be used by any ContainerError instances created within
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
        finally:
            if previous is not None:
                cls._current_container[thread_id] = previous
            else:
                del cls._current_container[thread_id]


class DIServiceNotFoundError(ContainerError):
    """Error raised when a service is not found in the container.

    This error is raised when a service is requested from the container but
    is not registered or cannot be resolved.
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
            error_code=error_code or "DI_SERVICE_NOT_FOUND",
            category=ErrorCategory.DI,
            severity=ErrorSeverity.ERROR,
            **context,
        )


class DICircularDependencyError(ContainerError):
    """Error raised when a circular dependency is detected.

    This error is raised when the container detects a circular dependency
    during service resolution.
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
            error_code=error_code or "DI_CIRCULAR_DEPENDENCY",
            category=ErrorCategory.DI,
            severity=ErrorSeverity.ERROR,
            **context,
        )


class DIServiceCreationError(ContainerError):
    """Error raised when a service cannot be created.

    This error is raised when the container encounters an error while creating
    a service instance.
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
        message = f"Error creating service '{service_key}': {str(original_error)}"

        # Add service and error information to context
        context["service_type"] = type_name
        context["service_key"] = service_key
        context["original_error_type"] = type(original_error).__name__
        context["original_error_message"] = str(original_error)

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
            error_code=error_code or "DI_SERVICE_CREATION_ERROR",
            category=ErrorCategory.DI,
            severity=ErrorSeverity.ERROR,
            **context,
        )

        # Set the original error as the cause
        self.__cause__ = original_error


class ContainerDisposedError(ContainerError):
    """Error raised when an operation is attempted on a disposed container.

    This error is raised when an operation is attempted on a container that has
    been disposed, such as requesting a service or creating a scope.
    """

    def __init__(
        self,
        operation: str,
        container: ContainerProtocol | None = None,
        error_code: str | None = None,
        **context: Any,
    ):
        """Initialize the container disposed error.

        Args:
            operation: The operation that was attempted
            container: The DI container to capture state from
            error_code: The error code
            **context: Additional context to include
        """
        # Create the error message
        message = f"Cannot perform operation '{operation}' on a disposed container"

        # Add operation to context
        context["operation"] = operation

        # Initialize the base class
        super().__init__(
            message=message,
            container=container,
            error_code=error_code or "DI_CONTAINER_DISPOSED",
            category=ErrorCategory.DI,
            severity=ErrorSeverity.ERROR,
            **context,
        )


class DIScopeDisposedError(ContainerError):
    """Error raised when an operation is attempted on a disposed scope.

    This error is raised when an operation is attempted on a scope that has
    been disposed, such as requesting a service or creating a child scope.
    """

    def __init__(
        self,
        operation: str,
        scope_id: str,
        container: ContainerProtocol | None = None,
        error_code: str | None = None,
        **context: Any,
    ):
        """Initialize the scope disposed error.

        Args:
            operation: The operation that was attempted
            scope_id: The ID of the disposed scope
            container: The DI container to capture state from
            error_code: The error code
            **context: Additional context to include
        """
        # Create the error message
        message = f"Cannot perform operation '{operation}' on a disposed scope (ID: {scope_id})"

        # Add operation and scope ID to context
        context["operation"] = operation
        context["scope_id"] = scope_id

        # Initialize the base class
        super().__init__(
            message=message,
            container=container,
            error_code=error_code or "DI_SCOPE_DISPOSED",
            category=ErrorCategory.DI,
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
) -> ContainerDisposedError:
    """Create a ContainerDisposedError.

    Args:
        operation: The operation that was attempted
        container: The DI container to capture state from
        **context: Additional context to include

    Returns:
        A new ContainerDisposedError instance
    """
    return ContainerDisposedError(
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
