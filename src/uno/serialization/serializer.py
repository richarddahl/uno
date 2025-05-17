"""Serialization utilities with compression support."""

import gzip
import json
import lzma
import zlib
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, ClassVar, Dict, Optional, Type, TypeVar, Union, cast
from uuid import UUID

from pydantic import BaseModel, ValidationError

from uno.errors import SerializationError
from uno.logging import LoggerProtocol, get_logger
from uno.metrics import measure_time

T = TypeVar('T', bound=BaseModel)


class CompressionType(Enum):
    """Supported compression types for serialization."""
    
    NONE = auto()
    GZIP = auto()
    LZMA = auto()
    ZLIB = auto()
    
    @classmethod
    def from_string(cls, value: str) -> 'CompressionType':
        """Get compression type from string."""
        try:
            return cls[value.upper()]
        except KeyError as e:
            raise ValueError(f"Invalid compression type: {value}") from e


class SerializationFormat(Enum):
    """Supported serialization formats."""
    
    JSON = auto()
    # Add more formats as needed (e.g., MSGPACK, PROTOBUF, etc.)


class SerializationMetadata(BaseModel):
    """Metadata for serialized data."""
    
    format: SerializationFormat
    compression: CompressionType
    schema_version: str
    model_type: str
    
    class Config:
        use_enum_values = True
        frozen = True


class Serializer(ABC):
    """Base class for serializers with compression support."""
    
    def __init__(
        self,
        compression: CompressionType = CompressionType.NONE,
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        self.compression = compression
        self._logger = logger or get_logger("uno.serialization.serializer")
    
    @abstractmethod
    def serialize(self, obj: BaseModel) -> bytes:
        """Serialize an object to bytes."""
        ...
    
    @abstractmethod
    def deserialize(self, data: bytes, model_type: Type[T]) -> T:
        """Deserialize bytes to an object."""
        ...
    
    def _compress(self, data: bytes) -> tuple[bytes, CompressionType]:
        """Compress data using the configured compression."""
        if self.compression == CompressionType.NONE:
            return data, self.compression
            
        try:
            if self.compression == CompressionType.GZIP:
                return gzip.compress(data), self.compression
            elif self.compression == CompressionType.LZMA:
                return lzma.compress(data), self.compression
            elif self.compression == CompressionType.ZLIB:
                return zlib.compress(data), self.compression
            else:
                raise ValueError(f"Unsupported compression type: {self.compression}")
        except Exception as e:
            self._logger.warning(
                "Failed to compress data with %s: %s. Falling back to no compression.",
                self.compression.name,
                str(e),
                exc_info=True,
            )
            return data, CompressionType.NONE
    
    def _decompress(self, data: bytes, compression: CompressionType) -> bytes:
        """Decompress data using the specified compression."""
        if compression == CompressionType.NONE:
            return data
            
        try:
            if compression == CompressionType.GZIP:
                return gzip.decompress(data)
            elif compression == CompressionType.LZMA:
                return lzma.decompress(data)
            elif compression == CompressionType.ZLIB:
                return zlib.decompress(data)
            else:
                raise ValueError(f"Unsupported compression type: {compression}")
        except Exception as e:
            self._logger.error(
                "Failed to decompress data with %s: %s",
                compression.name,
                str(e),
                exc_info=True,
            )
            raise SerializationError(f"Failed to decompress data: {e}") from e


class JsonSerializer(Serializer):
    """JSON serializer with compression support."""
    
    def __init__(
        self,
        compression: CompressionType = CompressionType.NONE,
        logger: Optional[LoggerProtocol] = None,
        indent: Optional[int] None,
        ensure_ascii: bool = False,
        allow_nan: bool = False,
        sort_keys: bool = False,
        **json_dumps_kwargs: Any,
    ) -> None:
        super().__init__(compression, logger)
        self._indent = indent
        self._ensure_ascii = ensure_ascii
        self._allow_nan = allow_nan
        self._sort_keys = sort_keys
        self._json_dumps_kwargs = json_dumps_kwargs
    
    @measure_time(namespace="serialization")
    def serialize(self, obj: BaseModel) -> bytes:
        """Serialize a Pydantic model to JSON bytes with optional compression."""
        try:
            # Convert model to JSON string
            json_str = obj.model_dump_json(
                indent=self._indent,
                ensure_ascii=self._ensure_ascii,
                allow_nan=self._allow_nan,
                sort_keys=self._sort_keys,
                **self._json_dumps_kwargs,
            )
            
            # Convert to bytes
            data = json_str.encode('utf-8')
            
            # Compress if needed
            compressed_data, compression_used = self._compress(data)
            
            # Create metadata
            metadata = SerializationMetadata(
                format=SerializationFormat.JSON,
                compression=compression_used,
                schema_version=getattr(obj, '__version__', '1.0'),
                model_type=f"{obj.__class__.__module__}.{obj.__class__.__name__}",
            )
            
            # Combine metadata and data
            result = json.dumps({
                '_metadata': metadata.model_dump(),
                'data': compressed_data.decode('latin1')  # Store binary as string
            }).encode('utf-8')
            
            return result
            
        except Exception as e:
            self._logger.error("Failed to serialize object: %s", e, exc_info=True)
            raise SerializationError(f"Failed to serialize object: {e}") from e
    
    @measure_time(namespace="deserialization")
    def deserialize(self, data: bytes, model_type: Type[T]) -> T:
        """Deserialize JSON bytes to a Pydantic model with optional decompression."""
        try:
            # Parse the wrapper JSON
            wrapper = json.loads(data.decode('utf-8'))
            
            # Extract metadata and data
            metadata_dict = wrapper.get('_metadata', {})
            compressed_data = wrapper['data'].encode('latin1')
            
            # Parse metadata
            try:
                metadata = SerializationMetadata.model_validate(metadata_dict)
            except ValidationError as e:
                self._logger.warning(
                    "Failed to parse metadata: %s. Using defaults.",
                    e,
                    exc_info=True,
                )
                metadata = SerializationMetadata(
                    format=SerializationFormat.JSON,
                    compression=CompressionType.NONE,
                    schema_version='1.0',
                    model_type=model_type.__name__,
                )
            
            # Decompress if needed
            json_bytes = self._decompress(compressed_data, metadata.compression)
            
            # Parse JSON to dict
            obj_dict = json.loads(json_bytes)
            
            # Convert to model
            return model_type.model_validate(obj_dict)
            
        except json.JSONDecodeError as e:
            self._logger.error("Invalid JSON data: %s", e, exc_info=True)
            raise SerializationError("Invalid JSON data") from e
        except ValidationError as e:
            self._logger.error("Validation error during deserialization: %s", e, exc_info=True)
            raise SerializationError("Validation error during deserialization") from e
        except Exception as e:
            self._logger.error("Failed to deserialize object: %s", e, exc_info=True)
            raise SerializationError(f"Failed to deserialize object: {e}") from e


def get_serializer(
    format: str = 'json',
    compression: Union[str, CompressionType] = CompressionType.NONE,
    **kwargs: Any,
) -> Serializer:
    """Get a serializer instance.
    
    Args:
        format: Serialization format ('json')
        compression: Compression type or name ('gzip', 'lzma', 'zlib', 'none')
        **kwargs: Additional arguments for the serializer
        
    Returns:
        Serializer instance
        
    Raises:
        ValueError: If the format or compression type is invalid
    """
    if isinstance(compression, str):
        compression = CompressionType.from_string(compression)
    
    if format.lower() == 'json':
        return JsonSerializer(compression=compression, **kwargs)
    else:
        raise ValueError(f"Unsupported format: {format}")
