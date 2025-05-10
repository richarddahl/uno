"""Tests for container-aware error classes in the DI system."""

import threading
from unittest.mock import MagicMock, patch

import pytest

from uno.di.errors import (
    DICircularDependencyError,
    ContainerError,
    DIServiceCreationError,
    DIServiceNotFoundError,
)
from uno.errors.base import ErrorCategory, ErrorSeverity


# Mock classes to simulate the container protocol
class MockScope:
    def __init__(self, scope_id: str, parent=None) -> None:
        self.id = scope_id
        self.parent = parent
        self.services = [f"service_{i}" for i in range(3)]

    def get_service_keys(self) -> list[str]:
        """Return a list of service keys in the current scope."""
        return self.services


class MockContainer:
    def __init__(self, scope=None):
        self.current_scope = scope
        self.registrations = [f"registration_{i}" for i in range(5)]
        self.scopes = []
        if scope:
            self.scopes = [scope]

    def get_registration_keys(self):
        return self.registrations

    def get_scope_chain(self):
        return self.scopes


class TestContainerError:
    """Tests for the ContainerError base class."""

    def test_init_with_explicit_container(self):
        """Test initializing with an explicitly provided container."""
        mock_container = MockContainer()
        error = ContainerError("Test error", container=mock_container)

        assert "Test error" in str(error)
        assert error.error_code == "DI_CONTAINER_ERROR"
        assert error.category == ErrorCategory.DI
        assert error.severity == ErrorSeverity.ERROR
        assert "container_registrations" in error.context
        assert error.context["container_registrations"] == mock_container.registrations

    def test_init_with_container_and_scope(self):
        """Test initializing with a container that has an active scope."""
        mock_scope = MockScope("test_scope")
        mock_container = MockContainer(scope=mock_scope)
        error = ContainerError("Test error", container=mock_container)

        assert "current_scope_id" in error.context
        assert error.context["current_scope_id"] == "test_scope"
        assert "current_scope_services" in error.context
        assert error.context["current_scope_services"] == mock_scope.services
        assert "scope_chain" in error.context
        assert error.context["scope_chain"] == ["test_scope"]

    def test_init_without_capturing_container_state(self):
        """Test initializing without capturing container state."""
        mock_container = MockContainer()
        error = ContainerError(
            "Test error", container=mock_container, capture_container_state=False
        )

        assert "container_registrations" not in error.context

    def test_container_state_capture_error_handling(self):
        """Test that errors during container state capture are handled gracefully."""
        mock_container = MagicMock()
        mock_container.get_registration_keys.side_effect = RuntimeError(
            "Test exception"
        )

        error = ContainerError("Test error", container=mock_container)

        assert "container_state_capture_error" in error.context
        assert "Test exception" in error.context["container_state_capture_error"]

    def test_using_container_context_manager(self):
        """Test the using_container context manager."""
        mock_container = MockContainer()

        # Container should be set during the context
        with ContainerError.using_container(mock_container):
            error = ContainerError("Test error")
            assert "container_registrations" in error.context

        # Container should be cleared after the context
        error = ContainerError("Test error")
        assert "container_registrations" not in error.context

    def test_using_container_with_nested_contexts(self):
        """Test nested using_container context managers."""
        outer_container = MockContainer()
        inner_container = MockContainer()

        with ContainerError.using_container(outer_container):
            outer_error = ContainerError("Outer error")

            with ContainerError.using_container(inner_container):
                inner_error = ContainerError("Inner error")

            # After inner context, should revert to outer container
            after_inner_error = ContainerError("After inner error")

        # Ensure each error captured the right container
        assert (
            outer_error.context["container_registrations"]
            == outer_container.registrations
        )
        assert (
            inner_error.context["container_registrations"]
            == inner_container.registrations
        )
        assert (
            after_inner_error.context["container_registrations"]
            == outer_container.registrations
        )

    def test_using_container_with_exception(self):
        """Test that container is properly cleaned up if exception occurs in context."""
        mock_container = MockContainer()
        thread_id = threading.get_ident()

        try:
            with ContainerError.using_container(mock_container):
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Check that thread-local container is cleaned up
        assert thread_id not in ContainerError._current_container


class TestDIServiceCreationError:
    """Tests for DIServiceCreationError."""

    def test_init_with_basic_info(self):
        """Test initialization with basic service info."""

        class TestService:
            pass

        original_error = ValueError("Cannot create service")
        error = DIServiceCreationError(
            service_type=TestService, original_error=original_error
        )

        assert "Error creating service 'TestService'" in str(error)
        assert error.error_code == "DI_SERVICE_CREATION"
        assert error.context["service_type"] == "TestService"
        assert error.context["service_key"] == "TestService"
        assert error.context["original_error_type"] == "ValueError"
        assert error.context["original_error_message"] == "Cannot create service"
        assert error.__cause__ is original_error

    def test_init_with_custom_key(self):
        """Test initialization with a custom service key."""

        class TestService:
            pass

        error = DIServiceCreationError(
            service_type=TestService,
            original_error=ValueError("Test error"),
            service_key="custom.service.key",
        )

        assert "Error creating service 'custom.service.key'" in str(error)
        assert error.context["service_key"] == "custom.service.key"

    def test_init_with_dependency_chain(self):
        """Test initialization with a dependency chain."""

        class TestService:
            pass

        dependency_chain = ["ServiceA", "ServiceB", "TestService"]
        error = DIServiceCreationError(
            service_type=TestService,
            original_error=ValueError("Test error"),
            dependency_chain=dependency_chain,
        )

        assert "dependency_chain" in error.context
        assert error.context["dependency_chain"] == dependency_chain

    def test_init_captures_constructor_parameters(self):
        """Test that constructor parameters are captured."""

        class TestService:
            def __init__(self, param1: str, param2: int = 0):
                pass

        error = DIServiceCreationError(
            service_type=TestService, original_error=ValueError("Test error")
        )

        assert "constructor_parameters" in error.context
        assert "param1" in error.context["constructor_parameters"]
        assert "param2" in error.context["constructor_parameters"]

    def test_init_with_container(self):
        """Test initialization with a container."""

        class TestService:
            pass

        mock_container = MockContainer()
        error = DIServiceCreationError(
            service_type=TestService,
            original_error=ValueError("Test error"),
            container=mock_container,
        )

        assert "container_registrations" in error.context
        assert error.context["container_registrations"] == mock_container.registrations


class TestDIServiceNotFoundError:
    """Tests for DIServiceNotFoundError."""

    def test_init_with_basic_info(self):
        """Test initialization with basic service info."""

        class TestService:
            pass

        error = DIServiceNotFoundError(service_type=TestService)

        assert "Service not found: TestService" in str(error)
        assert error.error_code == "DI_SERVICE_NOT_FOUND"
        assert error.context["service_type"] == "TestService"
        assert error.context["service_key"] == "TestService"

    def test_init_with_protocol(self):
        """Test initialization with a Protocol type."""
        # Mock a Protocol type
        mock_protocol = MagicMock()
        mock_protocol.__name__ = "TestProtocol"
        mock_protocol.__protocol_attrs__ = ["method1", "method2"]

        with patch.object(
            mock_protocol, "__protocol_attrs__", ["method1", "method2"], create=True
        ):
            error = DIServiceNotFoundError(service_type=mock_protocol)

        assert "Service not found: TestProtocol" in str(error)
        assert error.context["is_protocol"] is True
        assert "protocol_attributes" in error.context
        assert "method1" in error.context["protocol_attributes"]
        assert "method2" in error.context["protocol_attributes"]

    def test_init_with_custom_key(self):
        """Test initialization with a custom service key."""

        class TestService:
            pass

        error = DIServiceNotFoundError(
            service_type=TestService, service_key="custom.service.key"
        )

        assert "Service not found: custom.service.key" in str(error)
        assert error.context["service_key"] == "custom.service.key"

    def test_init_with_container(self):
        """Test initialization with a container."""

        class TestService:
            pass

        mock_container = MockContainer()
        error = DIServiceNotFoundError(
            service_type=TestService, container=mock_container
        )

        assert "container_registrations" in error.context
        assert error.context["container_registrations"] == mock_container.registrations


class TestDICircularDependencyError:
    """Tests for DICircularDependencyError."""

    def test_init_with_dependency_chain(self):
        """Test initialization with a dependency chain."""
        dependency_chain = ["ServiceA", "ServiceB", "ServiceC", "ServiceA"]
        error = DICircularDependencyError(dependency_chain=dependency_chain)

        assert (
            "Circular dependency detected: ServiceA -> ServiceB -> ServiceC -> ServiceA"
            in str(error)
        )
        assert error.error_code == "DI_CIRCULAR_DEPENDENCY"
        assert error.context["dependency_chain"] == dependency_chain
        assert error.context["circular_dependency"] == [
            "ServiceA",
            "ServiceB",
            "ServiceC",
            "ServiceA",
        ]

    def test_init_with_partial_chain(self):
        """Test initialization with a partial dependency chain (no complete cycle)."""
        dependency_chain = ["ServiceA", "ServiceB", "ServiceC", "ServiceD"]
        error = DICircularDependencyError(dependency_chain=dependency_chain)

        assert "Circular dependency detected:" in str(error)
        assert error.context["dependency_chain"] == dependency_chain
        # Since there's no repeat, the circular_dependency should be the whole chain
        assert error.context["circular_dependency"] == dependency_chain

    def test_init_with_container(self):
        """Test initialization with a container."""
        dependency_chain = ["ServiceA", "ServiceB", "ServiceA"]
        mock_container = MockContainer()
        error = DICircularDependencyError(
            dependency_chain=dependency_chain, container=mock_container
        )

        assert "container_registrations" in error.context
        assert error.context["container_registrations"] == mock_container.registrations
