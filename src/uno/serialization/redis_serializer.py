"""Redis-specific serialization utilities."""

from typing import Any, Type, TypeVar, cast

from pydantic import BaseModel

from .serializer import (
    CompressionType,
    JsonSerializer,
    SerializationError,
    Serializer,
    get_serializer,
)

T = TypeVar('T', bound=BaseModel)


class RedisSerializer:
    """Redis serializer that handles compression and versioning.
    
    This serializer wraps the standard serializers to provide Redis-specific
    functionality like key prefixing and versioning.
    """
    
    def __init__(
        self,
        key_prefix: str = "uno:",
        compression: CompressionType = CompressionType.NONE,
        serializer: Serializer | None = None,
    ) -> None:
        """Initialize the Redis serializer.
        
        Args:
            key_prefix: Prefix for all Redis keys
            compression: Default compression type
            serializer: Custom serializer instance (uses JsonSerializer if None)
        """
        self.key_prefix = key_prefix
        self._compression = compression
        self._serializer = serializer or JsonSerializer(compression=compression)
    
    def get_key(self, key: str) -> str:
        """Get the full Redis key with prefix."""
        return f"{self.key_prefix}{key}"
    
    def serialize_value(self, value: BaseModel) -> bytes:
        """Serialize a value for storage in Redis."""
        try:
            return self._serializer.serialize(value)
        except Exception as e:
            raise SerializationError(f"Failed to serialize value: {e}") from e
    
    def deserialize_value(self, data: bytes, model_type: Type[T]) -> T:
        """Deserialize a value from Redis."""
        if not data:
            raise SerializationError("No data to deserialize")
            
        try:
            return self._serializer.deserialize(data, model_type)
        except Exception as e:
            raise SerializationError(f"Failed to deserialize value: {e}") from e


def get_redis_serializer(
    key_prefix: str = "uno:",
    compression: str | CompressionType = CompressionType.NONE,
    **kwargs: Any,
) -> RedisSerializer:
    """Get a Redis serializer with the specified configuration.
    
    Args:
        key_prefix: Prefix for all Redis keys
        compression: Compression type or name ('gzip', 'lzma', 'zlib', 'none')
        **kwargs: Additional arguments for the serializer
        
    Returns:
        RedisSerializer instance
    """
    serializer = get_serializer(compression=compression, **kwargs)
    return RedisSerializer(key_prefix=key_prefix, serializer=serializer)
