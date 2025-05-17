"""Tests for SecureValue class and secure field handling."""

from __future__ import annotations

import json
import os
import pickle
from dataclasses import dataclass
from enum import Enum
from typing import Any

import pytest
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field

from uno.config import (
    SecureField,
    SecureValue,
    SecureValueHandling,
    Config,
    setup_secure_config,
)
from uno.config.errors import SecureValueError
from uno.config.secure import DEFAULT_KDF_PARAMS


class MockComplexModel(BaseModel):
    name: str
    value: int


class TestSecureValueBasics:
    """Test basic SecureValue functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, setup_secure_config: None) -> None:
        """Test initializing SecureValue with different types and handling."""
        # Test with different types
        test_cases = [
            ("string_value", str),
            (123, int),
            (123.45, float),
            (True, bool),
            (None, type(None)),
            ([1, 2, 3], list),
            ({"key": "value"}, dict),
        ]

        for value, expected_type in test_cases:
            # Test MASK handling
            masked = SecureValue(value, handling=SecureValueHandling.MASK)
            result = await masked.get_value()
            assert isinstance(result, expected_type)
            assert result == value
            assert str(masked) == "******"

            # Test ENCRYPT handling
            encrypted = SecureValue(value, handling=SecureValueHandling.ENCRYPT)
            result = await encrypted.get_value()
            assert isinstance(result, expected_type)
            assert result == value
            assert str(encrypted) == "******"

            # Test SEALED handling (can't access value)
            sealed = SecureValue(value, handling=SecureValueHandling.SEALED)
            assert str(sealed) == "******"
            with pytest.raises(SecureValueError):
                await sealed.get_value()

    def test_unsupported_types(self, setup_secure_config: None) -> None:
        """Test handling of unsupported types."""
        # Should raise TypeError for unsupported types
        with pytest.raises(TypeError):
            SecureValue(object())

    @pytest.mark.asyncio
    async def test_equality(self, setup_secure_config: None) -> None:
        """Test secure value equality comparison."""
        # Basic equality between SecureValue objects
        a = SecureValue("test", handling=SecureValueHandling.MASK)
        b = SecureValue("test", handling=SecureValueHandling.MASK)
        assert a == b

        # Different values should not be equal
        c = SecureValue("different", handling=SecureValueHandling.MASK)
        assert a != c

        # Same value but different handling
        d = SecureValue("test", handling=SecureValueHandling.ENCRYPT)
        # For regular equality, handling matters
        assert a != d

        # SecureValue to raw value comparison
        assert a == "test"
        assert a != "different"

        # Async equality should work for constant-time comparison
        assert await a.async_equals("test")
        assert not await a.async_equals("different")
        assert await a.async_equals(b)
        assert not await a.async_equals(c)

    @pytest.mark.asyncio
    async def test_complex_objects(self, setup_secure_config: None) -> None:
        """Test SecureValue with complex objects."""

        # Test with enum
        class TestEnum(Enum):
            A = "a"
            B = "b"

        enum_value = SecureValue(TestEnum.A, handling=SecureValueHandling.ENCRYPT)
        assert await enum_value.get_value() == TestEnum.A

        model = MockComplexModel(name="test", value=123)
        model_value = SecureValue(model, handling=SecureValueHandling.ENCRYPT)

        # Get the decrypted value
        result = await model_value.get_value()

        # Compare data rather than exact type since we might get a dynamic model back
        assert result.name == "test"
        assert result.value == 123

        # If exact type checking is needed, check specific attributes instead
        assert hasattr(result, "name")
        assert hasattr(result, "value")
        assert result.model_dump() == model.model_dump()


class TestSecureValueMemory:
    """Test memory handling and security features in SecureValue."""

    @pytest.mark.asyncio
    async def test_memory_clearing(self, setup_secure_config: None) -> None:
        """Test that memory is properly cleared."""
        # Create value and check internal state
        val = SecureValue("sensitive", handling=SecureValueHandling.MASK)
        orig_value = val._value
        orig_salt = val._salt

        # Verify we can access the value before clearing
        assert await val.get_value() == "sensitive"

        # Clear and check clearing
        val.clear()
        assert val._value == "\x00" * len(orig_value)
        assert val._original_value is None
        assert val._salt == b"\x00" * len(orig_salt)

    @pytest.mark.asyncio
    async def test_context_manager(self, setup_secure_config: None) -> None:
        """Test using SecureValue as a context manager."""
        # Use with context manager
        with SecureValue("context_test", handling=SecureValueHandling.MASK) as val:
            assert await val.get_value() == "context_test"

        # After exiting context, value should be cleared
        assert val._value == "\x00" * len("context_test")
        assert val._original_value is None

    def test_serialization_protection(self, setup_secure_config: None) -> None:
        """Test protection against serialization and introspection."""
        val = SecureValue("secret_data", handling=SecureValueHandling.ENCRYPT)

        # Test getstate masking for pickle
        state = val.__getstate__()
        for k in ["_value", "_original_value", "_serialized_value", "_salt"]:
            assert state[k] == "******"

        # Test pickle doesn't expose the secret
        pickled = pickle.dumps(val)
        assert b"secret_data" not in pickled

        # Test dir() hiding sensitive attributes
        attrs = dir(val)
        for k in ["_value", "_original_value", "_serialized_value", "_salt"]:
            assert k not in attrs


class TestSecureValueEncryption:
    """Test encryption features of SecureValue."""

    @pytest.mark.asyncio
    async def test_encryption_setup(self, test_encryption_key: bytes) -> None:
        """Test setting up encryption."""
        # Clear any existing keys
        SecureValue._encryption_keys.clear()
        SecureValue._current_key_version = None

        # Setup with a test key
        await setup_secure_config(test_encryption_key.decode("utf-8"))

        # Check key is stored
        assert SecureValue._encryption_keys
        assert SecureValue._current_key_version is not None

        # Should now be able to create encrypted values
        val = SecureValue("encrypted", handling=SecureValueHandling.ENCRYPT)
        assert await val.get_value() == "encrypted"

    @pytest.mark.asyncio
    async def test_kdf_params(self, setup_secure_config: None) -> None:
        """Test custom KDF parameters."""
        # Use custom KDF params
        custom_kdf = {"algorithm": "sha256", "iterations": 100_000, "length": 32}

        val = SecureValue(
            "kdf_test", handling=SecureValueHandling.ENCRYPT, kdf_params=custom_kdf
        )

        # Should use the custom KDF params
        assert val._kdf_params == custom_kdf
        # Should still decrypt correctly
        assert await val.get_value() == "kdf_test"

    @pytest.mark.asyncio
    async def test_rotate_kdf(self, setup_secure_config: None) -> None:
        """Test rotating KDF parameters."""
        val = SecureValue("rotate_test", handling=SecureValueHandling.ENCRYPT)
        old_params = val._kdf_params.copy()

        # Rotate to new params
        new_params = {"algorithm": "sha256", "iterations": 300_000, "length": 32}
        val.rotate_kdf(new_params)

        # Should use new params but still decrypt correctly
        assert val._kdf_params == new_params
        assert val._kdf_params != old_params
        assert await val.get_value() == "rotate_test"

    @pytest.mark.asyncio
    async def test_key_rotation(self, test_encryption_key: bytes) -> None:
        """Test key rotation."""
        # Setup with initial key
        await setup_secure_config(test_encryption_key.decode("utf-8"), key_version="v1")

        # Create and encrypt a value
        val = SecureValue("rotate_key", handling=SecureValueHandling.ENCRYPT)
        assert await val.get_value() == "rotate_key"

        # Generate a new key for rotation
        new_key = Fernet.generate_key()

        # Register the new key
        await setup_secure_config(new_key.decode("utf-8"), key_version="v2")

        # Rotate the value to the new key
        await val.rotate_key("v2")

        # Should still decrypt correctly
        assert await val.get_value() == "rotate_key"
        # And should be using the new key version
        assert val._key_version == "v2"


class TestSecureField:
    """Test SecureField integration with Config."""

    @pytest.mark.asyncio
    async def test_secure_field_in_config(self, setup_secure_config: None) -> None:
        """Test using SecureField in Config classes."""

        class TestSecureConfig(Config):
            username: str = "admin"
            password: Any = SecureField("secret", handling=SecureValueHandling.MASK)
            api_key: Any = SecureField("key123", handling=SecureValueHandling.ENCRYPT)

        config = TestSecureConfig()

        # Fields should be SecureValue instances
        assert isinstance(config.password, SecureValue)
        assert isinstance(config.api_key, SecureValue)

        # Regular fields should be unchanged
        assert config.username == "admin"

        # Secure fields should work
        assert await config.password.get_value() == "secret"
        assert await config.api_key.get_value() == "key123"

        # Track secure fields in the class
        assert "password" in config._secure_fields
        assert "api_key" in config._secure_fields
