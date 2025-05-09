# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Usage examples for the Uno error context enrichment system.

This module provides examples of how to use the error context enrichment
utilities provided by the Uno framework.
"""

import asyncio
import contextlib
import uuid
from typing import Dict, Any, Optional

from uno.errors import (
    UnoError,
    APIError,
    ValidationError,
    ErrorContext,
    with_error_context,
    with_dynamic_error_context,
    capture_error_context,
    add_global_context,
    add_thread_context,
    add_async_context,
    ErrorContextBridge,
    default_registry,
)


# =============================================================================
# Basic Examples
# =============================================================================


def basic_error_context_example():
    """Demonstrate basic error context usage."""
    try:
        # Use a context manager to add context
        with ErrorContext(feature="user_management", operation="create_user"):
            # This error will have the context added
            raise ValidationError(message="Username already exists")
    except UnoError as e:
        # Print the error with its context
        print(f"Error: {e.message}")
        print(f"Context: {e.context}")
        # The context will include: feature="user_management", operation="create_user"


def decorator_error_context_example():
    """Demonstrate error context decorators."""

    # Use a decorator to add context to a function
    @with_error_context(component="authentication", feature="login")
    def authenticate_user(username: str, password: str):
        """Authenticate a user with username and password."""
        # This error will have the component and feature in its context
        raise APIError(message="Authentication failed")

    try:
        authenticate_user("johndoe", "password123")
    except UnoError as e:
        # Print the error with its context
        print(f"Error: {e.message}")
        print(f"Context: {e.context}")
        # The context will include: component="authentication", feature="login"


def dynamic_error_context_example():
    """Demonstrate dynamic error context based on function arguments."""

    # Create a context factory that uses function arguments
    def user_context_factory(user_id: str, **kwargs) -> dict[str, Any]:
        return {
            "user_id": user_id,
            "operation": "get_user_profile",
            "request_id": str(uuid.uuid4()),
        }

    # Use the dynamic context decorator
    @with_dynamic_error_context(user_context_factory)
    def get_user_profile(user_id: str):
        """Get a user profile by ID."""
        # This error will have context from the factory function
        raise APIError(message=f"User {user_id} not found")

    try:
        get_user_profile("12345")
    except UnoError as e:
        # Print the error with its context
        print(f"Error: {e.message}")
        print(f"Context: {e.context}")
        # The context will include: user_id="12345", operation="get_user_profile", request_id=<uuid>


# =============================================================================
# Advanced Examples
# =============================================================================


def global_context_example():
    """Demonstrate global error context."""

    # Add global context (typically set once at application startup)
    add_global_context("environment", "production")
    add_global_context("application_version", "1.2.3")

    try:
        # This error will have the global context added
        raise UnoError(message="Something went wrong")
    except UnoError as e:
        # Print the error with its context
        print(f"Error: {e.message}")
        print(f"Context: {e.context}")
        # The context will include: environment="production", application_version="1.2.3"


def nested_context_example():
    """Demonstrate nested error contexts."""

    # Outer context
    with ErrorContext(service="order_service"):
        try:
            # Inner context (will be merged with outer)
            with ErrorContext(operation="place_order", order_id="ORD-12345"):
                # This error will have both contexts added
                raise APIError(message="Payment processing failed")
        except UnoError as e:
            # Print the error with its context
            print(f"Error: {e.message}")
            print(f"Context: {e.context}")
            # The context will include: service="order_service", operation="place_order", order_id="ORD-12345"


def registry_context_example():
    """Demonstrate using the context registry."""

    # Use a predefined context from the registry
    try:
        with default_registry.get_context(
            "request", request_id="REQ-12345", http_method="POST", path="/api/users"
        ):
            # This error will have the request context added
            raise APIError(message="Invalid request data")
    except UnoError as e:
        # Print the error with its context
        print(f"Error: {e.message}")
        print(f"Context: {e.context}")
        # The context will include: request_id="REQ-12345", http_method="POST", path="/api/users"


def bridge_context_example():
    """Demonstrate using the context bridge between sync and async code."""

    # Create a bridge
    bridge = ErrorContextBridge()

    # Add context to the bridge (in sync code)
    bridge.add("transaction_id", "TXN-12345")
    bridge.add("amount", 100.50)

    # Define an async function that will use the bridge
    async def process_payment():
        # Apply the bridge context in async code
        async with bridge.apply_async():
            # This error will have the bridge context added
            raise APIError(message="Payment gateway error")

    # Run the async function with the bridge context
    try:
        asyncio.run(process_payment())
    except UnoError as e:
        # Print the error with its context
        print(f"Error: {e.message}")
        print(f"Context: {e.context}")
        # The context will include: transaction_id="TXN-12345", amount=100.50


# =============================================================================
# Real-world Examples
# =============================================================================


class UserService:
    """Example user service with context enrichment."""

    def __init__(self, user_repository):
        self.user_repository = user_repository

    @with_error_context(service="user_service")
    def get_user(self, user_id: str) -> dict[str, Any]:
        """Get a user by ID with error context."""
        try:
            return self.user_repository.get_by_id(user_id)
        except Exception as e:
            # Wrap and enrich any repository exception
            raise APIError(
                message=f"Failed to get user with ID {user_id}",
                user_id=user_id,
            ) from e

    @with_error_context(service="user_service")
    def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Create a user with error context."""
        # Validate the user data
        self._validate_user_data(user_data)

        # Additional context for this specific operation
        with ErrorContext(operation="create_user"):
            try:
                return self.user_repository.create(user_data)
            except Exception as e:
                # Wrap and enrich any repository exception
                raise APIError(
                    message="Failed to create user",
                    user_data=user_data,
                ) from e

    @capture_error_context  # This will add current context to any raised error
    def _validate_user_data(self, user_data: dict[str, Any]) -> None:
        """Validate user data with error context capture."""
        required_fields = ["username", "email", "password"]
        for field in required_fields:
            if field not in user_data:
                raise ValidationError(
                    message=f"Missing required field: {field}",
                    field_name=field,
                )


# Example of using error context in FastAPI
def fastapi_example_code():
    """
    This is not meant to be run, just shows how to use with FastAPI.

    ```python
    from fastapi import FastAPI, Depends, HTTPException
    from uno.errors import add_error_context_middleware, ErrorContext, UnoError, APIError

    app = FastAPI()

    # Add the error context middleware
    add_error_context_middleware(app)

    # Define an endpoint
    @app.get("/users/{user_id}")
    async def get_user(user_id: str):
        # Any UnoError raised here will have request context already
        # You can add more specific context
        async with ErrorContext(operation="get_user"):
            try:
                # Your logic here
                # ...
                if not user:
                    raise APIError(message=f"User not found: {user_id}")
                return user
            except UnoError as e:
                # Convert to HTTPException
                raise HTTPException(status_code=404, detail=str(e))
    ```
    """
    pass
