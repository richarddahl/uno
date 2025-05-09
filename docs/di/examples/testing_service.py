"""
Testing example for the Uno DI system.

This example demonstrates:
1. Service mocking
2. Service contracts
3. Service testing
4. Test mode configuration
5. Service validation
"""

from typing import Protocol, List, Dict, Any
from dataclasses import dataclass
from unittest import TestCase, main
from uno.di.decorators import (
    service,
    singleton,
    ServiceMock,
    ServiceContract,
    ServiceScope,
    ServiceVersion,
)
from uno.di.service_collection import ServiceCollection
from uno.di.service_provider import ServiceProvider
from uno.di.errors import ServiceConfigurationError


# Define interfaces
class IUserService(Protocol):
    """Interface for user services."""

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """Get a user by ID."""
        ...

    async def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new user."""
        ...


# Define service contracts
class UserServiceContract(ServiceContract):
    """Contract for user service validation."""

    def validate_get_user(self, user_id: str) -> None:
        """Validate get_user parameters."""
        if not user_id:
            raise ServiceConfigurationError("User ID is required")
        if not isinstance(user_id, str):
            raise ServiceConfigurationError("User ID must be a string")

    def validate_create_user(self, user_data: dict[str, Any]) -> None:
        """Validate create_user parameters."""
        if not user_data:
            raise ServiceConfigurationError("User data is required")
        if "name" not in user_data:
            raise ServiceConfigurationError("User name is required")
        if "email" not in user_data:
            raise ServiceConfigurationError("User email is required")


# Define service options
@dataclass
class UserServiceOptions:
    """Options for user service."""

    max_users: int = 1000
    allow_duplicate_emails: bool = False

    def validate(self) -> None:
        """Validate user service options."""
        if self.max_users < 1:
            raise ServiceConfigurationError("Max users must be positive")


# Implement service
@service(
    interface=IUserService,
    scope=ServiceScope.SINGLETON,
    options_type=UserServiceOptions,
    version="1.0.0",
    contract=UserServiceContract(),
)
class UserService:
    """User service implementation."""

    def __init__(self, options: UserServiceOptions):
        self.options = options
        self.users: dict[str, dict[str, Any]] = {}
        self._version = ServiceVersion("1.0.0")

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """Get a user by ID."""
        return self.users.get(user_id, {})

    async def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new user."""
        if len(self.users) >= self.options.max_users:
            raise ServiceConfigurationError("Maximum number of users reached")

        if not self.options.allow_duplicate_emails:
            for user in self.users.values():
                if user["email"] == user_data["email"]:
                    raise ServiceConfigurationError("Email already exists")

        user_id = f"user_{len(self.users) + 1}"
        self.users[user_id] = user_data
        return {"id": user_id, **user_data}


# Implement service mock
class UserServiceMock(ServiceMock):
    """Mock implementation of user service."""

    def __init__(self):
        self.users: dict[str, dict[str, Any]] = {}
        self.get_user_calls = 0
        self.create_user_calls = 0

    async def get_user(self, user_id: str) -> dict[str, Any]:
        """Mock get_user implementation."""
        self.get_user_calls += 1
        return self.users.get(user_id, {})

    async def create_user(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Mock create_user implementation."""
        self.create_user_calls += 1
        user_id = f"mock_user_{len(self.users) + 1}"
        self.users[user_id] = user_data
        return {"id": user_id, **user_data}


# Test cases
class UserServiceTests(TestCase):
    """Test cases for user service."""

    def setUp(self):
        """Set up test environment."""
        self.services = ServiceCollection()
        self.services.add_singleton(IUserService, UserService)
        self.services.configure[UserServiceOptions](
            lambda options: {"max_users": 10, "allow_duplicate_emails": False}
        )
        self.provider = ServiceProvider(self.services)

    def test_get_user(self):
        """Test get_user method."""

        async def run_test():
            service = self.provider.get_service(IUserService)

            # Test with non-existent user
            result = await service.get_user("nonexistent")
            self.assertEqual(result, {})

            # Test with existing user
            user_data = {"name": "Test User", "email": "test@example.com"}
            created = await service.create_user(user_data)
            result = await service.get_user(created["id"])
            self.assertEqual(result["name"], user_data["name"])
            self.assertEqual(result["email"], user_data["email"])

        import asyncio

        asyncio.run(run_test())

    def test_create_user(self):
        """Test create_user method."""

        async def run_test():
            service = self.provider.get_service(IUserService)

            # Test valid user creation
            user_data = {"name": "Test User", "email": "test@example.com"}
            result = await service.create_user(user_data)
            self.assertEqual(result["name"], user_data["name"])
            self.assertEqual(result["email"], user_data["email"])
            self.assertTrue("id" in result)

            # Test duplicate email
            with self.assertRaises(ServiceConfigurationError):
                await service.create_user(user_data)

            # Test max users limit
            for i in range(9):  # Already created 1 user
                await service.create_user(
                    {"name": f"User {i}", "email": f"user{i}@example.com"}
                )

            with self.assertRaises(ServiceConfigurationError):
                await service.create_user(
                    {"name": "Extra User", "email": "extra@example.com"}
                )

        import asyncio

        asyncio.run(run_test())

    def test_mock_service(self):
        """Test service with mock implementation."""

        async def run_test():
            # Create service collection with mock
            services = ServiceCollection()
            services.add_singleton(IUserService, UserServiceMock)
            provider = ServiceProvider(services)

            # Get mock service
            service = provider.get_service(IUserService)
            self.assertIsInstance(service, UserServiceMock)

            # Test mock implementation
            user_data = {"name": "Test User", "email": "test@example.com"}
            result = await service.create_user(user_data)
            self.assertEqual(result["name"], user_data["name"])
            self.assertEqual(service.create_user_calls, 1)

            result = await service.get_user(result["id"])
            self.assertEqual(result["name"], user_data["name"])
            self.assertEqual(service.get_user_calls, 1)

        import asyncio

        asyncio.run(run_test())

    def test_service_contract(self):
        """Test service contract validation."""

        async def run_test():
            service = self.provider.get_service(IUserService)

            # Test invalid user ID
            with self.assertRaises(ServiceConfigurationError):
                await service.get_user("")

            # Test invalid user data
            with self.assertRaises(ServiceConfigurationError):
                await service.create_user({})

            with self.assertRaises(ServiceConfigurationError):
                await service.create_user({"name": "Test User"})

            with self.assertRaises(ServiceConfigurationError):
                await service.create_user({"email": "test@example.com"})

        import asyncio

        asyncio.run(run_test())


if __name__ == "__main__":
    main()
