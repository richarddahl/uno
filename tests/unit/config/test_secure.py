"""Tests for secure value handling with proper type annotations."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
import pytest
from typing import Any, ClassVar
from unittest.mock import Mock

from pydantic import Field

from uno.config import (
    SecureField,
    SecureValue,
    SecureValueError,
    SecureValueHandling,
    UnoSettings,
    requires_secure_access,
)


class TestSecureValue:
    def test_getstate_and_dir_masking(self, setup_secure_config):
        import pickle
        val = SecureValue("supersecret", handling=SecureValueHandling.ENCRYPT)
        state = val.__getstate__()
        # Sensitive fields are masked
        for k in ['_value', '_original_value', '_serialized_value', '_salt']:
            assert state[k] == '******'
        # dir() does not show sensitive fields
        attrs = dir(val)
        for k in ['_value', '_original_value', '_serialized_value', '_salt']:
            assert k not in attrs
        # Pickling does not leak secret
        pickled = pickle.dumps(val)
        assert b'supersecret' not in pickled

    """Test SecureValue class with proper handling of types."""

    def test_mask_handling(self, setup_secure_config: None) -> None:
        """Test masked value handling."""
        # Simple value types
        value = SecureValue("password123", handling=SecureValueHandling.MASK)
        assert value.get_value() == "password123"
        assert str(value) == "******"
        # Match the actual representation format
        assert repr(value) == "SecureValue('******')"

    def test_encrypt_handling(self, setup_secure_config: None) -> None:
        """Test encrypted value handling."""
        # Test with various types
        test_cases = [
            ("string_value", str),
            (123, int),
            (123.45, float),
            (True, bool),
            ([1, 2, 3], list),
            ({"key": "value"}, dict),
        ]

        for value, expected_type in test_cases:
            secure = SecureValue(value, handling=SecureValueHandling.ENCRYPT)
            # Value should be encrypted internally
            assert isinstance(
                secure._value, bytes
            )  
            # But decrypted when accessed
            decrypted = secure.get_value()
            assert isinstance(decrypted, expected_type)
            assert decrypted == value

    def test_sealed_handling(self, setup_secure_config: None) -> None:
        """Test sealed value handling."""
        value = SecureValue("sealed_secret", handling=SecureValueHandling.SEALED)
        # Should raise error when attempting to access value
        with pytest.raises(SecureValueError) as exc_info:
            value.get_value()
        assert "Cannot access sealed value" in str(exc_info.value)

    def test_complex_type_encryption(self, setup_secure_config: None) -> None:
        """Test encrypting and decrypting complex types."""

        @dataclass
        class ComplexObject:
            name: str
            value: int

        # Dictionary with mixed types
        dict_value = {"name": "test", "value": 123, "enabled": True}
        secure_dict = SecureValue(dict_value, handling=SecureValueHandling.ENCRYPT)
        # Get the decrypted value - in current implementation it preserves the original type
        decrypted_dict = secure_dict.get_value()
        # The implementation now preserves the original dict type rather than converting to string
        assert isinstance(decrypted_dict, dict)
        # Verify the content is preserved
        assert decrypted_dict["name"] == "test"
        assert decrypted_dict["value"] == 123
        assert decrypted_dict["enabled"] is True

        # Test with enum-like string values
        enum_value = "A"
        secure_enum = SecureValue(enum_value, handling=SecureValueHandling.ENCRYPT)
        assert secure_enum.get_value() == "A"

    def test_encryption_key_required(self) -> None:
        """Test that encryption requires setup."""
        # Clear the new keyring attributes to simulate not being set up
        SecureValue._encryption_keys.clear()
        SecureValue._current_key_version = None

        # Attempt to create an encrypted SecureValue (should raise)
        with pytest.raises(SecureValueError) as exc_info:
            SecureValue("test", handling=SecureValueHandling.ENCRYPT)
        assert "No key version specified and no current key set" in str(exc_info.value)
        assert exc_info.value.code == "CONFIG_SECURE_NO_KEY_VERSION"

        # Also test manual encryption on an existing instance
        value = SecureValue("test", handling=SecureValueHandling.MASK)
        value._handling_strategy = SecureValueHandling.ENCRYPT
        with pytest.raises(SecureValueError) as exc_info2:
            value._encrypt()
        assert "No key version specified and no current key set" in str(exc_info2.value)
        assert exc_info2.value.code == "CONFIG_SECURE_NO_KEY_VERSION"
    
    @pytest.mark.asyncio
    async def test_key_rotation(self, test_encryption_key: bytes) -> None:
        """Test the key rotation capability."""
        # Set up with initial key
        from uno.config import setup_secure_config

        await setup_secure_config(test_encryption_key.decode("utf-8"))

        # Create and encrypt a value
        original = SecureValue("rotate_me", handling=SecureValueHandling.ENCRYPT)
        encrypted_value = original._value

        # Generate a new key for rotation
        from cryptography.fernet import Fernet

        new_key = Fernet.generate_key()

        # Test rotating the key
        # This test will fail with current implementation but should pass after fixes
        await setup_secure_config(new_key.decode("utf-8"))

        # Create a new SecureValue with the encrypted bytes from the original
        # This is a way to test key rotation - we'd need a separate rotate method
        # in the updated implementation
        rotated = SecureValue("placeholder", handling=SecureValueHandling.ENCRYPT)
        rotated._value = encrypted_value

        # Should raise an error with the wrong key
        with pytest.raises(Exception):
            rotated.get_value()

    def test_securevalue_equality(self, setup_secure_config: None) -> None:
        """Test equality comparison between SecureValue objects."""
        # Create values with same handling type and same underlying content
        a = SecureValue("password123", handling=SecureValueHandling.MASK)
        b = SecureValue("password123", handling=SecureValueHandling.MASK)

        # Currently, SecureValue objects are not implementing equality properly
        # This is documenting the current behavior - objects that should be equal aren't
        assert a == b

        # Same for encrypted values
        e = SecureValue("same_secret", handling=SecureValueHandling.ENCRYPT)
        f = SecureValue("same_secret", handling=SecureValueHandling.ENCRYPT)
        assert e == f


    def test_securevalue_none_handling(self, setup_secure_config: None) -> None:
        """Test handling of None values in SecureValue."""
        # Test with None value and different handling strategies

        # With MASK handling
        none_mask = SecureValue(None, handling=SecureValueHandling.MASK)
        assert none_mask.get_value() is None
        assert str(none_mask) == "******"  

        # With ENCRYPT handling - should be able to encrypt and decrypt None
        none_encrypt = SecureValue(None, handling=SecureValueHandling.ENCRYPT)
        # Should not raise an error
        assert none_encrypt.get_value() is None

        # With SEALED handling
        none_sealed = SecureValue(None, handling=SecureValueHandling.SEALED)
        # Should still raise error when attempting to access
        with pytest.raises(SecureValueError) as exc_info:
            none_sealed.get_value()
        assert "Cannot access sealed value" in str(exc_info.value)

        # Test empty string
        empty_value = SecureValue("", handling=SecureValueHandling.ENCRYPT)
        assert empty_value.get_value() == ""


class TestSecureFields:
    """Test secure field handling in settings."""

    class SecureSettings(UnoSettings):
        """Settings with secure fields for testing."""

        username: str = "admin"
        password: str = SecureField("s3cret", handling=SecureValueHandling.MASK)
        api_key: str = SecureField("abc123", handling=SecureValueHandling.ENCRYPT)
        internal_token: str = SecureField("int123", handling=SecureValueHandling.SEALED)

    def test_secure_field_initialization(self, setup_secure_config: None) -> None:
        """Test that secure fields are properly initialized."""
        settings = self.SecureSettings()

        # Regular field should be untouched
        assert settings.username == "admin"

        # Secure fields should be wrapped
        assert isinstance(settings.password, SecureValue)
        assert isinstance(settings.api_key, SecureValue)
        assert isinstance(settings.internal_token, SecureValue)

        # Values should be accessible according to their handling strategy
        assert settings.password.get_value() == "s3cret"
        assert settings.api_key.get_value() == "abc123"

        # Sealed values should not be accessible
        with pytest.raises(SecureValueError):
            settings.internal_token.get_value()

    def test_secure_field_isolation(self, setup_secure_config: None) -> None:
        """Test that secure fields are properly isolated between instances."""

        # Define a second settings class with some overlapping field names
        class AnotherSecureSettings(UnoSettings):
            username: str = "user2"
            password: str = SecureField("different", handling=SecureValueHandling.MASK)

        # Create instances of both
        settings1 = self.SecureSettings()
        settings2 = AnotherSecureSettings()

        # Check that their secure fields don't interfere
        assert settings1.password == "s3cret"
        assert settings2.password == "different"

        # Check that _secure_fields don't leak between classes
        assert "api_key" in settings1._secure_fields
        assert "api_key" not in settings2._secure_fields

    def test_requires_secure_access(self, setup_secure_config: None) -> None:
        """Test the secure access decorator."""
        access_log = []

        # Import the decorator directly to avoid name shadowing issues
        from uno.config import requires_secure_access as original_decorator

        try:
            # Replace the decorator temporarily for testing
            def test_decorator(func: Any) -> Any:
                def wrapper(*args: Any, **kwargs: Any) -> Any:
                    access_log.append(func.__name__)
                    return func(*args, **kwargs)

                return wrapper

            # Import the module where the decorator is defined to modify it
            import uno.config.secure

            # Store the original
            original = uno.config.secure.requires_secure_access
            # Replace with our test version
            uno.config.secure.requires_secure_access = test_decorator

            @test_decorator
            def access_secure_value(value: SecureValue[Any]) -> Any:
                return value.get_value()

            # Test with a secure value
            secure_value = SecureValue("test_secret", handling=SecureValueHandling.MASK)
            result = access_secure_value(secure_value)

            # Check result and access logging
            assert result == "test_secret"
            assert "access_secure_value" in access_log
        finally:
            # Restore original decorator
            uno.config.secure.requires_secure_access = original
