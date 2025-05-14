"""Unit tests for the key rotation utilities."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from uno.config.key_rotation import rotate_secure_values, setup_key_rotation
from uno.config.secure import SecureValue


@pytest.fixture
def mock_secure_values() -> list[MagicMock]:
    """Create a list of mock SecureValue instances."""
    values = []
    for i in range(5):
        mock = MagicMock(spec=SecureValue)
        mock.rotate_key = AsyncMock()
        values.append(mock)
    return values


@pytest.fixture
def caplog_fixture(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    """Set up logging capture."""
    caplog.set_level(logging.INFO, logger="uno.config.key_rotation")
    return caplog


@pytest.mark.asyncio
async def test_rotate_secure_values_parallel(
    mock_secure_values: list[MagicMock],
    caplog_fixture: pytest.LogCaptureFixture,
) -> None:
    """Test rotating secure values in parallel mode."""
    # Act
    await rotate_secure_values(
        values=mock_secure_values, new_key_version="v2", parallel=True, batch_size=2
    )

    # Assert
    for value in mock_secure_values:
        value.rotate_key.assert_awaited_once_with("v2")

    # Verify logging (should have 4 logs: start, 2 batches, and finish)
    assert "Rotating 5 secure values to key version v2" in caplog_fixture.text
    assert "Rotated 2/5 values" in caplog_fixture.text
    assert "Rotated 4/5 values" in caplog_fixture.text
    assert (
        "Successfully rotated 5 secure values to key version v2" in caplog_fixture.text
    )


@pytest.mark.asyncio
async def test_rotate_secure_values_sequential(
    mock_secure_values: list[MagicMock],
    caplog_fixture: pytest.LogCaptureFixture,
) -> None:
    """Test rotating secure values in sequential mode."""
    # Act
    await rotate_secure_values(
        values=mock_secure_values, new_key_version="v2", parallel=False
    )

    # Assert
    for value in mock_secure_values:
        value.rotate_key.assert_awaited_once_with("v2")

    # Verify logging (should have 2 logs: start, finish)
    assert "Rotating 5 secure values to key version v2" in caplog_fixture.text
    assert (
        "Successfully rotated 5 secure values to key version v2" in caplog_fixture.text
    )


@pytest.mark.asyncio
async def test_rotate_secure_values_empty(
    caplog_fixture: pytest.LogCaptureFixture,
) -> None:
    """Test rotating an empty list of secure values."""
    # Act
    await rotate_secure_values(values=[], new_key_version="v2")

    # Assert
    assert "No values to rotate" in caplog_fixture.text


@pytest.mark.asyncio
async def test_setup_key_rotation() -> None:
    """Test setting up key rotation with old and new keys."""
    # Arrange
    with patch.object(SecureValue, "setup_encryption", new=AsyncMock()) as mock_setup:
        with patch.object(
            SecureValue, "set_current_key_version", new=AsyncMock()
        ) as mock_set_version:
            # Act
            await setup_key_rotation(
                old_key="old_secret",
                new_key="new_secret",
                old_version="old_ver",
                new_version="new_ver",
            )

            # Assert
            # Verify old key was registered
            mock_setup.assert_any_await(
                master_key="old_secret",
                key_version="old_ver",
            )

            # Verify new key was registered
            mock_setup.assert_any_await(
                master_key="new_secret",
                key_version="new_ver",
            )

            # Verify new key was set as current
            mock_set_version.assert_awaited_once_with("new_ver")


@pytest.mark.asyncio
async def test_setup_key_rotation_with_defaults() -> None:
    """Test setting up key rotation with default version values."""
    # Arrange
    with patch.object(SecureValue, "setup_encryption", new=AsyncMock()) as mock_setup:
        with patch.object(
            SecureValue, "set_current_key_version", new=AsyncMock()
        ) as mock_set_version:
            # Act
            await setup_key_rotation(old_key="old_secret", new_key="new_secret")

            # Assert
            # Verify default versions were used
            mock_setup.assert_any_await(
                master_key="old_secret",
                key_version="v1",
            )

            mock_setup.assert_any_await(
                master_key="new_secret",
                key_version="v2",
            )

            mock_set_version.assert_awaited_once_with("v2")
