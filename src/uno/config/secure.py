"""
Secure value handling for the Uno configuration system.

This module provides tools for handling sensitive configuration values
with support for masking, encryption, and secure access.
"""

from __future__ import annotations

import base64
import os
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import (
    Any,
    ClassVar,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    cast,
)

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import Field, SecretStr
from pydantic.fields import FieldInfo
from pydantic_core import PydanticCustomError

from uno.errors import ErrorCategory, UnoError, create_error


class SecureValueError(UnoError):
    """Base class for secure value related errors."""

    def __init__(
        self, message: str, error_code: str | None = None, **context: Any
    ) -> None:
        """Initialize a secure value error.

        Args:
            message: Human-readable error message
            error_code: Error code without prefix
            **context: Additional context information
        """
        super().__init__(
            message=message,
            error_code=(
                f"CONFIG_SECURE_{error_code}" if error_code else "CONFIG_SECURE_ERROR"
            ),
            category=ErrorCategory.CONFIG,
            **context,
        )


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
    """Container for secure values with controlled access.

    This class wraps a sensitive value and controls access to it,
    providing masking for logging and optional encryption for storage.
    """

    _handling: ClassVar[dict[str, SecureValueHandling]] = {}
    _encryption_key: ClassVar[bytes | None] = None

    def __init__(
        self,
        value: T,
        handling: SecureValueHandling = SecureValueHandling.MASK,
        salt: bytes | None = None,
    ):
        """Initialize a secure value.

        Args:
            value: The sensitive value to secure
            handling: How to handle the value (mask, encrypt, seal)
            salt: Optional salt for encryption (will generate if None)
        """
        self._original_type = type(
            value
        )  # Store the original type for correct restoration
        self._value = value
        self._handling_strategy = handling
        self._salt = salt or os.urandom(16)

        # If we need to encrypt, do it now
        if handling in (SecureValueHandling.ENCRYPT, SecureValueHandling.SEALED):
            self._encrypt()

    @classmethod
    def setup_encryption(cls, master_key: str | bytes | None = None) -> None:
        """Set up the encryption system with a master key.

        Args:
            master_key: Master encryption key (will use UNO_MASTER_KEY env var if None)
        """
        if master_key is None:
            # Try to get from environment
            env_key = os.environ.get("UNO_MASTER_KEY")
            if not env_key:
                raise SecureValueError(
                    "No master encryption key provided and UNO_MASTER_KEY not set",
                    error_code="NO_MASTER_KEY",
                )
            master_key = env_key

        # Convert to bytes if needed
        if isinstance(master_key, str):
            master_key = master_key.encode("utf-8")

        # We don't store the raw master key, just derive a key from it
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"uno_framework_salt",  # Fixed salt for key derivation
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
                error_code="ENCRYPTION_NOT_SETUP",
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

        # Convert value to string for encryption
        value_str = str(self._value)

        # Encrypt
        fernet = self._get_fernet()
        encrypted = fernet.encrypt(value_str.encode("utf-8"))

        # Store encrypted value
        self._value = cast(T, encrypted)

    def _decrypt(self) -> T:
        """Decrypt the value if needed.

        Returns:
            Decrypted value
        """
        if self._handling_strategy not in (
            SecureValueHandling.ENCRYPT,
            SecureValueHandling.SEALED,
        ):
            return self._value

        # Decrypt
        fernet = self._get_fernet()
        decrypted = fernet.decrypt(cast("bytes", self._value)).decode("utf-8")

        # Convert back to original type if possible (best effort)
        try:
            if self._original_type is bool:
                return cast("T", decrypted.lower() in ("true", "1", "yes"))
            elif self._original_type is int:
                return cast("T", int(decrypted))
            elif self._original_type is float:
                return cast("T", float(decrypted))
            elif self._original_type is object:
                # object constructor doesn't accept arguments
                return cast("T", decrypted)
            else:
                try:
                    return self._original_type(decrypted)
                except TypeError:
                    # Type doesn't accept a string argument
                    return cast("T", decrypted)
        except ValueError:
            # Just return as string if conversion fails
            return cast("T", decrypted)

    def get_value(self) -> T:
        """Get the actual value, decrypting if needed.

        Returns:
            The actual value

        Raises:
            SecureValueError: If value is sealed and direct access attempted
        """
        if self._handling_strategy == SecureValueHandling.SEALED:
            raise SecureValueError(
                "Cannot access sealed value directly",
                error_code="SEALED_VALUE_ACCESS",
            )

        if self._handling_strategy == SecureValueHandling.ENCRYPT:
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
        return f"SecureValue('********')"


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
    field_info = Field(default, json_schema_extra=kwargs.pop('json_schema_extra', {}), **kwargs)
    field_info.json_schema_extra = field_info.json_schema_extra or {}
    field_info.json_schema_extra["secure"] = True
    field_info.json_schema_extra["handling"] = handling.value

    return field_info


def requires_secure_access(func: Callable) -> Callable:
    """Decorator to log access to secure configuration values.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Here we could log access or enforce additional security checks
        # For now we just pass through, but this gives us a hook point
        return func(*args, **kwargs)

    return wrapper
