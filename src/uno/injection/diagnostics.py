"""
Container diagnostics service for capturing container state.

This module provides services for capturing container state for diagnostic purposes,
particularly for error handling and debugging.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, ClassVar, Final

from uno.errors.base import UnoError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from uno.injection.protocols import ContainerProtocol


class ContainerStateCapture:
    """Service for capturing container state for diagnostics."""

    # Thread-local container storage
    _current_container: ClassVar[dict[int, "ContainerProtocol"]] = {}

    @classmethod
    @contextmanager
    def using_container(cls, container: "ContainerProtocol") -> Iterator[None]:
        """Context manager for setting the current container for the thread.

        Args:
            container: The container to set as current

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

    @classmethod
    def get_current_container(cls) -> "ContainerProtocol | None":
        """Get the current container for the thread.

        Returns:
            The current container or None if not set
        """
        thread_id = threading.get_ident()
        return cls._current_container.get(thread_id)

    @classmethod
    async def capture_state(
        cls, error: UnoError, container: "ContainerProtocol | None" = None
    ) -> UnoError:
        """Capture container state and add it to the error context.

        Args:
            error: The error to enrich with container state
            container: The container to capture state from (uses thread-local if None)

        Returns:
            The enriched error
        """
        # Get container from thread-local storage if not provided
        container = container or cls.get_current_container()

        if container is None:
            # No container available
            return error

        # Capture container registrations if available
        try:
            if hasattr(container, "get_registration_keys"):
                registration_keys = await container.get_registration_keys()
                error.add_context("container_registrations", registration_keys)
                error.add_context("container_id", id(container))
        except Exception as exc:
            error.add_context("container_state_capture_error", str(exc))

        return error

    @classmethod
    async def capture_service_creation_state(
        cls,
        error: UnoError,
        service_type: type,
        container: "ContainerProtocol | None" = None,
        service_key: str | None = None,
        dependency_chain: list[str] | None = None,
    ) -> UnoError:
        """Capture service creation specific state and add it to the error context.

        Args:
            error: The error to enrich
            service_type: The type of service that failed to create
            container: The container to capture state from
            service_key: The service key that was requested
            dependency_chain: The chain of dependencies being resolved

        Returns:
            The enriched error
        """
        # First capture basic container state
        await cls.capture_state(error, container)

        # Add service-specific context
        service_type_name = getattr(service_type, "__name__", str(service_type))
        error.add_context("service_type_name", service_type_name)

        if service_key is not None:
            error.add_context("service_key", service_key)

        if dependency_chain is not None:
            error.add_context("dependency_chain", dependency_chain)

        # Capture constructor parameters for better debugging
        try:
            if hasattr(service_type, "__init__"):
                import inspect

                signature = inspect.signature(service_type.__init__)
                error.add_context("constructor_parameters", str(signature))
        except Exception:
            pass

        return error
