# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
HashiCorp Vault provider implementation.

This module provides integration with HashiCorp Vault for secure key management.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from typing import Any, cast

from uno.config.errors import SecureValueError, CONFIG_SECURE_KEY_ERROR
from uno.config.key_provider import KeyProviderProtocol

logger = logging.getLogger("uno.config.providers.vault")


class VaultProvider:
    """HashiCorp Vault provider implementation."""

    def __init__(self) -> None:
        """Initialize HashiCorp Vault provider."""
        self._client = None
        self._url = None
        self._token = None
        self._transit_mount = None
        self._kv_mount = None
        self._initialized = False

    @property
    def name(self) -> str:
        """Get the name of this provider."""
        return "vault"

    @property
    def description(self) -> str:
        """Get a human-readable description of this provider."""
        return "HashiCorp Vault provider for secure key management"

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the provider with Vault credentials and configuration.

        Args:
            config: Vault-specific configuration options including:
                   - url: Vault server URL (required)
                   - token: Authentication token (required unless auth_method specified)
                   - auth_method: Authentication method (token, approle, kubernetes)
                   - role_id: AppRole role ID (required if auth_method=approle)
                   - secret_id: AppRole secret ID (required if auth_method=approle)
                   - transit_mount: Transit engine mount point (default: transit)
                   - kv_mount: KV engine mount point (default: secret)
                   - kv_version: KV engine version (1 or 2, default: 2)

        Raises:
            SecureValueError: If initialization fails
        """
        config = config or {}

        # Check for hvac
        try:
            import hvac
        except ImportError:
            raise SecureValueError(
                "hvac is required for Vault provider. Install with 'pip install hvac'.",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        # Get Vault URL (required)
        self._url = config.get("url") or os.environ.get("VAULT_ADDR")
        if not self._url:
            raise SecureValueError(
                "Vault URL is required. Provide it in config or set VAULT_ADDR env var.",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        # Get auth method
        auth_method = config.get("auth_method", "token")

        # Set up token-based authentication
        if auth_method == "token":
            self._token = config.get("token") or os.environ.get("VAULT_TOKEN")
            if not self._token:
                raise SecureValueError(
                    "Vault token is required for token auth. Provide it in config or set VAULT_TOKEN env var.",
                    code=CONFIG_SECURE_KEY_ERROR,
                )

        # Get engine mount points
        self._transit_mount = config.get("transit_mount", "transit")
        self._kv_mount = config.get("kv_mount", "secret")
        self._kv_version = config.get("kv_version", 2)

        # Create Vault client
        loop = asyncio.get_event_loop()
        try:
            # Create the client in a thread to avoid blocking
            def create_client():
                client = hvac.Client(url=self._url, token=self._token)
                # Ensure client is authenticated
                if not client.is_authenticated():
                    raise SecureValueError(
                        "Failed to authenticate with Vault server",
                        code=CONFIG_SECURE_KEY_ERROR,
                    )
                return client

            self._client = await loop.run_in_executor(None, create_client)

            # Set up engines if not already enabled
            if config.get("initialize_engines", False):
                await self._ensure_engines_enabled()

            self._initialized = True

        except Exception as e:
            raise SecureValueError(
                f"Failed to initialize Vault client: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def _ensure_engines_enabled(self) -> None:
        """Ensure transit and KV engines are enabled.

        This requires policy permissions to manage Vault mounts.
        """
        loop = asyncio.get_event_loop()

        try:
            # Check if Transit engine is enabled
            mounts = await loop.run_in_executor(
                None, lambda: self._client.sys.list_mounted_secrets_engines()
            )

            # Enable Transit engine if not already enabled
            transit_path = f"{self._transit_mount}/"
            if transit_path not in mounts:
                await loop.run_in_executor(
                    None,
                    lambda: self._client.sys.enable_secrets_engine(
                        backend_type="transit", path=self._transit_mount
                    ),
                )
                logger.info(f"Enabled Transit engine at {self._transit_mount}")

            # Enable KV engine if not already enabled
            kv_path = f"{self._kv_mount}/"
            if kv_path not in mounts:
                await loop.run_in_executor(
                    None,
                    lambda: self._client.sys.enable_secrets_engine(
                        backend_type="kv",
                        path=self._kv_mount,
                        options={"version": self._kv_version},
                    ),
                )
                logger.info(
                    f"Enabled KV engine (v{self._kv_version}) at {self._kv_mount}"
                )

        except Exception as e:
            logger.warning(f"Could not initialize Vault engines: {e}")
            # Continue without failing - this operation is optional

    async def is_available(self) -> bool:
        """Check if Vault is available with the provided configuration.

        Returns:
            True if Vault is available, False otherwise
        """
        if not self._initialized or not self._client:
            return False

        try:
            # Try to get health status
            loop = asyncio.get_event_loop()
            health = await loop.run_in_executor(
                None, lambda: self._client.sys.read_health_status()
            )

            # Check if server is initialized and unsealed
            if health["initialized"] and not health["sealed"]:
                # Verify authentication
                return self._client.is_authenticated()
            return False

        except Exception as e:
            logger.warning(f"Vault not available: {e}")
            return False

    async def generate_key(
        self, key_id: str | None = None, **options: Any
    ) -> tuple[str, bytes]:
        """Generate a new key using Vault.

        This method uses Vault's Transit engine to generate a key,
        then wraps it for secure storage.

        Args:
            key_id: Optional identifier for the key
            **options: Provider-specific options including:
                      - key_type: Type of key to generate (aes256-gcm96, ed25519, etc.)
                      - exportable: Whether the key should be exportable
                      - derived: Whether key derivation should be enabled

        Returns:
            Tuple of (key_version, key_bytes)

        Raises:
            SecureValueError: If key generation fails
        """
        if not self._initialized or not self._client:
            raise SecureValueError(
                "Vault provider not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            # Use the provided key ID or generate a default one
            key_name = key_id or f"uno-key-{uuid.uuid4().hex[:8]}"

            # Generate a secure random key
            import os

            key_bytes = os.urandom(32)  # 256-bit key

            # Generate a version ID based on timestamp and random component
            version = f"vault-{int(time.time())}-{uuid.uuid4().hex[:6]}"

            # Store the key in Vault's KV store
            await self._store_key(key_name, version, key_bytes, options)

            return version, key_bytes

        except Exception as e:
            raise SecureValueError(
                f"Failed to generate key in Vault: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def _store_key(
        self, key_name: str, version: str, key_bytes: bytes, metadata: dict[str, Any]
    ) -> None:
        """Store a key in Vault's KV store.

        Args:
            key_name: Name of the key
            version: Version identifier
            key_bytes: Key data to store
            metadata: Additional metadata about the key

        Raises:
            SecureValueError: If storage fails
        """
        if not self._initialized or not self._client:
            raise SecureValueError(
                "Vault provider not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            loop = asyncio.get_event_loop()

            # Encode the key
            key_b64 = base64.b64encode(key_bytes).decode("utf-8")

            # Prepare data for storage
            data = {
                "key": key_b64,
                "version": version,
                "metadata": metadata,
                "created_at": time.time(),
            }

            # Store in KV store
            path = f"uno/keys/{key_name}/{version}"

            if self._kv_version == 2:
                # KV version 2 storage
                await loop.run_in_executor(
                    None,
                    lambda: self._client.secrets.kv.v2.create_or_update_secret(
                        path=path,
                        mount_point=self._kv_mount,
                        secret=data,
                    ),
                )
            else:
                # KV version 1 storage
                await loop.run_in_executor(
                    None,
                    lambda: self._client.secrets.kv.v1.create_or_update_secret(
                        path=path,
                        mount_point=self._kv_mount,
                        secret=data,
                    ),
                )

        except Exception as e:
            raise SecureValueError(
                f"Failed to store key in Vault: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def get_key(self, key_id: str, **options: Any) -> bytes:
        """Get an existing key from Vault.

        Args:
            key_id: Identifier for the key
            **options: Provider-specific options including:
                      - version: Specific key version to get

        Returns:
            Key bytes

        Raises:
            SecureValueError: If key retrieval fails or key doesn't exist
        """
        if not self._initialized or not self._client:
            raise SecureValueError(
                "Vault provider not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            # Get desired version
            version = options.get("version")

            if version:
                # Get specific version
                key_bytes = await self._get_key_by_version(key_id, version)
            else:
                # Get latest version
                key_bytes = await self._get_latest_key(key_id)

            return key_bytes

        except Exception as e:
            raise SecureValueError(
                f"Failed to get key from Vault: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def _get_key_by_version(self, key_name: str, version: str) -> bytes:
        """Get a specific version of a key from Vault's KV store.

        Args:
            key_name: Name of the key
            version: Version identifier

        Returns:
            Key bytes

        Raises:
            SecureValueError: If key retrieval fails
        """
        loop = asyncio.get_event_loop()

        try:
            # Construct path
            path = f"uno/keys/{key_name}/{version}"

            # Get from KV store
            if self._kv_version == 2:
                # KV version 2 retrieval
                response = await loop.run_in_executor(
                    None,
                    lambda: self._client.secrets.kv.v2.read_secret_version(
                        path=path,
                        mount_point=self._kv_mount,
                    ),
                )
                data = response["data"]["data"]
            else:
                # KV version 1 retrieval
                response = await loop.run_in_executor(
                    None,
                    lambda: self._client.secrets.kv.v1.read_secret(
                        path=path,
                        mount_point=self._kv_mount,
                    ),
                )
                data = response["data"]

            # Decode key
            if "key" not in data:
                raise SecureValueError(
                    f"Invalid key data format for {key_name}/{version}",
                    code=CONFIG_SECURE_KEY_ERROR,
                )

            key_b64 = data["key"]
            key_bytes = base64.b64decode(key_b64)

            return key_bytes

        except Exception as e:
            raise SecureValueError(
                f"Failed to retrieve key {key_name}/{version} from Vault: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def _get_latest_key(self, key_name: str) -> bytes:
        """Get the latest version of a key from Vault's KV store.

        Args:
            key_name: Name of the key

        Returns:
            Key bytes

        Raises:
            SecureValueError: If key retrieval fails
        """
        loop = asyncio.get_event_loop()

        try:
            # List versions
            prefix = f"uno/keys/{key_name}/"

            # Get versions from KV store (implementation depends on KV version)
            if self._kv_version == 2:
                # For KV v2, we need to list keys with prefix
                # The metadata endpoint gives us version info
                response = await loop.run_in_executor(
                    None,
                    lambda: self._client.secrets.kv.v2.list_secrets(
                        path=prefix,
                        mount_point=self._kv_mount,
                    ),
                )
                versions = response.get("data", {}).get("keys", [])
            else:
                # For KV v1, we just list keys
                response = await loop.run_in_executor(
                    None,
                    lambda: self._client.secrets.kv.v1.list_secrets(
                        path=prefix,
                        mount_point=self._kv_mount,
                    ),
                )
                versions = response.get("data", {}).get("keys", [])

            if not versions:
                raise SecureValueError(
                    f"No versions found for key {key_name}",
                    code=CONFIG_SECURE_KEY_ERROR,
                )

            # Find latest version (by timestamp in version ID)
            latest_version = None
            latest_timestamp = 0

            for ver in versions:
                # Extract timestamp from version ID format: vault-{timestamp}-{uuid}
                parts = ver.split("-")
                if len(parts) >= 2 and parts[0] == "vault":
                    try:
                        timestamp = int(parts[1])
                        if timestamp > latest_timestamp:
                            latest_timestamp = timestamp
                            latest_version = ver
                    except (ValueError, IndexError):
                        continue

            if not latest_version:
                # If we couldn't determine by timestamp, use the first one
                latest_version = versions[0]

            # Get the key with the latest version
            return await self._get_key_by_version(key_name, latest_version)

        except Exception as e:
            raise SecureValueError(
                f"Failed to retrieve latest version of key {key_name} from Vault: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def delete_key(self, key_id: str, **options: Any) -> None:
        """Delete a key from Vault.

        Args:
            key_id: Identifier for the key
            **options: Provider-specific options including:
                      - version: Specific key version to delete (optional)

        Raises:
            SecureValueError: If key deletion fails
        """
        if not self._initialized or not self._client:
            raise SecureValueError(
                "Vault provider not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            # Get desired version
            version = options.get("version")

            loop = asyncio.get_event_loop()

            if version:
                # Delete specific version
                path = f"uno/keys/{key_id}/{version}"

                if self._kv_version == 2:
                    # KV version 2 deletion (metadata remains, data is removed)
                    await loop.run_in_executor(
                        None,
                        lambda: self._client.secrets.kv.v2.delete_secret_versions(
                            path=path,
                            mount_point=self._kv_mount,
                            versions=[version],
                        ),
                    )
                else:
                    # KV version 1 deletion
                    await loop.run_in_executor(
                        None,
                        lambda: self._client.secrets.kv.v1.delete_secret(
                            path=path,
                            mount_point=self._kv_mount,
                        ),
                    )
            else:
                # Delete all versions
                prefix = f"uno/keys/{key_id}"

                if self._kv_version == 2:
                    # KV version 2 deletion (metadata and all versions)
                    await loop.run_in_executor(
                        None,
                        lambda: self._client.secrets.kv.v2.delete_metadata_and_all_versions(
                            path=prefix,
                            mount_point=self._kv_mount,
                        ),
                    )
                else:
                    # For KV v1, we need to list and delete individual keys
                    response = await loop.run_in_executor(
                        None,
                        lambda: self._client.secrets.kv.v1.list_secrets(
                            path=prefix,
                            mount_point=self._kv_mount,
                        ),
                    )

                    versions = response.get("data", {}).get("keys", [])
                    for ver in versions:
                        ver_path = f"{prefix}/{ver}"
                        await loop.run_in_executor(
                            None,
                            lambda: self._client.secrets.kv.v1.delete_secret(
                                path=ver_path,
                                mount_point=self._kv_mount,
                            ),
                        )

        except Exception as e:
            raise SecureValueError(
                f"Failed to delete key from Vault: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def list_keys(self, **options: Any) -> list[str]:
        """List available keys in Vault.

        Args:
            **options: Provider-specific options including:
                      - prefix: Optional prefix to filter by

        Returns:
            List of key identifiers

        Raises:
            SecureValueError: If key listing fails
        """
        if not self._initialized or not self._client:
            raise SecureValueError(
                "Vault provider not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            # Get optional prefix
            prefix = options.get("prefix", "")

            loop = asyncio.get_event_loop()

            # List keys from Vault
            list_path = "uno/keys"

            if self._kv_version == 2:
                # KV version 2 listing
                response = await loop.run_in_executor(
                    None,
                    lambda: self._client.secrets.kv.v2.list_secrets(
                        path=list_path,
                        mount_point=self._kv_mount,
                    ),
                )
            else:
                # KV version 1 listing
                response = await loop.run_in_executor(
                    None,
                    lambda: self._client.secrets.kv.v1.list_secrets(
                        path=list_path,
                        mount_point=self._kv_mount,
                    ),
                )

            keys = response.get("data", {}).get("keys", [])

            # Filter by prefix if specified
            if prefix:
                keys = [k for k in keys if k.startswith(prefix)]

            return keys

        except Exception as e:
            raise SecureValueError(
                f"Failed to list keys from Vault: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def rotate_key(self, key_id: str, **options: Any) -> tuple[str, bytes]:
        """Rotate a key in Vault.

        Args:
            key_id: Identifier for the key to rotate
            **options: Provider-specific options (same as generate_key)

        Returns:
            Tuple of (new_key_version, new_key_bytes)

        Raises:
            SecureValueError: If key rotation fails
        """
        if not self._initialized or not self._client:
            raise SecureValueError(
                "Vault provider not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            # Generate a new key with the same ID
            return await self.generate_key(key_id, **options)

        except Exception as e:
            raise SecureValueError(
                f"Failed to rotate key in Vault: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e


# Register the provider with the registry
from uno.config.key_provider import ProviderRegistry

# Register provider when module is imported
ProviderRegistry.register_provider(VaultProvider, "vault")
