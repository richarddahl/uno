# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
External key management provider integration for the Uno configuration system.

This module defines the protocol for external key management systems (KMS, Vault, etc.)
and provides a registration system for different providers.
"""

from __future__ import annotations

import asyncio
import logging
import os
from enum import Enum
from typing import Any, Callable, ClassVar, Protocol, cast

from uno.config.errors import SecureValueError, CONFIG_SECURE_KEY_ERROR
from uno.config.protocols import SecureAccessibleProtocol

logger = logging.getLogger("uno.config.key_provider")


class KeyOperation(str, Enum):
    """Type of key operation being performed."""

    CREATE = "create"  # Create a new key
    GET = "get"  # Get an existing key
    ROTATE = "rotate"  # Rotate a key
    DELETE = "delete"  # Delete a key
    LIST = "list"  # List available keys
    ENCRYPT = "encrypt"  # Encrypt data using key
    DECRYPT = "decrypt"  # Decrypt data using key


class KeyProviderProtocol(Protocol):
    """Protocol defining the interface for key management providers.

    This protocol is NOT runtime_checkable and should be used for
    static type checking only.
    """

    @property
    def name(self) -> str:
        """Get the name of this provider."""
        ...

    @property
    def description(self) -> str:
        """Get a human-readable description of this provider."""
        ...

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the provider with configuration.

        Args:
            config: Provider-specific configuration options

        Raises:
            SecureValueError: If initialization fails
        """
        ...

    async def is_available(self) -> bool:
        """Check if the provider is available and properly configured.

        Returns:
            True if the provider is available, False otherwise
        """
        ...

    async def generate_key(
        self, key_id: str | None = None, **options: Any
    ) -> tuple[str, bytes]:
        """Generate a new key.

        Args:
            key_id: Optional identifier for the key (provider may generate one if None)
            **options: Provider-specific options

        Returns:
            Tuple of (key_version, key_bytes)

        Raises:
            SecureValueError: If key generation fails
        """
        ...

    async def get_key(self, key_id: str, **options: Any) -> bytes:
        """Get an existing key.

        Args:
            key_id: Identifier for the key
            **options: Provider-specific options

        Returns:
            Key bytes

        Raises:
            SecureValueError: If key retrieval fails or key doesn't exist
        """
        ...

    async def delete_key(self, key_id: str, **options: Any) -> None:
        """Delete a key.

        Args:
            key_id: Identifier for the key
            **options: Provider-specific options

        Raises:
            SecureValueError: If key deletion fails
        """
        ...

    async def list_keys(self, **options: Any) -> list[str]:
        """List available keys.

        Args:
            **options: Provider-specific options

        Returns:
            List of key identifiers

        Raises:
            SecureValueError: If key listing fails
        """
        ...

    async def rotate_key(self, key_id: str, **options: Any) -> tuple[str, bytes]:
        """Rotate a key.

        Args:
            key_id: Identifier for the key to rotate
            **options: Provider-specific options

        Returns:
            Tuple of (new_key_version, new_key_bytes)

        Raises:
            SecureValueError: If key rotation fails
        """
        ...


class KeyDistributionProtocol(Protocol):
    """Protocol defining the interface for key distribution systems.

    This protocol is NOT runtime_checkable and should be used for
    static type checking only.
    """

    @property
    def name(self) -> str:
        """Get the name of this distribution system."""
        ...

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the distribution system with configuration.

        Args:
            config: System-specific configuration options
        """
        ...

    async def announce_key(self, key_id: str, key_version: str) -> None:
        """Announce a new key version to other instances.

        Args:
            key_id: Identifier for the key
            key_version: Version of the key
        """
        ...

    async def get_latest_key_version(self, key_id: str) -> str | None:
        """Get the latest version of a key known to the system.

        Args:
            key_id: Identifier for the key

        Returns:
            Latest key version or None if not found
        """
        ...

    async def acquire_rotation_lock(self, key_id: str, ttl: int = 60) -> bool:
        """Acquire a distributed lock for key rotation.

        Args:
            key_id: Identifier for the key
            ttl: Time-to-live for the lock in seconds

        Returns:
            True if lock was acquired, False otherwise
        """
        ...

    async def release_rotation_lock(self, key_id: str) -> None:
        """Release a distributed lock for key rotation.

        Args:
            key_id: Identifier for the key
        """
        ...


class ProviderRegistry:
    """Registry for key management providers.

    This registry allows applications to discover and use different
    key management providers.
    """

    _providers: ClassVar[dict[str, type[KeyProviderProtocol]]] = {}
    _distribution_systems: ClassVar[dict[str, type[KeyDistributionProtocol]]] = {}
    _initialized_providers: ClassVar[dict[str, KeyProviderProtocol]] = {}
    _initialized_distribution: ClassVar[KeyDistributionProtocol | None] = None

    @classmethod
    def register_provider(
        cls, provider_type: type[KeyProviderProtocol], name: str | None = None
    ) -> None:
        """Register a provider type.

        Args:
            provider_type: The provider class to register
            name: Optional name to register under (defaults to class name)
        """
        provider_name = name or provider_type.__name__
        cls._providers[provider_name] = provider_type
        logger.debug(f"Registered key provider: {provider_name}")

    @classmethod
    def register_distribution_system(
        cls, system_type: type[KeyDistributionProtocol], name: str | None = None
    ) -> None:
        """Register a distribution system type.

        Args:
            system_type: The distribution system class to register
            name: Optional name to register under (defaults to class name)
        """
        system_name = name or system_type.__name__
        cls._distribution_systems[system_name] = system_type
        logger.debug(f"Registered distribution system: {system_name}")

    @classmethod
    def get_provider_type(cls, name: str) -> type[KeyProviderProtocol] | None:
        """Get a provider type by name.

        Args:
            name: Name of the provider type

        Returns:
            Provider class or None if not found
        """
        return cls._providers.get(name)

    @classmethod
    def get_distribution_system_type(
        cls, name: str
    ) -> type[KeyDistributionProtocol] | None:
        """Get a distribution system type by name.

        Args:
            name: Name of the distribution system type

        Returns:
            Distribution system class or None if not found
        """
        return cls._distribution_systems.get(name)

    @classmethod
    def list_providers(cls) -> list[str]:
        """List registered provider types.

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())

    @classmethod
    def list_distribution_systems(cls) -> list[str]:
        """List registered distribution system types.

        Returns:
            List of distribution system names
        """
        return list(cls._distribution_systems.keys())

    @classmethod
    async def initialize_provider(
        cls, name: str, config: dict[str, Any] | None = None
    ) -> KeyProviderProtocol:
        """Initialize a provider instance.

        Args:
            name: Name of the provider to initialize
            config: Provider-specific configuration

        Returns:
            Initialized provider instance

        Raises:
            SecureValueError: If provider initialization fails
        """
        # Check if already initialized
        if name in cls._initialized_providers:
            return cls._initialized_providers[name]

        # Get provider type
        provider_type = cls.get_provider_type(name)
        if not provider_type:
            raise SecureValueError(
                f"Unknown key provider: {name}",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        # Create instance
        try:
            provider = provider_type()
            await provider.initialize(config)

            # Check if provider is available
            if not await provider.is_available():
                raise SecureValueError(
                    f"Key provider {name} is not available",
                    code=CONFIG_SECURE_KEY_ERROR,
                )

            # Cache the instance
            cls._initialized_providers[name] = provider
            return provider

        except Exception as e:
            raise SecureValueError(
                f"Failed to initialize key provider {name}: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    @classmethod
    async def initialize_distribution(
        cls, name: str, config: dict[str, Any] | None = None
    ) -> KeyDistributionProtocol:
        """Initialize a distribution system instance.

        Args:
            name: Name of the distribution system to initialize
            config: System-specific configuration

        Returns:
            Initialized distribution system instance

        Raises:
            SecureValueError: If distribution system initialization fails
        """
        # Check if already initialized
        if cls._initialized_distribution is not None:
            return cls._initialized_distribution

        # Get distribution system type
        system_type = cls.get_distribution_system_type(name)
        if not system_type:
            raise SecureValueError(
                f"Unknown distribution system: {name}",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        # Create instance
        try:
            system = system_type()
            await system.initialize(config)

            # Cache the instance
            cls._initialized_distribution = system
            return system

        except Exception as e:
            raise SecureValueError(
                f"Failed to initialize distribution system {name}: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    @classmethod
    def get_provider(cls, name: str) -> KeyProviderProtocol | None:
        """Get an initialized provider instance.

        Args:
            name: Name of the provider

        Returns:
            Provider instance or None if not initialized
        """
        return cls._initialized_providers.get(name)

    @classmethod
    def get_distribution_system(cls) -> KeyDistributionProtocol | None:
        """Get the initialized distribution system instance.

        Returns:
            Distribution system instance or None if not initialized
        """
        return cls._initialized_distribution

    @classmethod
    def clear(cls) -> None:
        """Clear all initialized providers and distribution systems.

        This is primarily used for testing and resets the registry state.
        """
        cls._initialized_providers.clear()
        cls._initialized_distribution = None


class KeyManagementConfig:
    """Configuration for key management system."""

    def __init__(
        self,
        provider: str,
        provider_config: dict[str, Any] | None = None,
        distribution_system: str | None = None,
        distribution_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize key management configuration.

        Args:
            provider: Name of key provider to use
            provider_config: Provider-specific configuration
            distribution_system: Optional distribution system to use
            distribution_config: Distribution system configuration
        """
        self.provider = provider
        self.provider_config = provider_config or {}
        self.distribution_system = distribution_system
        self.distribution_config = distribution_config or {}


async def setup_key_management(config: KeyManagementConfig) -> None:
    """Set up the key management system.

    This initializes the specified provider and distribution system
    according to the provided configuration.

    Args:
        config: Key management configuration

    Raises:
        SecureValueError: If setup fails
    """
    # Initialize provider
    await ProviderRegistry.initialize_provider(config.provider, config.provider_config)

    # Initialize distribution system if specified
    if config.distribution_system:
        await ProviderRegistry.initialize_distribution(
            config.distribution_system, config.distribution_config
        )

    logger.info(
        f"Key management initialized with provider: {config.provider}"
        + (
            f", distribution: {config.distribution_system}"
            if config.distribution_system
            else ""
        )
    )


async def get_managed_key(key_id: str, **options: Any) -> tuple[str, bytes]:
    """Get a managed key from the current provider.

    This is a high-level function that retrieves a key from the current provider,
    handling distribution coordination if configured.

    Args:
        key_id: Identifier for the key
        **options: Provider-specific options

    Returns:
        Tuple of (key_version, key_bytes)

    Raises:
        SecureValueError: If key retrieval fails
    """
    # Check for initialized provider
    if not ProviderRegistry._initialized_providers:
        raise SecureValueError(
            "No key provider initialized. Call setup_key_management() first.",
            code=CONFIG_SECURE_KEY_ERROR,
        )

    # Get the first provider (we currently only support one active provider)
    provider_name = next(iter(ProviderRegistry._initialized_providers.keys()))
    provider = ProviderRegistry._initialized_providers[provider_name]

    # Get distribution system if available
    distribution = ProviderRegistry._initialized_distribution

    try:
        # If we have a distribution system, check for the latest version
        latest_version = None
        if distribution:
            latest_version = await distribution.get_latest_key_version(key_id)

        # Generate a version ID based on timestamp if we don't have one
        import time
        import uuid

        version = f"v{int(time.time())}-{uuid.uuid4().hex[:6]}"

        # Try to get the key
        try:
            key_bytes = await provider.get_key(
                key_id, version=latest_version, **options
            )
            # If successful and we have a latest version, use that
            if latest_version:
                version = latest_version
        except SecureValueError:
            # Key doesn't exist, generate a new one
            version, key_bytes = await provider.generate_key(key_id, **options)

            # Announce the new key if we have a distribution system
            if distribution:
                await distribution.announce_key(key_id, version)

        return version, key_bytes

    except Exception as e:
        raise SecureValueError(
            f"Failed to get managed key {key_id}: {e}",
            code=CONFIG_SECURE_KEY_ERROR,
        ) from e


async def rotate_managed_key(key_id: str, **options: Any) -> tuple[str, bytes]:
    """Rotate a managed key using the current provider.

    This is a high-level function that rotates a key using the current provider,
    handling distributed coordination if configured.

    Args:
        key_id: Identifier for the key to rotate
        **options: Provider-specific options

    Returns:
        Tuple of (new_key_version, new_key_bytes)

    Raises:
        SecureValueError: If key rotation fails
    """
    # Check for initialized provider
    if not ProviderRegistry._initialized_providers:
        raise SecureValueError(
            "No key provider initialized. Call setup_key_management() first.",
            code=CONFIG_SECURE_KEY_ERROR,
        )

    # Get the first provider (we currently only support one active provider)
    provider_name = next(iter(ProviderRegistry._initialized_providers.keys()))
    provider = ProviderRegistry._initialized_providers[provider_name]

    # Get distribution system if available
    distribution = ProviderRegistry._initialized_distribution

    try:
        # Acquire rotation lock if we have a distribution system
        lock_acquired = True
        if distribution:
            lock_acquired = await distribution.acquire_rotation_lock(key_id)
            if not lock_acquired:
                # Another instance is rotating the key, wait and get the latest version
                for _ in range(10):  # Try up to 10 times
                    await asyncio.sleep(2)  # Wait 2 seconds between checks
                    latest_version = await distribution.get_latest_key_version(key_id)
                    if latest_version:
                        # Another instance successfully rotated the key
                        key_bytes = await provider.get_key(
                            key_id, version=latest_version
                        )
                        return latest_version, key_bytes

                # If we get here, something went wrong with the other instance's rotation
                raise SecureValueError(
                    f"Failed to get rotated key {key_id} from another instance",
                    code=CONFIG_SECURE_KEY_ERROR,
                )

        try:
            # Perform the rotation
            new_version, new_key = await provider.rotate_key(key_id, **options)

            # Announce the new key if we have a distribution system
            if distribution:
                await distribution.announce_key(key_id, new_version)
                # Release the lock
                await distribution.release_rotation_lock(key_id)

            return new_version, new_key

        finally:
            # Make sure we release the lock if we acquired it
            if distribution and lock_acquired:
                await distribution.release_rotation_lock(key_id)

    except Exception as e:
        raise SecureValueError(
            f"Failed to rotate managed key {key_id}: {e}",
            code=CONFIG_SECURE_KEY_ERROR,
        ) from e
