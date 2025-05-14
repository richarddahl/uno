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

# Default KDF parameters (upgradeable)
DEFAULT_KDF_PARAMS = {
    "algorithm": "sha256",
    "iterations": 200_000,
    "length": 32,
}

_SUPPORTED_KDF_ALGOS = {
    "sha256": lambda: hashes.SHA256(),
    # Add more algorithms here if needed
}


from pydantic import Field, BaseModel, TypeAdapter

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

    SECURITY WARNING:
    While __str__, __repr__, __getstate__, and __dir__ mask sensitive values,
    advanced debugging, pickling, or introspection (e.g., vars(), __dict__, memory inspection)
    may still expose secrets. Never log, print, or serialize SecureValue objects directly.

    This class ensures sensitive configuration values are handled securely. It preserves the original type
    and provides masking/encryption as specified by the handling strategy. Use `get_value()` to retrieve
    the original value with type fidelity. String representation always returns a masked value ("******")
    for masked fields, regardless of the underlying type.

    Note: Secure memory wiping is best-effort in Python. Due to garbage collection and string immutability,
    some sensitive data may remain in memory after use. This class will overwrite internal buffers and attributes
    where possible, but cannot guarantee absolute memory security.
    """
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
        kdf_params: dict | None = None,  # Optionally override KDF params
    ):
        """
        Initialize a secure value.

        Args:
            value: The sensitive value to secure. Must be a primitive (str, int, float, bool, None),
                collection (dict, list, tuple, set), or Enum. Other types will raise TypeError.
            handling: How to handle the value (mask, encrypt, seal).
            salt: Optional salt for encryption (random if None).
            key_version: Optional specific key version to use (current key if None).
            kdf_params: Optional dict of KDF parameters (algorithm, iterations, length).
        Raises:
            TypeError: If value is not a supported type.
            SecureValueError: If specified key version doesn't exist.
        """
        allowed = (str, int, float, bool, type(None), dict, list, tuple, set)
        if not (isinstance(value, allowed) or isinstance(value, Enum)):
            raise TypeError(
                f"SecureValue only supports primitive types, collections, or Enum. Got: {type(value)}"
            )
        self._handling_strategy = handling
        self._salt = salt or os.urandom(16)
        self._key_version = key_version or self._current_key_version
        self._kdf_params = kdf_params or DEFAULT_KDF_PARAMS.copy()

        # Store type info for restoration
        self._type_info = None
        if isinstance(value, BaseModel):
            self._original_type = type(value)
            self._type_info = {
                "module": value.__class__.__module__,
                "qualname": value.__class__.__qualname__,
            }
            payload = {"type": self._type_info, "data": value.model_dump()}
            self._serialized_value = json.dumps(payload)
            self._value = self._serialized_value
            self._complex_type = True
        elif isinstance(value, (dict, list, tuple, set)):
            self._original_type = type(value)
            payload = {"type": {"builtin": self._original_type.__name__}, "data": value}
            self._serialized_value = json.dumps(payload)
            self._value = self._serialized_value
            self._complex_type = True
        elif isinstance(value, Enum):
            self._original_type = type(value)
            payload = {"type": {"enum": self._original_type.__name__, "module": value.__class__.__module__}, "data": value.value}
            self._serialized_value = json.dumps(payload)
            self._value = self._serialized_value
            self._complex_type = False
            self._is_enum = True
        else:
            self._original_type = type(value)
            self._serialized_value = str(value)
            self._value = self._serialized_value
            self._complex_type = False
            self._is_enum = False
        self._original_value = value

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

    def _get_fernet(self, key_version: str | None = None, kdf_params: dict | None = None) -> tuple[Fernet, str]:
        """Get a Fernet cipher for encryption/decryption.

        Args:
            key_version: Specific key version to use (defaults to this value's key version)
            kdf_params: Dict of KDF params (algorithm, iterations, length)

        Returns:
            Tuple of (Fernet cipher, key version used)

        Raises:
            SecureValueError: If encryption is not set up or key version is invalid
        """
        version_to_use = key_version or self._key_version
        if not version_to_use:
            raise SecureValueError(
                "No key version specified and no current key set",
                code="NO_KEY_VERSION",
            )
        if not hasattr(self, '_encryption_keys') or version_to_use not in self._encryption_keys:
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
        # Use provided KDF params or fall back to self._kdf_params
        params = (kdf_params or getattr(self, '_kdf_params', None) or DEFAULT_KDF_PARAMS)
        algo_name = params.get("algorithm", "sha256")
        algo = _SUPPORTED_KDF_ALGOS[algo_name]()
        length = params.get("length", 32)
        iterations = params.get("iterations", 200_000)
        kdf = PBKDF2HMAC(
            algorithm=algo,
            length=length,
            salt=self._salt,
            iterations=iterations,
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
        fernet, used_version = self._get_fernet(key_version, self._kdf_params)
        self._key_version = used_version
        value_str = (
            self._serialized_value.decode("utf-8")
            if isinstance(self._serialized_value, bytes)
            else self._serialized_value
        )
        # Store KDF params in metadata
        metadata = {
            "version": used_version,
            "kdf_params": self._kdf_params,
            "value": value_str,
        }
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
            return (
                self._value.decode("utf-8")
                if isinstance(self._value, bytes)
                else str(self._value)
            )
        try:
            # Try to decrypt and parse metadata
            # First, decrypt with default/fallback KDF params in case metadata is not present
            fernet, _ = self._get_fernet(kdf_params=self._kdf_params)
            decrypted_bytes = fernet.decrypt(self._value)
            metadata = json.loads(decrypted_bytes.decode("utf-8"))
            # If kdf_params present in metadata, re-derive and re-decrypt
            kdf_params = metadata.get("kdf_params")
            if kdf_params:
                fernet, _ = self._get_fernet(kdf_params=kdf_params)
                decrypted_bytes = fernet.decrypt(self._value)
                metadata = json.loads(decrypted_bytes.decode("utf-8"))
                self._kdf_params = kdf_params
            if isinstance(metadata, dict) and "value" in metadata:
                return str(metadata["value"])
            return decrypted_bytes.decode("utf-8")
        except (json.JSONDecodeError, KeyError):
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
        # No need to overwrite self._value; _encrypt will use the current serialization
        self._encrypt(key_version=version_to_use)
        self._logger.info(
            f"Rotated secure value from key {self._key_version} to {version_to_use}"
        )

    def rotate_kdf(self, new_kdf_params: dict) -> None:
        """
        Re-encrypt this value with new KDF parameters (e.g., to upgrade security).
        Args:
            new_kdf_params: dict with new KDF parameters (algorithm, iterations, length)
        """
        if self._handling_strategy not in (
            SecureValueHandling.ENCRYPT,
            SecureValueHandling.SEALED,
        ):
            return
        self._kdf_params = new_kdf_params.copy()
        self._encrypt(key_version=self._key_version)
        self._logger.info(f"Rotated secure value to new KDF params: {new_kdf_params}")

    def _convert_to_original_type(self, value_str: str) -> T:
        """Convert a string value back to its original type, using Pydantic when possible."""
        # Handle None type
        if self._original_type is type(None):
            if value_str == "None":
                return cast(T, None)
            return cast(T, None)
        try:
            parsed = json.loads(value_str)
        except Exception:
            parsed = value_str
        # Handle Pydantic model restoration
        if isinstance(parsed, dict) and "type" in parsed and "data" in parsed:
            type_info = parsed["type"]
            data = parsed["data"]
            if "module" in type_info and "qualname" in type_info:
                # Pydantic model
                import importlib
                module = importlib.import_module(type_info["module"])
                cls = module
                for attr in type_info["qualname"].split("."):
                    cls = getattr(cls, attr)
                return TypeAdapter(cls).validate_python(data)
            elif "builtin" in type_info:
                # Builtin container
                if type_info["builtin"] == "set":
                    return cast(T, set(data))
                if type_info["builtin"] == "tuple":
                    return cast(T, tuple(data))
                return cast(T, data)
            elif "enum" in type_info:
                # Enum
                import importlib
                module = importlib.import_module(type_info["module"])
                enum_cls = getattr(module, type_info["enum"])
                for member in enum_cls:
                    if member.value == data:
                        return cast(T, member)
                return cast(T, data)
        # Handle primitive types
        if self._original_type is bool:
            return cast(T, value_str.lower() in ("true", "1", "yes"))
        if self._original_type is int:
            return cast(T, int(value_str))
        if self._original_type is float:
            return cast(T, float(value_str))
        # For strings and fallback
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
            self._serialized_value.decode("utf-8")
            if isinstance(self._serialized_value, bytes)
            else self._serialized_value
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

    def clear(self) -> None:
        """
        Overwrite sensitive data in memory (best effort).
        This should be called when the value is no longer needed.
        Robust to missing attributes if construction failed.
        """
        # Overwrite _value only if it exists
        if hasattr(self, '_value'):
            if isinstance(self._value, bytearray):
                for i in range(len(self._value)):
                    self._value[i] = 0
            elif isinstance(self._value, (str, bytes)):
                self._value = "\x00" * len(self._value) if isinstance(self._value, str) else b"\x00" * len(self._value)
        # Overwrite original_value if possible
        if hasattr(self, '_original_value'):
            self._original_value = None
        # Overwrite salt
        if hasattr(self, '_salt') and isinstance(self._salt, (bytes, bytearray)):
            self._salt = b"\x00" * len(self._salt)
        # Overwrite decrypted type info
        if hasattr(self, '_type_info'):
            self._type_info = None


    def __enter__(self):
        """Allow use as a context manager. Returns self."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Automatically clear sensitive data when exiting context."""
        self.clear()

    def __del__(self):
        self.clear()

    def __getstate__(self):
        # Mask sensitive fields during pickling or introspection
        state = self.__dict__.copy()
        for k in ['_value', '_original_value', '_serialized_value', '_salt']:
            if k in state:
                state[k] = '******'
        return state

    def __dir__(self):
        # Hide sensitive attributes from dir()
        return [attr for attr in super().__dir__() if attr not in ('_value', '_original_value', '_serialized_value', '_salt')]




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
