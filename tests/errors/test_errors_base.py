"""Tests for the Uno error handling system.

This module contains tests for the error foundation components,
including UnoError, error categories, and error wrapping.
"""

from __future__ import annotations

import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional, cast

import pytest

from uno.errors import (
    ErrorCategory,
    ErrorSeverity,
    UnoError,
    create_error,
    error_context_from_dict,
    wrap_exception,
)


class TestUnoErrorBase:
    """Tests for the base UnoError class."""

    def test_basic_error_creation(self) -> None:
        """Test creating a basic error with minimal arguments."""
        error = UnoError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.error_code == "UNKNOWN"
        assert error.category == ErrorCategory.INTERNAL
        assert error.severity == ErrorSeverity.ERROR
        assert isinstance(error.context, dict)
        assert len(error.context) == 0

    def test_error_with_context(self) -> None:
        """Test creating an error with context information."""
        error = UnoError(
            message="Invalid user input",
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            field_name="email",
            input_value="invalid@example",
        )

        assert error.message == "Invalid user input"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.WARNING
        assert error.context["field_name"] == "email"
        assert error.context["input_value"] == "invalid@example"

    def test_add_context(self) -> None:
        """Test adding context to an existing error."""
        error = UnoError("Connection failed")
        error.add_context("host", "db.example.com")
        error.add_context("port", 5432)

        assert error.context["host"] == "db.example.com"
        assert error.context["port"] == 5432

        # Test method chaining
        error.add_context("retry_count", 3).add_context("timeout", 30)
        assert error.context["retry_count"] == 3
        assert error.context["timeout"] == 30

    def test_to_dict(self) -> None:
        """Test converting an error to a dictionary."""
        error = UnoError(
            message="Resource not found",
            error_code="NOT_FOUND",
            category=ErrorCategory.API,
            resource_id="12345",
            resource_type="User",
        )

        error_dict = error.to_dict()

        assert error_dict["message"] == "Resource not found"
        assert error_dict["error_code"] == "NOT_FOUND"
        assert error_dict["category"] == "API"
        assert error_dict["severity"] == "ERROR"
        assert error_dict["context"]["resource_id"] == "12345"
        assert error_dict["context"]["resource_type"] == "User"
        assert "timestamp" in error_dict

    def test_wrap(self) -> None:
        """Test wrapping an exception in a UnoError."""
        original_exception = None
        try:
            raise ValueError("Invalid value")
        except ValueError as e:
            original_exception = e
            error = UnoError.wrap(
                e, error_code="WRAPPED_VALUE_ERROR", category=ErrorCategory.VALIDATION
            )

        assert error.message == "Invalid value"
        assert error.error_code == "WRAPPED_VALUE_ERROR"
        assert error.category == ErrorCategory.VALIDATION
        assert error.context["original_exception"] == "ValueError"
        assert error.__cause__ is original_exception


class TestErrorHelpers:
    """Tests for error helper functions."""

    def test_create_error(self) -> None:
        """Test creating an error with the create_error function."""
        error = create_error(
            message="Database query failed",
            error_code="DB_QUERY_FAILED",
            category=ErrorCategory.DB,
            severity=ErrorSeverity.CRITICAL,
            query="SELECT * FROM users",
            error_detail="Connection timeout",
        )

        assert error.message == "Database query failed"
        assert error.error_code == "DB_QUERY_FAILED"
        assert error.category == ErrorCategory.DB
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.context["query"] == "SELECT * FROM users"
        assert error.context["error_detail"] == "Connection timeout"

    def test_wrap_exception(self) -> None:
        """Test wrapping an exception with the wrap_exception function."""
        original_exception = None
        try:
            # Create a test exception
            raise KeyError("Unknown key")
        except KeyError as e:
            original_exception = e
            error = wrap_exception(
                exception=e,
                message="Failed to retrieve configuration",
                error_code="CONFIG_KEY_ERROR",
                category=ErrorCategory.CONFIG,
                severity=ErrorSeverity.WARNING,
                key_name="database_url",
            )

        assert error.message == "Failed to retrieve configuration"
        assert error.error_code == "CONFIG_KEY_ERROR"
        assert error.category == ErrorCategory.CONFIG
        assert error.severity == ErrorSeverity.WARNING
        assert error.context["key_name"] == "database_url"
        assert error.context["original_exception"] == "KeyError"
        assert error.__cause__ is original_exception

    def test_error_context_from_dict(self) -> None:
        """Test extracting context from a dictionary."""
        data = {
            "user_id": 123,
            "action": "login",
            "timestamp": datetime.now(),
            "successful": True,
            "null_value": None,
        }

        context = error_context_from_dict(data)

        # None values should be filtered out
        assert "null_value" not in context
        assert context["user_id"] == 123
        assert context["action"] == "login"
        assert context["successful"] is True
        assert "timestamp" in context


class TestDIErrors:
    """Tests for the DI-specific error classes."""

    def test_service_not_registered_error(self) -> None:
        """Test creating a ServiceNotRegisteredError."""
        from uno.di.errors import ServiceNotRegisteredError

        class IService:
            pass

        error = ServiceNotRegisteredError(IService)

        assert error.message == "Service IService is not registered"
        assert error.error_code == "DI_SERVICE_NOT_REGISTERED"
        assert error.category == ErrorCategory.DI
        assert error.context["interface_name"] == "IService"

    def test_type_mismatch_error(self) -> None:
        """Test creating a TypeMismatchError."""
        from uno.di.errors import TypeMismatchError

        class ILogger:
            pass

        class ConsoleWriter:
            pass

        error = TypeMismatchError(ILogger, ConsoleWriter)

        assert "Expected ILogger, got ConsoleWriter" in error.message
        assert error.error_code == "DI_TYPE_MISMATCH"
        assert error.category == ErrorCategory.DI
        assert error.context["expected_type"] == "ILogger"
        assert error.context["actual_type"] == "ConsoleWriter"

    def test_scope_error_factory_methods(self) -> None:
        """Test ScopeError factory methods."""
        from uno.di.errors import ScopeError

        class IRepository:
            pass

        # Test outside_scope factory
        error = ScopeError.outside_scope(IRepository)
        assert (
            "Cannot resolve scoped service IRepository outside a scope" in error.message
        )
        assert error.error_code == "DI_OUTSIDE_SCOPE"
        assert error.context["interface_name"] == "IRepository"

        # Test container_disposed factory
        error = ScopeError.container_disposed()
        assert "Container has been disposed" in error.message
        assert error.error_code == "DI_CONTAINER_DISPOSED"

        # Test scope_disposed factory
        error = ScopeError.scope_disposed()
        assert "Scope has been disposed" in error.message
        assert error.error_code == "DI_SCOPE_DISPOSED"
