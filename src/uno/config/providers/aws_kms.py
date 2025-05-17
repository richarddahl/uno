# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
AWS Key Management Service (KMS) provider implementation.

This module provides integration with AWS KMS for secure key management.
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

logger = logging.getLogger("uno.config.providers.aws_kms")


class AwsKmsProvider:
    """AWS KMS provider implementation."""

    def __init__(self) -> None:
        """Initialize AWS KMS provider."""
        self._client = None
        self._key_id = None
        self._region = None
        self._initialized = False

    @property
    def name(self) -> str:
        """Get the name of this provider."""
        return "aws-kms"

    @property
    def description(self) -> str:
        """Get a human-readable description of this provider."""
        return "AWS Key Management Service provider"

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the provider with AWS credentials and configuration.

        Args:
            config: AWS-specific configuration options including:
                   - key_id: KMS key ID/ARN to use (required)
                   - region: AWS region (optional, defaults to AWS_REGION env var)
                   - profile: AWS profile to use (optional)
                   - endpoint_url: Custom endpoint URL (optional, for testing)

        Raises:
            SecureValueError: If initialization fails
        """
        config = config or {}

        # Check for boto3
        try:
            import boto3
            import botocore.exceptions
        except ImportError:
            raise SecureValueError(
                "boto3 is required for AWS KMS provider. Install with 'pip install boto3'.",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        # Get KMS key ID (required)
        self._key_id = config.get("key_id") or os.environ.get("AWS_KMS_KEY_ID")
        if not self._key_id:
            raise SecureValueError(
                "AWS KMS key ID is required. Provide it in config or set AWS_KMS_KEY_ID env var.",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        # Get region
        self._region = config.get("region") or os.environ.get("AWS_REGION")
        if not self._region:
            # Try to get from AWS_DEFAULT_REGION or EC2 metadata
            self._region = os.environ.get("AWS_DEFAULT_REGION")

            if not self._region:
                # Try to get from EC2 instance metadata (if running on EC2)
                try:
                    import requests

                    response = requests.get(
                        "http://169.254.169.254/latest/meta-data/placement/region",
                        timeout=1,
                    )
                    if response.status_code == 200:
                        self._region = response.text
                except Exception:
                    # Not running on EC2 or metadata service not available
                    pass

            if not self._region:
                # Default to us-east-1 if we can't determine region
                self._region = "us-east-1"
                logger.warning(
                    "AWS region not specified. Defaulting to us-east-1. "
                    "Set the region in config or AWS_REGION env var."
                )

        # Create KMS client
        session_kwargs = {}
        if "profile" in config:
            session_kwargs["profile_name"] = config["profile"]

        session = boto3.Session(region_name=self._region, **session_kwargs)

        client_kwargs = {}
        if "endpoint_url" in config:
            client_kwargs["endpoint_url"] = config["endpoint_url"]

        # Create client in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        try:
            self._client = await loop.run_in_executor(
                None, lambda: session.client("kms", **client_kwargs)
            )
        except botocore.exceptions.ClientError as e:
            raise SecureValueError(
                f"Failed to create AWS KMS client: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

        self._initialized = True

    async def is_available(self) -> bool:
        """Check if AWS KMS is available with the provided configuration.

        Returns:
            True if AWS KMS is available, False otherwise
        """
        if not self._initialized or not self._client:
            return False

        try:
            # Try to describe the key to check access
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self._client.describe_key(KeyId=self._key_id)
            )
            return True
        except Exception as e:
            logger.warning(f"AWS KMS not available: {e}")
            return False

    async def generate_key(
        self, key_id: str | None = None, **options: Any
    ) -> tuple[str, bytes]:
        """Generate a new data key using AWS KMS.

        AWS KMS generates a data key and encrypts it with the master key.
        We store the encrypted version and return the plaintext for immediate use.

        Args:
            key_id: Optional identifier for the key (used for AWS KMS aliases)
            **options: Provider-specific options including:
                      - key_spec: KMS key spec (default: AES_256)
                      - context: Encryption context (optional)

        Returns:
            Tuple of (key_version, key_bytes)

        Raises:
            SecureValueError: If key generation fails
        """
        if not self._initialized or not self._client:
            raise SecureValueError(
                "AWS KMS provider not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            # Prepare encryption context
            context = options.get("context", {})

            # Determine key spec
            key_spec = options.get("key_spec", "AES_256")

            # Generate data key
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.generate_data_key(
                    KeyId=self._key_id, KeySpec=key_spec, EncryptionContext=context
                ),
            )

            # Get plaintext key and encrypted key
            plaintext_key = response["Plaintext"]
            encrypted_key = response["CiphertextBlob"]

            # Generate a version ID based on timestamp
            version = (
                options.get("version")
                or f"kms-{int(time.time())}-{uuid.uuid4().hex[:6]}"
            )

            # Store encrypted key with version (implement in subclass)
            await self._store_encrypted_key(
                key_id or "default", version, encrypted_key, context
            )

            return version, plaintext_key

        except Exception as e:
            raise SecureValueError(
                f"Failed to generate key from AWS KMS: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def get_key(self, key_id: str, **options: Any) -> bytes:
        """Get an existing key.

        Retrieves an encrypted data key and decrypts it with AWS KMS.

        Args:
            key_id: Identifier for the key
            **options: Provider-specific options including:
                      - version: Specific key version to get (optional)
                      - context: Encryption context for decrypting (optional)

        Returns:
            Decrypted key bytes

        Raises:
            SecureValueError: If key retrieval fails or key doesn't exist
        """
        if not self._initialized or not self._client:
            raise SecureValueError(
                "AWS KMS provider not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            # Get desired version
            version = options.get("version")

            # Get encryption context
            context = options.get("context", {})

            # Retrieve encrypted key
            encrypted_key, stored_context = await self._get_encrypted_key(
                key_id, version
            )

            # Merge stored context with provided context
            if stored_context:
                # Use stored context as base, override with provided context
                merged_context = stored_context.copy()
                merged_context.update(context)
                context = merged_context

            # Decrypt the data key
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.decrypt(
                    KeyId=self._key_id,
                    CiphertextBlob=encrypted_key,
                    EncryptionContext=context,
                ),
            )

            return response["Plaintext"]

        except Exception as e:
            raise SecureValueError(
                f"Failed to get key from AWS KMS: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def delete_key(self, key_id: str, **options: Any) -> None:
        """Delete a key.

        Note: This doesn't delete the KMS key, only the stored data key.

        Args:
            key_id: Identifier for the key
            **options: Provider-specific options including:
                      - version: Specific key version to delete (optional)

        Raises:
            SecureValueError: If key deletion fails
        """
        if not self._initialized:
            raise SecureValueError(
                "AWS KMS provider not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            # Get desired version
            version = options.get("version")

            # Delete the encrypted key
            await self._delete_encrypted_key(key_id, version)

        except Exception as e:
            raise SecureValueError(
                f"Failed to delete key: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def list_keys(self, **options: Any) -> list[str]:
        """List available keys.

        Args:
            **options: Provider-specific options including:
                      - prefix: Optional prefix to filter by

        Returns:
            List of key identifiers

        Raises:
            SecureValueError: If key listing fails
        """
        if not self._initialized:
            raise SecureValueError(
                "AWS KMS provider not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            # Get optional prefix
            prefix = options.get("prefix", "")

            # List keys
            keys = await self._list_encrypted_keys(prefix)
            return keys

        except Exception as e:
            raise SecureValueError(
                f"Failed to list keys: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def rotate_key(self, key_id: str, **options: Any) -> tuple[str, bytes]:
        """Rotate a key.

        Generate a new data key while keeping track of the previous version.

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
                "AWS KMS provider not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            # Get current version if available
            try:
                # Don't specify version to get the latest
                encrypted_key, context = await self._get_encrypted_key(key_id, None)

                # Add context to options if not already specified
                if context and "context" not in options:
                    options["context"] = context

            except SecureValueError:
                # Key doesn't exist yet, that's fine
                pass

            # Generate a new key
            version, key_bytes = await self.generate_key(key_id, **options)

            return version, key_bytes

        except Exception as e:
            raise SecureValueError(
                f"Failed to rotate key: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    # Storage methods that should be implemented by subclasses

    async def _store_encrypted_key(
        self, key_id: str, version: str, encrypted_key: bytes, context: dict[str, str]
    ) -> None:
        """Store an encrypted key.

        Default implementation uses files in the local filesystem.
        Subclasses should override this to use a more secure storage mechanism.

        Args:
            key_id: Identifier for the key
            version: Version of the key
            encrypted_key: Encrypted key bytes
            context: Encryption context

        Raises:
            SecureValueError: If storage fails
        """
        try:
            # Get storage directory
            storage_dir = self._get_storage_dir()
            os.makedirs(storage_dir, exist_ok=True)

            # Create key file path
            key_file = os.path.join(storage_dir, f"{key_id}.{version}")

            # Encode key and context
            data = {
                "encrypted_key": base64.b64encode(encrypted_key).decode("utf-8"),
                "context": context,
                "version": version,
                "key_id": key_id,
                "timestamp": time.time(),
            }

            # Write to file
            with open(key_file, "w") as f:
                json.dump(data, f)

        except Exception as e:
            raise SecureValueError(
                f"Failed to store encrypted key: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def _get_encrypted_key(
        self, key_id: str, version: str | None = None
    ) -> tuple[bytes, dict[str, str] | None]:
        """Get an encrypted key.

        Default implementation uses files in the local filesystem.
        Subclasses should override this to use a more secure storage mechanism.

        Args:
            key_id: Identifier for the key
            version: Optional specific version to get (latest if None)

        Returns:
            Tuple of (encrypted_key_bytes, encryption_context or None)

        Raises:
            SecureValueError: If key retrieval fails
        """
        try:
            # Get storage directory
            storage_dir = self._get_storage_dir()

            if version:
                # Get specific version
                key_file = os.path.join(storage_dir, f"{key_id}.{version}")
                if not os.path.exists(key_file):
                    raise SecureValueError(
                        f"Key {key_id} version {version} not found",
                        code=CONFIG_SECURE_KEY_ERROR,
                    )

                # Read key file
                with open(key_file, "r") as f:
                    data = json.load(f)

            else:
                # Get latest version
                prefix = f"{key_id}."
                key_files = [f for f in os.listdir(storage_dir) if f.startswith(prefix)]

                if not key_files:
                    raise SecureValueError(
                        f"No versions found for key {key_id}",
                        code=CONFIG_SECURE_KEY_ERROR,
                    )

                # Sort by timestamp if available, otherwise by name
                latest_file = None
                latest_timestamp = 0

                for key_file in key_files:
                    file_path = os.path.join(storage_dir, key_file)
                    try:
                        with open(file_path, "r") as f:
                            data = json.load(f)
                            timestamp = data.get("timestamp", 0)

                            if timestamp > latest_timestamp:
                                latest_timestamp = timestamp
                                latest_file = file_path

                    except Exception:
                        # Skip files that can't be parsed
                        continue

                if not latest_file:
                    # If we couldn't determine by timestamp, use filename sorting
                    # which should work for version IDs like kms-{timestamp}-{uuid}
                    key_files.sort(reverse=True)
                    latest_file = os.path.join(storage_dir, key_files[0])

                # Read latest key file
                with open(latest_file, "r") as f:
                    data = json.load(f)

            # Decode key
            encrypted_key = base64.b64decode(data["encrypted_key"])
            context = data.get("context")

            return encrypted_key, context

        except SecureValueError:
            # Re-raise SecureValueError
            raise
        except Exception as e:
            raise SecureValueError(
                f"Failed to get encrypted key: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def _delete_encrypted_key(
        self, key_id: str, version: str | None = None
    ) -> None:
        """Delete an encrypted key.

        Default implementation uses files in the local filesystem.
        Subclasses should override this to use a more secure storage mechanism.

        Args:
            key_id: Identifier for the key
            version: Optional specific version to delete (all versions if None)

        Raises:
            SecureValueError: If deletion fails
        """
        try:
            # Get storage directory
            storage_dir = self._get_storage_dir()

            if version:
                # Delete specific version
                key_file = os.path.join(storage_dir, f"{key_id}.{version}")
                if os.path.exists(key_file):
                    os.remove(key_file)

            else:
                # Delete all versions
                prefix = f"{key_id}."
                key_files = [f for f in os.listdir(storage_dir) if f.startswith(prefix)]

                for key_file in key_files:
                    file_path = os.path.join(storage_dir, key_file)
                    os.remove(file_path)

        except Exception as e:
            raise SecureValueError(
                f"Failed to delete encrypted key: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def _list_encrypted_keys(self, prefix: str = "") -> list[str]:
        """List stored encrypted keys.

        Default implementation uses files in the local filesystem.
        Subclasses should override this to use a more secure storage mechanism.

        Args:
            prefix: Optional prefix to filter by

        Returns:
            List of key identifiers

        Raises:
            SecureValueError: If listing fails
        """
        try:
            # Get storage directory
            storage_dir = self._get_storage_dir()

            # List key files
            if not os.path.exists(storage_dir):
                return []

            # Get unique key IDs (without version suffixes)
            key_ids = set()

            for filename in os.listdir(storage_dir):
                parts = filename.split(".", 1)
                if len(parts) == 2:
                    key_id = parts[0]
                    if key_id.startswith(prefix):
                        key_ids.add(key_id)

            return sorted(list(key_ids))

        except Exception as e:
            raise SecureValueError(
                f"Failed to list encrypted keys: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    def _get_storage_dir(self) -> str:
        """Get the directory for key storage.

        Returns:
            Path to storage directory
        """
        # Default to a directory in the user's home directory
        base_dir = os.environ.get("UNO_KMS_STORAGE_DIR")
        if not base_dir:
            home_dir = os.path.expanduser("~")
            base_dir = os.path.join(home_dir, ".uno", "kms_keys")

        return base_dir


# S3-backed implementation that stores keys in S3
class AwsKmsS3Provider(AwsKmsProvider):
    """AWS KMS provider with S3 storage backend."""

    def __init__(self) -> None:
        """Initialize AWS KMS provider with S3 storage."""
        super().__init__()
        self._s3_client = None
        self._s3_bucket = None
        self._s3_prefix = None

    @property
    def name(self) -> str:
        """Get the name of this provider."""
        return "aws-kms-s3"

    @property
    def description(self) -> str:
        """Get a human-readable description of this provider."""
        return "AWS KMS provider with S3 storage backend"

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the provider with AWS credentials and configuration.

        Args:
            config: AWS-specific configuration options including:
                   - key_id: KMS key ID/ARN to use (required)
                   - region: AWS region (optional, defaults to AWS_REGION env var)
                   - profile: AWS profile to use (optional)
                   - s3_bucket: S3 bucket for key storage (required)
                   - s3_prefix: Prefix for S3 objects (optional)

        Raises:
            SecureValueError: If initialization fails
        """
        config = config or {}

        # Initialize KMS provider
        await super().initialize(config)

        # Check for boto3
        try:
            import boto3
            import botocore.exceptions
        except ImportError:
            raise SecureValueError(
                "boto3 is required for AWS KMS provider. Install with 'pip install boto3'.",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        # Get S3 bucket (required)
        self._s3_bucket = config.get("s3_bucket") or os.environ.get("AWS_KMS_S3_BUCKET")
        if not self._s3_bucket:
            raise SecureValueError(
                "S3 bucket is required for S3 storage. Provide it in config or set AWS_KMS_S3_BUCKET env var.",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        # Get S3 prefix (optional)
        self._s3_prefix = config.get("s3_prefix") or os.environ.get(
            "AWS_KMS_S3_PREFIX", "uno/keys/"
        )

        # Ensure prefix ends with '/'
        if self._s3_prefix and not self._s3_prefix.endswith("/"):
            self._s3_prefix += "/"

        # Create S3 client
        session_kwargs = {}
        if "profile" in config:
            session_kwargs["profile_name"] = config["profile"]

        session = boto3.Session(region_name=self._region, **session_kwargs)

        client_kwargs = {}
        if "endpoint_url" in config:
            client_kwargs["endpoint_url"] = config["endpoint_url"]

        # Create client in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        try:
            self._s3_client = await loop.run_in_executor(
                None, lambda: session.client("s3", **client_kwargs)
            )
        except botocore.exceptions.ClientError as e:
            raise SecureValueError(
                f"Failed to create AWS S3 client: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def is_available(self) -> bool:
        """Check if AWS KMS and S3 are available with the provided configuration.

        Returns:
            True if AWS KMS and S3 are available, False otherwise
        """
        if not await super().is_available():
            return False

        if not self._s3_client or not self._s3_bucket:
            return False

        try:
            # Check if bucket exists and is accessible
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, lambda: self._s3_client.head_bucket(Bucket=self._s3_bucket)
            )
            return True
        except Exception as e:
            logger.warning(f"AWS S3 not available: {e}")
            return False

    async def _store_encrypted_key(
        self, key_id: str, version: str, encrypted_key: bytes, context: dict[str, str]
    ) -> None:
        """Store an encrypted key in S3.

        Args:
            key_id: Identifier for the key
            version: Version of the key
            encrypted_key: Encrypted key bytes
            context: Encryption context

        Raises:
            SecureValueError: If storage fails
        """
        if not self._s3_client or not self._s3_bucket:
            raise SecureValueError(
                "AWS S3 not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            # Prepare object key
            object_key = f"{self._s3_prefix}{key_id}.{version}"

            # Prepare data
            data = {
                "encrypted_key": base64.b64encode(encrypted_key).decode("utf-8"),
                "context": context,
                "version": version,
                "key_id": key_id,
                "timestamp": time.time(),
            }

            # Convert to JSON
            json_data = json.dumps(data)

            # Upload to S3
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._s3_client.put_object(
                    Bucket=self._s3_bucket,
                    Key=object_key,
                    Body=json_data.encode("utf-8"),
                    ContentType="application/json",
                ),
            )

        except Exception as e:
            raise SecureValueError(
                f"Failed to store encrypted key in S3: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def _get_encrypted_key(
        self, key_id: str, version: str | None = None
    ) -> tuple[bytes, dict[str, str] | None]:
        """Get an encrypted key from S3.

        Args:
            key_id: Identifier for the key
            version: Optional specific version to get (latest if None)

        Returns:
            Tuple of (encrypted_key_bytes, encryption_context or None)

        Raises:
            SecureValueError: If key retrieval fails
        """
        if not self._s3_client or not self._s3_bucket:
            raise SecureValueError(
                "AWS S3 not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            loop = asyncio.get_event_loop()

            if version:
                # Get specific version
                object_key = f"{self._s3_prefix}{key_id}.{version}"

                try:
                    response = await loop.run_in_executor(
                        None,
                        lambda: self._s3_client.get_object(
                            Bucket=self._s3_bucket,
                            Key=object_key,
                        ),
                    )

                    # Read and parse data
                    body = await loop.run_in_executor(
                        None, lambda: response["Body"].read().decode("utf-8")
                    )

                    data = json.loads(body)

                except Exception as e:
                    raise SecureValueError(
                        f"Key {key_id} version {version} not found in S3: {e}",
                        code=CONFIG_SECURE_KEY_ERROR,
                    ) from e

            else:
                # List objects with prefix
                prefix = f"{self._s3_prefix}{key_id}."

                response = await loop.run_in_executor(
                    None,
                    lambda: self._s3_client.list_objects_v2(
                        Bucket=self._s3_bucket,
                        Prefix=prefix,
                    ),
                )

                if "Contents" not in response or not response["Contents"]:
                    raise SecureValueError(
                        f"No versions found for key {key_id} in S3",
                        code=CONFIG_SECURE_KEY_ERROR,
                    )

                # Find the latest version based on LastModified
                latest_object = None
                latest_time = None

                for obj in response["Contents"]:
                    if latest_time is None or obj["LastModified"] > latest_time:
                        latest_time = obj["LastModified"]
                        latest_object = obj

                if not latest_object:
                    raise SecureValueError(
                        f"Could not determine latest version for key {key_id} in S3",
                        code=CONFIG_SECURE_KEY_ERROR,
                    )

                # Get the latest object
                object_key = latest_object["Key"]

                response = await loop.run_in_executor(
                    None,
                    lambda: self._s3_client.get_object(
                        Bucket=self._s3_bucket,
                        Key=object_key,
                    ),
                )

                # Read and parse data
                body = await loop.run_in_executor(
                    None, lambda: response["Body"].read().decode("utf-8")
                )

                data = json.loads(body)

            # Decode key
            encrypted_key = base64.b64decode(data["encrypted_key"])
            context = data.get("context")

            return encrypted_key, context

        except SecureValueError:
            # Re-raise SecureValueError
            raise
        except Exception as e:
            raise SecureValueError(
                f"Failed to get encrypted key from S3: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def _delete_encrypted_key(
        self, key_id: str, version: str | None = None
    ) -> None:
        """Delete an encrypted key from S3.

        Args:
            key_id: Identifier for the key
            version: Optional specific version to delete (all versions if None)

        Raises:
            SecureValueError: If deletion fails
        """
        if not self._s3_client or not self._s3_bucket:
            raise SecureValueError(
                "AWS S3 not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            loop = asyncio.get_event_loop()

            if version:
                # Delete specific version
                object_key = f"{self._s3_prefix}{key_id}.{version}"

                await loop.run_in_executor(
                    None,
                    lambda: self._s3_client.delete_object(
                        Bucket=self._s3_bucket,
                        Key=object_key,
                    ),
                )

            else:
                # List objects with prefix
                prefix = f"{self._s3_prefix}{key_id}."

                response = await loop.run_in_executor(
                    None,
                    lambda: self._s3_client.list_objects_v2(
                        Bucket=self._s3_bucket,
                        Prefix=prefix,
                    ),
                )

                if "Contents" in response and response["Contents"]:
                    # Delete multiple objects
                    objects = [{"Key": obj["Key"]} for obj in response["Contents"]]

                    await loop.run_in_executor(
                        None,
                        lambda: self._s3_client.delete_objects(
                            Bucket=self._s3_bucket,
                            Delete={"Objects": objects},
                        ),
                    )

        except Exception as e:
            raise SecureValueError(
                f"Failed to delete encrypted key from S3: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e

    async def _list_encrypted_keys(self, prefix: str = "") -> list[str]:
        """List stored encrypted keys in S3.

        Args:
            prefix: Optional prefix to filter by

        Returns:
            List of key identifiers

        Raises:
            SecureValueError: If listing fails
        """
        if not self._s3_client or not self._s3_bucket:
            raise SecureValueError(
                "AWS S3 not initialized",
                code=CONFIG_SECURE_KEY_ERROR,
            )

        try:
            loop = asyncio.get_event_loop()

            # List objects with prefix
            s3_prefix = f"{self._s3_prefix}{prefix}"

            response = await loop.run_in_executor(
                None,
                lambda: self._s3_client.list_objects_v2(
                    Bucket=self._s3_bucket,
                    Prefix=s3_prefix,
                ),
            )

            if "Contents" not in response or not response["Contents"]:
                return []

            # Extract key IDs (without version suffixes)
            key_ids = set()

            prefix_len = len(self._s3_prefix)
            for obj in response["Contents"]:
                key = obj["Key"][prefix_len:]  # Remove S3 prefix
                parts = key.split(".", 1)
                if len(parts) == 2:
                    key_id = parts[0]
                    if key_id.startswith(prefix):
                        key_ids.add(key_id)

            return sorted(list(key_ids))

        except Exception as e:
            raise SecureValueError(
                f"Failed to list encrypted keys from S3: {e}",
                code=CONFIG_SECURE_KEY_ERROR,
            ) from e


# Register these providers with the registry
from uno.config.key_provider import ProviderRegistry

# Register providers when module is imported
ProviderRegistry.register_provider(AwsKmsProvider, "aws-kms")
ProviderRegistry.register_provider(AwsKmsS3Provider, "aws-kms-s3")
