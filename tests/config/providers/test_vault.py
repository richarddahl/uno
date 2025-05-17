# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""Tests for the HashiCorp Vault provider."""

import asyncio
import json
import os
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from uno.config.providers.vault import VaultProvider
from uno.config.errors import SecureValueError


@pytest.fixture
def mock_hvac_client() -> Generator[MagicMock, None, None]:
    """Create a mock hvac client for testing."""
    with patch("hvac.Client") as mock_client:
        # Set is_authenticated to return True
        mock_client.return_value.is_authenticated.return_value = True

        # Mock health status
        mock_client.return_value.sys.read_health_status.return_value = {
            "initialized": True,
            "sealed": False,
            "standby": False,
            "performance_standby": False,
            "replication_performance_mode": "disabled",
            "replication_dr_mode": "disabled",
            "server_time_utc": 1632146589,
            "version": "1.8.2",
        }

        # Mock KV store methods
        kv_v2 = mock_client.return_value.secrets.kv.v2
        kv_v2.create_or_update_secret = MagicMock()
        kv_v2.read_secret_version.return_value = {
            "data": {
                "data": {
                    "key": "dGVzdC1rZXktZGF0YQ==",  # "test-key-data" in base64
                    "version": "vault-1632146589-123456",
                    "metadata": {},
                },
                "metadata": {
                    "created_time": "2021-09-20T10:15:00Z",
                    "deletion_time": "",
                    "destroyed": False,
                    "version": 1,
                },
            }
        }
        kv_v2.list_secrets.return_value = {
            "data": {
                "keys": ["vault-1632146589-123456", "vault-1632146590-789012"],
            }
        }

        # Mock KV v1 methods
        kv_v1 = mock_client.return_value.secrets.kv.v1
        kv_v1.create_or_update_secret = MagicMock()
        kv_v1.read_secret.return_value = {
            "data": {
                "key": "dGVzdC1rZXktZGF0YQ==",  # "test-key-data" in base64
                "version": "vault-1632146589-123456",
                "metadata": {},
            }
        }
        kv_v1.list_secrets.return_value = {
            "data": {
                "keys": ["vault-1632146589-123456", "vault-1632146590-789012"],
            }
        }

        yield mock_client.return_value


class TestVaultProvider:
    """Tests for the VaultProvider class."""

    @pytest.mark.asyncio
    async def test_initialize(self, mock_hvac_client: MagicMock) -> None:
        """Test provider initialization."""
        provider = VaultProvider()

        # Initialize with token auth
        await provider.initialize(
            {
                "url": "https://vault.example.com:8200",
                "token": "test-token",
                "transit_mount": "transit",
                "kv_mount": "secret",
                "kv_version": 2,
            }
        )

        assert provider._url == "https://vault.example.com:8200"
        assert provider._token == "test-token"
        assert provider._transit_mount == "transit"
        assert provider._kv_mount == "secret"
        assert provider._kv_version == 2
        assert provider._initialized is True
        assert provider._client is not None

    @pytest.mark.asyncio
    async def test_initialize_with_environment_vars(
        self, mock_hvac_client: MagicMock
    ) -> None:
        """Test initialization using environment variables."""
        # Set environment variables
        os.environ["VAULT_ADDR"] = "https://vault.env.example.com:8200"
        os.environ["VAULT_TOKEN"] = "env-token"

        provider = VaultProvider()

        # Initialize without explicit config
        await provider.initialize({})

        assert provider._url == "https://vault.env.example.com:8200"
        assert provider._token == "env-token"
        assert provider._transit_mount == "transit"  # Default
        assert provider._kv_mount == "secret"  # Default
        assert provider._kv_version == 2  # Default
        assert provider._initialized is True

        # Clean up
        del os.environ["VAULT_ADDR"]
        del os.environ["VAULT_TOKEN"]

    @pytest.mark.asyncio
    async def test_initialize_missing_url(self) -> None:
        """Test initialization with missing URL."""
        provider = VaultProvider()

        # Ensure no environment variable
        if "VAULT_ADDR" in os.environ:
            del os.environ["VAULT_ADDR"]

        # Initialize without URL should fail
        with pytest.raises(SecureValueError) as excinfo:
            await provider.initialize(
                {
                    "token": "test-token",
                }
            )

        assert "Vault URL is required" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_is_available(self, mock_hvac_client: MagicMock) -> None:
        """Test availability check."""
        provider = VaultProvider()

        # Not initialized
        assert await provider.is_available() is False

        # Initialize
        await provider.initialize(
            {
                "url": "https://vault.example.com:8200",
                "token": "test-token",
            }
        )

        # Should be available
        assert await provider.is_available() is True

        # Test when Vault is sealed
        mock_hvac_client.sys.read_health_status.return_value["sealed"] = True
        assert await provider.is_available() is False

        # Test when authentication fails
        mock_hvac_client.sys.read_health_status.return_value["sealed"] = False
        mock_hvac_client.is_authenticated.return_value = False
        assert await provider.is_available() is False

    @pytest.mark.asyncio
    async def test_generate_key(self, mock_hvac_client: MagicMock) -> None:
        """Test key generation."""
        provider = VaultProvider()

        # Initialize
        await provider.initialize(
            {
                "url": "https://vault.example.com:8200",
                "token": "test-token",
            }
        )

        # Generate a key
        version, key_bytes = await provider.generate_key("test-key")

        # Check version format
        assert version.startswith("vault-")
        assert len(version.split("-")) == 3

        # Check key bytes
        assert isinstance(key_bytes, bytes)
        assert len(key_bytes) == 32  # AES-256 key

        # Check if key was stored
        if provider._kv_version == 2:
            mock_hvac_client.secrets.kv.v2.create_or_update_secret.assert_called_once()
        else:
            mock_hvac_client.secrets.kv.v1.create_or_update_secret.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_key(self, mock_hvac_client: MagicMock) -> None:
        """Test key retrieval."""
        provider = VaultProvider()

        # Initialize
        await provider.initialize(
            {
                "url": "https://vault.example.com:8200",
                "token": "test-token",
            }
        )

        # Get a key by specific version
        key_bytes = await provider.get_key(
            "test-key", version="vault-1632146589-123456"
        )

        # Check key bytes
        assert key_bytes == b"test-key-data"

        # Check if key was retrieved
        if provider._kv_version == 2:
            mock_hvac_client.secrets.kv.v2.read_secret_version.assert_called_once()
        else:
            mock_hvac_client.secrets.kv.v1.read_secret.assert_called_once()

        # Get latest version
        key_bytes = await provider.get_key("test-key")

        # Check key bytes
        assert key_bytes == b"test-key-data"

        # Check if keys were listed
        if provider._kv_version == 2:
            mock_hvac_client.secrets.kv.v2.list_secrets.assert_called_once()
        else:
            mock_hvac_client.secrets.kv.v1.list_secrets.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_key(self, mock_hvac_client: MagicMock) -> None:
        """Test key deletion."""
        provider = VaultProvider()

        # Initialize
        await provider.initialize(
            {
                "url": "https://vault.example.com:8200",
                "token": "test-token",
            }
        )

        # Delete a specific version
        await provider.delete_key("test-key", version="vault-1632146589-123456")

        # Check if version was deleted
        if provider._kv_version == 2:
            mock_hvac_client.secrets.kv.v2.delete_secret_versions.assert_called_once()
        else:
            mock_hvac_client.secrets.kv.v1.delete_secret.assert_called_once()

        # Reset mocks
        mock_hvac_client.reset_mock()

        # Delete all versions
        await provider.delete_key("test-key")

        # Check if all versions were deleted
        if provider._kv_version == 2:
            mock_hvac_client.secrets.kv.v2.delete_metadata_and_all_versions.assert_called_once()
        else:
            # For v1, it should list and delete each version
            mock_hvac_client.secrets.kv.v1.list_secrets.assert_called_once()
            assert mock_hvac_client.secrets.kv.v1.delete_secret.call_count == 2

    @pytest.mark.asyncio
    async def test_list_keys(self, mock_hvac_client: MagicMock) -> None:
        """Test key listing."""
        provider = VaultProvider()

        # Initialize
        await provider.initialize(
            {
                "url": "https://vault.example.com:8200",
                "token": "test-token",
            }
        )

        # List keys
        keys = await provider.list_keys()

        # Check keys
        assert len(keys) == 2
        assert "vault-1632146589-123456" in keys
        assert "vault-1632146590-789012" in keys

        # Check if keys were listed
        if provider._kv_version == 2:
            mock_hvac_client.secrets.kv.v2.list_secrets.assert_called_once()
        else:
            mock_hvac_client.secrets.kv.v1.list_secrets.assert_called_once()

    @pytest.mark.asyncio
    async def test_rotate_key(self, mock_hvac_client: MagicMock) -> None:
        """Test key rotation."""
        provider = VaultProvider()

        # Initialize
        await provider.initialize(
            {
                "url": "https://vault.example.com:8200",
                "token": "test-token",
            }
        )

        # Mock the generate_key method
        original_generate_key = provider.generate_key
        provider.generate_key = AsyncMock(
            return_value=("vault-rotated-123456", b"rotated-key-data")
        )

        # Rotate a key
        version, key_bytes = await provider.rotate_key("test-key")

        # Check results
        assert version == "vault-rotated-123456"
        assert key_bytes == b"rotated-key-data"

        # Check if generate_key was called
        provider.generate_key.assert_called_once_with("test-key")

        # Restore original method
        provider.generate_key = original_generate_key
