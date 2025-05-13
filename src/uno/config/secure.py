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
    Optional,
    Union,
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
    the original value with type fidelity. String representation always returns a masked value ("********")
    for masked fields, regardless of the underlying type.
    """

    _value: str | bytes
    _handling: ClassVar[dict[str, SecureValueHandling]] = {}
    _encryption_key: ClassVar[bytes | None] = None
    _MASTER_SALT: ClassVar[bytes] = b"uno_framework_salt"
    _logger: ClassVar[logging.Logger] = logging.getLogger("uno.config.secure")

    def __init__(
        self,
        value: T,
        handling: SecureValueHandling = SecureValueHandling.MASK,
        salt: bytes | None = None,
    ):
        """
        Initialize a secure value.

        Args:
            value: The sensitive value to secure. Must be a primitive (str, int, float, bool, None),
                collection (dict, list, tuple, set), or Enum. Other types will raise TypeError.
            handling: How to handle the value (mask, encrypt, seal).
            salt: Optional salt for encryption (random if None).
        Raises:
            TypeError: If value is not a supported type.
        """
        # Type enforcement: only allow primitives, collections, or Enum
        allowed = (str, int, float, bool, type(None), dict, list, tuple, set)
        if not (
            isinstance(value, allowed) or isinstance(value, Enum)
        ):
            raise TypeError(
                f"SecureValue only supports primitive types, collections, or Enum. Got: {type(value)}"
            )
        self._original_type = type(value)
        self._handling_strategy = handling
        self._salt = salt or os.urandom(16)
        self._is_enum = isinstance(value, Enum)
        self._original_value = value

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
        cls, master_key: Optional[Union[str, bytes]] = None
    ) -> None:
        """Set up the encryption system with a master key.

        Args:
            master_key: Master encryption key (will use UNO_MASTER_KEY env var if None)

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

        # Get salt from environment or use default
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

        cls._encryption_key = base64.urlsafe_b64encode(kdf.derive(master_key))

    def _get_fernet(self) -> Fernet:
        """Get a Fernet cipher for encryption/decryption.

        Returns:
            Fernet cipher

        Raises:
            SecureValueError: If encryption is not set up
        """
        if not self._encryption_key:
            raise SecureValueError(
                "Encryption not set up, call SecureValue.setup_encryption() first",
                code="ENCRYPTION_NOT_SETUP",
            )

        # For each value, we derive a unique key using the master key and this value's salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,
            iterations=10000,
        )

        key = base64.urlsafe_b64encode(kdf.derive(self._encryption_key))
        return Fernet(key)

    def _encrypt(self) -> None:
        """Encrypt the value if needed."""
        if self._handling_strategy not in (
            SecureValueHandling.ENCRYPT,
            SecureValueHandling.SEALED,
        ):
            return

        # Encrypt
        fernet = self._get_fernet()
        # Store as bytes directly, not as a string
        self._value = fernet.encrypt(self._value.encode("utf-8"))

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
            return self._value

        # Decrypt
        fernet = self._get_fernet()
        # Handle the _value as bytes directly
        return fernet.decrypt(self._value).decode("utf-8")

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
        return self._convert_to_original_type(self._value)

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

        return self._value

    def __str__(self) -> str:
        """Return a masked version of the value.

        Returns:
            Masked value
        """
        return "********"

    def __repr__(self) -> str:
        """Return a masked representation.

        Returns:
            Masked representation
        """
        return f"SecureValue('********', handling={self._handling_strategy})"

    def __eq__(self, other: object) -> bool:
        """Support equality comparison with raw values."""
        if isinstance(other, SecureValue):
            return bool(self.get_value() == other.get_value())
        return bool(self.get_value() == other)


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
