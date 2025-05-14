"""
Secure value handling for the Uno configuration system.

This module provides tools for handling sensitive configuration values
with support for masking, encryption, and secure access.
"""

from __future__ import annotations

import base64
import json
import os
import logging
import hmac  # For constant-time comparison
from enum import Enum
from functools import wraps
from typing import (
    Any,
    ClassVar,
    Callable,
    Generic,
    ParamSpec,
    TypeVar,
    cast,
)

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from pydantic import Field

from uno.config.errors import SecureValueError


P = ParamSpec("P")
R = TypeVar("R")


def requires_secure_access(func: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator to log access to secure configuration values.
    Logs all access to secure values and warns on SEALED handling.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if args and isinstance(args[0], SecureValue):
            secure_value = args[0]
            SecureValue._logger.info(
                f"Accessing secure value with handling {secure_value._handling_strategy}"
            )
            if secure_value._handling_strategy == SecureValueHandling.SEALED:
                SecureValue._logger.warning("Accessing SEALED value")
        return func(*args, **kwargs)

    return wrapper


class SecureValueHandling(str, Enum):
    """Handling strategy for secure values."""

    # Plaintext in memory, masked in logs/output
    MASK = "mask"

    # Encrypt in storage, decrypt in memory
    ENCRYPT = "encrypt"

    # Always encrypted, even in memory
    SEALED = "sealed"


T = TypeVar("T")


class SecureValue(Generic[T]):
    """
    Container for secure values with controlled access.

    This class ensures sensitive configuration values are handled securely. It preserves the original type
    and provides masking/encryption as specified by the handling strategy. Use `get_value()` to retrieve
    the original value with type fidelity. String representation always returns a masked value ("******")
    for masked fields, regardless of the underlying type.
    """

    _value: str | bytes
    _handling: ClassVar[dict[str, SecureValueHandling]] = {}
    _encryption_keys: ClassVar[dict[str, bytes]] = {}  # Key ring: version -> key
    _current_key_version: ClassVar[str | None] = (
        None  # Current key version for encryption
    )
    _MASTER_SALT: ClassVar[bytes] = b"uno_framework_salt"
    _logger: ClassVar[logging.Logger] = logging.getLogger("uno.config.secure")

    @classmethod
    def _encryption_key(cls) -> bytes | None:
        """Backward compatibility method to access the current encryption key."""
        if not cls._current_key_version or not cls._encryption_keys:
            return None
        return cls._encryption_keys.get(cls._current_key_version)

    def __init__(
        self,
        value: T,
        handling: SecureValueHandling = SecureValueHandling.MASK,
        salt: bytes | None = None,
        key_version: str | None = None,  # Optional key version for encryption
    ):
        """
        Initialize a secure value.

        Args:
            value: The sensitive value to secure. Must be a primitive (str, int, float, bool, None),
                collection (dict, list, tuple, set), or Enum. Other types will raise TypeError.
            handling: How to handle the value (mask, encrypt, seal).
            salt: Optional salt for encryption (random if None).
            key_version: Optional specific key version to use (current key if None).
        Raises:
            TypeError: If value is not a supported type.
            SecureValueError: If specified key version doesn't exist.
        """
        # Type enforcement: only allow primitives, collections, or Enum
        allowed = (str, int, float, bool, type(None), dict, list, tuple, set)
        if not (isinstance(value, allowed) or isinstance(value, Enum)):
            raise TypeError(
                f"SecureValue only supports primitive types, collections, or Enum. Got: {type(value)}"
            )
        self._original_type = type(value)
        self._handling_strategy = handling
        self._salt = salt or os.urandom(16)
        self._is_enum = isinstance(value, Enum)
        self._original_value = value
        self._key_version = key_version or self._current_key_version

        if isinstance(value, (dict, list, tuple, set)):
            self._value = json.dumps(value)
            self._complex_type = True
        else:
            self._value = str(value)
            self._complex_type = False

        if handling in (SecureValueHandling.ENCRYPT, SecureValueHandling.SEALED):
            self._encrypt()

    @classmethod
    async def setup_encryption(
        cls,
        master_key: str | bytes | None = None,
        salt_file: str | None = None,
        key_version: str = "v1",  # Default version for the key
    ) -> None:
        """Set up the encryption system with a master key.

        Args:
            master_key: Master encryption key (will use UNO_MASTER_KEY env var if None)
            salt_file: Optional path to a file containing the salt
            key_version: Version identifier for this key

        Raises:
            SecureValueError: If no master key is provided or found in environment
        """
        if master_key is None:
            # Try to get from environment
            env_key = os.environ.get("UNO_MASTER_KEY")
            if not env_key:
                raise SecureValueError(
                    "No master encryption key provided and UNO_MASTER_KEY not set",
                    code="NO_MASTER_KEY",
                )
            master_key = env_key

        # Convert to bytes if needed
        if isinstance(master_key, str):
            master_key = master_key.encode("utf-8")

        # Determine salt
        if salt_file:
            try:
                import aiofiles
                async with aiofiles.open(salt_file, "rb") as f:
                    salt = await f.read()
            except Exception as e:
                raise SecureValueError(
                    f"Could not read salt file: {e}",
                    code="SALT_FILE_ERROR",
                )
        else:
            master_salt = os.environ.get("UNO_MASTER_SALT", "")
            if master_salt:
                salt = master_salt.encode("utf-8")
            else:
                salt = cls._MASTER_SALT

        # We don't store the raw master key, just derive a key from it
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )

        derived_key = base64.urlsafe_b64encode(kdf.derive(master_key))

        # Store the key in our key ring
        cls._encryption_keys[key_version] = derived_key

        # Set as current key if it's the first one or explicitly specified
        if cls._current_key_version is None:
            cls._current_key_version = key_version
            cls._logger.info(f"Set initial encryption key version: {key_version}")
        else:
            cls._logger.info(f"Added encryption key version: {key_version}")

    @classmethod
    @classmethod
    def set_current_key_version(cls, key_version: str) -> None:
        """Set the current key version to use for new encryptions.

        Args:
            key_version: The key version to use for new encryptions

        Raises:
            SecureValueError: If the specified key version doesn't exist
        """
        if key_version not in cls._encryption_keys:
            raise SecureValueError(
                f"Key version {key_version} not found in key ring",
                code="UNKNOWN_KEY_VERSION",
            )

        cls._current_key_version = key_version
        cls._logger.info(f"Set current encryption key version to: {key_version}")

    def _get_fernet(self, key_version: str | None = None) -> tuple[Fernet, str]:
        """Get a Fernet cipher for encryption/decryption.

        Args:
            key_version: Specific key version to use (defaults to this value's key version)

        Returns:
            Tuple of (Fernet cipher, key version used)

        Raises:
            SecureValueError: If encryption is not set up or key version is invalid
        """
        # Use instance key version if none specified
        version_to_use = key_version or self._key_version

        if not version_to_use:
            raise SecureValueError(
                "No key version specified and no current key set",
                code="NO_KEY_VERSION",
            )

        if not self._encryption_keys:
            raise SecureValueError(
                "Encryption not set up, call SecureValue.setup_encryption() first",
                code="ENCRYPTION_NOT_SETUP",
            )

        # Get the key for this version
        if version_to_use not in self._encryption_keys:
            raise SecureValueError(
                f"Key version {version_to_use} not found in key ring",
                code="UNKNOWN_KEY_VERSION",
            )

        key = self._encryption_keys[version_to_use]
        if not key:
            raise SecureValueError(
                "Encryption key is None or empty",
                code="INVALID_ENCRYPTION_KEY",
            )

        # For each value, we derive a unique key using the master key and this value's salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=10000,
        )

        derived_key = base64.urlsafe_b64encode(kdf.derive(key))
        return Fernet(derived_key), version_to_use

    def _encrypt(self, key_version: str | None = None) -> None:
        """Encrypt the value if needed.

        Args:
            key_version: Optional specific key version to use for encryption
                         (defaults to the instance's key version)
        """
        if self._handling_strategy not in (
            SecureValueHandling.ENCRYPT,
            SecureValueHandling.SEALED,
        ):
            return

        # Get the cipher and actual key version used
        fernet, used_version = self._get_fernet(key_version)

        # Store the key version that was used
        self._key_version = used_version

        # Ensure we always encrypt a str, never bytes
        value_str = (
            self._value.decode("utf-8")
            if isinstance(self._value, bytes)
            else self._value
        )

        # Format as JSON with metadata
        metadata = {"version": used_version, "value": value_str}

        # Encrypt the full metadata package
        self._value = fernet.encrypt(json.dumps(metadata).encode("utf-8"))

    def _decrypt(self) -> str:
        """Decrypt the value.

        Returns:
            Decrypted value as string

        Raises:
            SecureValueError: If value is sealed or encryption isn't set up
        """
        if self._handling_strategy == SecureValueHandling.SEALED:
            raise SecureValueError(
                "Cannot access sealed value directly",
                code="SEALED_VALUE_ACCESS",
            )

        if self._handling_strategy != SecureValueHandling.ENCRYPT:
            # Always return str, decode if bytes
            return (
                self._value.decode("utf-8")
                if isinstance(self._value, bytes)
                else str(self._value)
            )

        # Try to extract metadata format first
        try:
            # Get the cipher based on stored key version
            fernet, _ = self._get_fernet()

            # Decrypt the value
            decrypted_bytes = fernet.decrypt(self._value)

            # Parse the metadata
            metadata = json.loads(decrypted_bytes.decode("utf-8"))

            # Extract the actual value
            if isinstance(metadata, dict) and "value" in metadata:
                return str(metadata["value"])

            # Legacy format without metadata, just return as is
            return decrypted_bytes.decode("utf-8")

        except (json.JSONDecodeError, KeyError):
            # Legacy format without metadata - try with current key
            try:
                fernet, _ = self._get_fernet()
                return fernet.decrypt(self._value).decode("utf-8")
            except Exception as e:
                raise SecureValueError(
                    f"Failed to decrypt value: {e}",
                    code="DECRYPTION_ERROR",
                ) from e

    def rotate_key(self, new_key_version: str | None = None) -> None:
        """Re-encrypt this value with a new key version."""
        if self._handling_strategy not in (
            SecureValueHandling.ENCRYPT,
            SecureValueHandling.SEALED,
        ):
            return

        version_to_use = new_key_version or self._current_key_version
        if not version_to_use:
            raise SecureValueError(
                "No key version specified and no current key set",
                code="NO_KEY_VERSION",
            )
        if version_to_use == self._key_version:
            return
        decrypted = self._decrypt()
        self._value = decrypted
        self._encrypt(key_version=version_to_use)
        self._logger.info(
            f"Rotated secure value from key {self._key_version} to {version_to_use}"
        )

    def _convert_to_original_type(self, value_str: str) -> T:
        """Convert a string value back to its original type.

        Args:
            value_str: String value to convert

        Returns:
            Value converted to its original type

        Raises:
            ValueError: If conversion fails
            TypeError: If type is not supported
        """
        # Handle None type
        if self._original_type is type(None):
            if value_str == "None":
                return cast(T, None)
            # Defensive: if not "None", still return None for type(None)
            return cast(T, None)
        # Handle complex types (dict, list, etc)
        if self._complex_type:
            parsed = json.loads(value_str)

            if self._original_type == set and isinstance(parsed, list):
                return cast(T, set(parsed))
            if self._original_type == tuple and isinstance(parsed, list):
                return cast(T, tuple(parsed))
            return cast(T, parsed)

        # Handle enums
        if self._is_enum and issubclass(self._original_type, Enum):
            for member in self._original_type:
                if str(member.value) == value_str:
                    return cast(T, member)
            # If we can't find a matching enum value, just return the string
            return cast(T, value_str)

        # Handle primitive types
        if self._original_type is bool:
            return cast(T, value_str.lower() in ("true", "1", "yes"))
        if self._original_type is int:
            return cast(T, int(value_str))
        if self._original_type is float:
            return cast(T, float(value_str))

        # For strings and other types that can be represented as strings
        return cast(T, value_str)

    @requires_secure_access
    def get_value(self) -> T:
        """Get the actual value, properly typed.

        Returns:
            The original value with its original type
        """
        # If encrypted, decrypt first
        if self._handling_strategy in (
            SecureValueHandling.ENCRYPT,
            SecureValueHandling.SEALED,
        ):
            try:
                decrypted_value = self._decrypt()
            except SecureValueError:
                # If value is sealed, we can't access it
                raise

            return self._convert_to_original_type(decrypted_value)

        # For unencrypted values, convert directly
        value_str = (
            self._value.decode("utf-8")
            if isinstance(self._value, bytes)
            else self._value
        )
        return self._convert_to_original_type(value_str)

    @requires_secure_access
    def get_raw_decrypted_value(self) -> str:
        """Get the raw decrypted value as a string, before type conversion.

        This is useful for testing and for cases where you need the raw string value.

        Returns:
            Raw decrypted value as a string

        Raises:
            SecureValueError: If value is sealed or encryption isn't set up
        """
        if self._handling_strategy in (
            SecureValueHandling.ENCRYPT,
            SecureValueHandling.SEALED,
        ):
            return self._decrypt()

        # Ensure return type is str
        if isinstance(self._value, bytes):
            return self._value.decode("utf-8")
        return self._value

    def __str__(self) -> str:
        """Return a masked version of the value.

        Returns:
            Masked value
        """
        return "******"

    def __repr__(self) -> str:
        """Return a masked representation.

        Returns:
            Masked representation
        """
        # Always mask in repr, regardless of handling strategy, to match test expectations
        return "SecureValue('******')"

    def __eq__(self, other: object) -> bool:
        """Support equality comparison with raw values and other SecureValue instances.

        Uses constant-time comparison to prevent timing attacks.
        """
        # First check handling strategy if comparing with another SecureValue
        if isinstance(other, SecureValue):
            if self._handling_strategy != other._handling_strategy:
                return False

            # Get both values as strings for constant-time comparison
            self_value = str(self.get_value())
            other_value = str(other.get_value())
            return hmac.compare_digest(self_value, other_value)

        # Compare with raw value using constant-time comparison
        try:
            self_value = str(self.get_value())
            other_value = str(other)
            return hmac.compare_digest(self_value, other_value)
        except (TypeError, ValueError):
            # If conversion to string fails, they can't be equal
            return False


def SecureField(
    default: Any = ...,
    *,
    handling: SecureValueHandling = SecureValueHandling.MASK,
    **kwargs: Any,
) -> Any:
    """Create a field for a secure value.

    Args:
        default: Default value
        handling: How to handle the secure value
        **kwargs: Additional field parameters

    Returns:
        Field with secure value handling
    """
    field_info = Field(
        default, json_schema_extra=kwargs.pop("json_schema_extra", {}), **kwargs
    )
    field_info.json_schema_extra = field_info.json_schema_extra or {}
    field_info.json_schema_extra["secure"] = True
    field_info.json_schema_extra["handling"] = handling.value
    return field_info


@classmethod
def setup_encryption(cls, master_key: str | bytes | None = None, salt_file: str | None = None, key_version: str = "v1") -> None:
    """Set up secure configuration for the Uno framework.

    Args:
        master_key: Master encryption key (will use UNO_MASTER_KEY env var if None)
        salt_file: Optional path to a file containing the salt
        key_version: Version identifier for this key
    """
    # implementation of setup_encryption


async def setup_secure_config(
    master_key: str | bytes | None = None,
    salt_file: str | None = None,
    key_version: str = "v1",
) -> None:
    """Set up secure configuration for the Uno framework.

    This is a convenience wrapper around SecureValue.setup_encryption.

    Args:
        master_key: Master encryption key (will use UNO_MASTER_KEY env var if None)
        salt_file: Optional path to a file containing the salt
        key_version: Version identifier for this key

    Raises:
        SecureValueError: If no master key is provided or found in environment
    """
    await SecureValue.setup_encryption(
        master_key=master_key,
        salt_file=salt_file,
        key_version=key_version,
    )
