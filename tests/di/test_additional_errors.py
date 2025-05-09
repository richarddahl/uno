"""Tests for additional error classes in the DI system."""

import asyncio
import threading

import pytest

from uno.di.errors import (
    DIContainerDisposedError,
    DIScopeDisposedError,
    SyncInAsyncContextError,
)
from uno.errors.base import ErrorCategory, ErrorSeverity


# Mock classes to simulate the container protocol
class MockScope:
    def __init__(self, scope_id: str, parent=None) -> None:
        self.id = scope_id
        self.parent = parent
        self.services = [f"service_{i}" for i in range(3)]
        self.disposed = False

    def get_service_keys(self) -> list[str]:
        return self.services


class MockContainer:
    def __init__(self, scope=None) -> None:
        self.current_scope = scope
        self.registrations = [f"registration_{i}" for i in range(5)]
        self.scopes = []
        self.disposed = False
        if scope:
            self.scopes = [scope]

    def get_registration_keys(self) -> list[str]:
        return self.registrations

    def get_scope_chain(self) -> list[MockScope]:
        return self.scopes


class TestDIContainerDisposedError:
    """Tests for DIContainerDisposedError."""

    def test_init_with_basic_info(self) -> None:
        """Test initialization with basic container info."""
        container = MockContainer()
        container.disposed = True

        error = DIContainerDisposedError(container=container)

        assert "Operation attempted on disposed container" in str(error)
        assert error.error_code == "DI_CONTAINER_DISPOSED"
        assert error.category == ErrorCategory.DI
        assert error.severity == ErrorSeverity.ERROR

    def test_init_with_custom_message(self) -> None:
        """Test initialization with a custom error message."""
        container = MockContainer()
        container.disposed = True

        error = DIContainerDisposedError(
            message="Cannot resolve service from disposed container",
            container=container,
        )

        assert "Cannot resolve service from disposed container" in str(error)

    def test_init_with_operation_name(self) -> None:
        """Test initialization with operation name."""
        container = MockContainer()
        container.disposed = True

        error = DIContainerDisposedError(operation_name="resolve", container=container)

        assert "Operation 'resolve' attempted on disposed container" in str(error)
        assert error.context["operation_name"] == "resolve"


class TestDIScopeDisposedError:
    """Tests for DIScopeDisposedError."""

    def test_init_with_basic_info(self) -> None:
        """Test initialization with basic scope info."""
        scope = MockScope("test_scope")
        scope.disposed = True

        error = DIScopeDisposedError(scope=scope)

        assert "Operation attempted on disposed scope" in str(error)
        assert error.error_code == "DI_SCOPE_DISPOSED"
        assert error.category == ErrorCategory.DI
        assert error.severity == ErrorSeverity.ERROR
        assert error.context["scope_id"] == "test_scope"

    def test_init_with_custom_message(self) -> None:
        """Test initialization with a custom error message."""
        scope = MockScope("test_scope")
        scope.disposed = True

        error = DIScopeDisposedError(
            message="Cannot get service from disposed scope", scope=scope
        )

        assert "Cannot get service from disposed scope" in str(error)

    def test_init_with_operation_name(self) -> None:
        """Test initialization with operation name."""
        scope = MockScope("test_scope")
        scope.disposed = True

        error = DIScopeDisposedError(operation_name="get_service", scope=scope)

        assert "Operation 'get_service' attempted on disposed scope" in str(error)
        assert error.context["operation_name"] == "get_service"

    def test_init_with_container(self) -> None:
        """Test initialization with container context."""
        scope = MockScope("test_scope")
        scope.disposed = True
        container = MockContainer(scope=scope)

        error = DIScopeDisposedError(scope=scope, container=container)

        assert "container_registrations" in error.context
        assert error.context["container_registrations"] == container.registrations


class TestSyncInAsyncContextError:
    """Tests for SyncInAsyncContextError."""

    def test_init_with_basic_info(self) -> None:
        """Test initialization with basic info."""
        error = SyncInAsyncContextError()

        assert "Synchronous API called from asynchronous context" in str(error)
        assert error.error_code == "DI_SYNC_IN_ASYNC_CONTEXT"
        assert error.category == ErrorCategory.DI
        assert error.severity == ErrorSeverity.ERROR

    def test_init_with_custom_message(self) -> None:
        """Test initialization with a custom error message."""
        error = SyncInAsyncContextError(
            message="Sync get_service() called from async context"
        )

        assert "Sync get_service() called from async context" in str(error)

    def test_init_with_method_name(self) -> None:
        """Test initialization with method name."""
        error = SyncInAsyncContextError(method_name="get_service")

        assert "Synchronous API 'get_service' called from asynchronous context" in str(
            error
        )
        assert error.context["method_name"] == "get_service"

    def test_init_with_container(self) -> None:
        """Test initialization with container context."""
        container = MockContainer()

        error = SyncInAsyncContextError(method="get_service", container=container)

        assert "container_registrations" in error.context
        assert error.context["container_registrations"] == container.registrations

    @pytest.mark.asyncio
    async def test_detect_async_context(self) -> None:
        """Test that the error correctly detects an async context."""
        # This simulates what would happen if code tried to detect
        # if we're in an async context

        # Define a function that checks if there's a running event loop
        def is_in_async_context() -> bool:
            try:
                asyncio.get_running_loop()
                return True
            except RuntimeError:
                return False

        # For the synchronous context check, we need to run in a separate thread
        # because pytest-asyncio runs the entire test in an asyncio event loop
        sync_result = None

        def check_in_thread() -> None:
            nonlocal sync_result
            sync_result = is_in_async_context()

        # Run the check in a separate thread to ensure it's truly synchronous
        thread = threading.Thread(target=check_in_thread)
        thread.start()
        thread.join()

        # In a synchronous context (separate thread), should be False
        assert not sync_result

        # In an asynchronous context, should be True
        assert is_in_async_context()
