"""Tests for secure configuration setup functions."""

import os
import pytest
from unittest.mock import patch, Mock, AsyncMock

from uno.config.secure import setup_secure_config, SecureValue, SecureValueError
from uno.errors.base import ErrorCode, ErrorSeverity, ErrorCategory


import pytest


@pytest.mark.asyncio
async def test_setup_secure_config_calls_setup_encryption():
    """Test that setup_secure_config calls SecureValue.setup_encryption with correct args."""
    with patch.object(
        SecureValue, "setup_encryption", new_callable=AsyncMock
    ) as mock_setup:
        # Call with explicit arguments
        test_key = "test_master_key"
        test_salt_file = "/path/to/salt"
        test_version = "test_version"

        await setup_secure_config(
            master_key=test_key,
            salt_file=test_salt_file,
            key_version=test_version,
        )

        # Verify setup_encryption was called with the right arguments
        mock_setup.assert_called_once_with(
            master_key=test_key,
            salt_file=test_salt_file,
            key_version=test_version,
        )


@pytest.mark.asyncio
async def test_setup_secure_config_default_values():
    """Test that setup_secure_config uses default values correctly."""
    with patch.object(
        SecureValue, "setup_encryption", new_callable=AsyncMock
    ) as mock_setup:
        # Call with defaults
        await setup_secure_config()

        # Verify defaults were passed through
        mock_setup.assert_called_once_with(
            master_key=None,
            salt_file=None,
            key_version="v1",
        )


@pytest.mark.asyncio
async def test_setup_secure_config_error_propagation():
    """Test that setup_secure_config propagates errors from setup_encryption."""
    with patch.object(
        SecureValue, "setup_encryption", new_callable=AsyncMock
    ) as mock_setup:
        # Make setup_encryption raise an error
        # Using the expected code format with CONFIG_SECURE_ prefix
        mock_setup.side_effect = SecureValueError(
            "Test error",
            code=ErrorCode.get_or_create(
                "CONFIG_SECURE_TEST_ERROR", ErrorCategory.get_or_create("TEST")
            ),
        )

        # Verify the error is propagated
        with pytest.raises(SecureValueError) as excinfo:
            await setup_secure_config()

        assert "Test error" in str(excinfo.value)
        # Update to match the actual format with the prefix
        assert excinfo.value.code.code == "CONFIG_SECURE_TEST_ERROR"


@pytest.mark.asyncio
async def test_setup_secure_config_environment_vars():
    """Test that setup_secure_config works with environment variables."""
    with patch.object(
        SecureValue, "setup_encryption", new_callable=AsyncMock
    ) as mock_setup:
        # Set environment variables
        with patch.dict(os.environ, {"UNO_MASTER_KEY": "env_master_key"}):
            await setup_secure_config()

            # The function itself doesn't process environment variables,
            # it just passes through to setup_encryption which does
            mock_setup.assert_called_once_with(
                master_key=None,  # Should be None to trigger env var lookup in setup_encryption
                salt_file=None,
                key_version="v1",
            )
