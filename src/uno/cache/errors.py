"""Exceptions for the cache system."""

from typing import Any, Dict, Optional, Type, TypeVar

from uno.errors import AppError, ErrorCode, ErrorContext, ErrorSeverity

# Re-export error codes for convenience
__all__ = [
    'CacheError',
    'CacheMissError',
    'CacheBackendError',
    'CacheSerializationError',
    'CacheConfigurationError',
]

# Error codes
class CacheErrorCode(ErrorCode):
    """Error codes for cache-related errors."""
    CACHE_ERROR = "cache_error"
    CACHE_MISS = "cache_miss"
    CACHE_BACKEND_ERROR = "cache_backend_error"
    CACHE_SERIALIZATION_ERROR = "cache_serialization_error"
    CACHE_CONFIGURATION_ERROR = "cache_configuration_error"


class CacheError(AppError):
    """Base class for cache errors."""
    
    def __init__(
        self,
        message: str,
        *,
        code: str | ErrorCode = CacheErrorCode.CACHE_ERROR,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize the error.
        
        Args:
            message: Error message
            code: Error code
            severity: Error severity
            context: Additional context about the error
            cause: The underlying exception that caused this error
        """
        super().__init__(
            message=message,
            code=code,
            severity=severity,
            context=context,
            cause=cause,
        )


class CacheMissError(CacheError):
    """Raised when a key is not found in the cache."""
    
    def __init__(
        self,
        key: str,
        message: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize the error.
        
        Args:
            key: The cache key that was not found
            message: Optional custom error message
            context: Additional context about the error
            cause: The underlying exception that caused this error
        """
        self.key = key
        message = message or f"Cache miss for key: {key}"
        
        if context is None:
            context = {}
        
        context.update({
            'cache_key': key,
        })
        
        super().__init__(
            message=message,
            code=CacheErrorCode.CACHE_MISS,
            severity=ErrorSeverity.WARNING,  # Cache misses are typically not critical
            context=context,
            cause=cause,
        )


class CacheBackendError(CacheError):
    """Raised when there's an error with the cache backend."""
    
    def __init__(
        self,
        message: str,
        backend: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize the error.
        
        Args:
            message: Error message
            backend: Name of the cache backend that caused the error
            context: Additional context about the error
            cause: The underlying exception that caused this error
        """
        self.backend = backend
        
        if context is None:
            context = {}
        
        if backend is not None:
            context['cache_backend'] = backend
        
        super().__init__(
            message=message,
            code=CacheErrorCode.CACHE_BACKEND_ERROR,
            severity=ErrorSeverity.ERROR,
            context=context,
            cause=cause,
        )


class CacheSerializationError(CacheError):
    """Raised when there's an error serializing or deserializing cache values."""
    
    def __init__(
        self,
        message: str,
        key: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize the error.
        
        Args:
            message: Error message
            key: The cache key that caused the error
            context: Additional context about the error
            cause: The underlying exception that caused this error
        """
        self.key = key
        
        if context is None:
            context = {}
        
        if key is not None:
            context['cache_key'] = key
        
        super().__init__(
            message=message,
            code=CacheErrorCode.CACHE_SERIALIZATION_ERROR,
            severity=ErrorSeverity.ERROR,
            context=context,
            cause=cause,
        )


class CacheConfigurationError(CacheError):
    """Raised when there's an error in the cache configuration."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        """Initialize the error.
        
        Args:
            message: Error message
            config_key: The configuration key that caused the error
            context: Additional context about the error
            cause: The underlying exception that caused this error
        """
        self.config_key = config_key
        
        if context is None:
            context = {}
        
        if config_key is not None:
            context['config_key'] = config_key
        
        super().__init__(
            message=message,
            code=CacheErrorCode.CACHE_CONFIGURATION_ERROR,
            severity=ErrorSeverity.CRITICAL,  # Configuration errors are critical
            context=context,
            cause=cause,
        )


# Type variable for error classes
E = TypeVar('E', bound=CacheError)

def wrap_cache_errors(
    error_class: Type[E],
    message: Optional[str] = None,
    **context: Any,
):
    """Decorator to wrap cache-related exceptions in a specific error class.
    
    Args:
        error_class: The error class to wrap exceptions in
        message: Optional custom error message
        **context: Additional context to include with the error
        
    Returns:
        A decorator that wraps the function and handles cache errors
    """
    import asyncio
    from functools import wraps
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except CacheError:
                raise
            except Exception as e:
                error_message = message or f"Cache operation failed: {str(e)}"
                error_context = {**context}
                
                if hasattr(e, 'args') and e.args:
                    error_context['error_details'] = str(e)
                
                raise error_class(
                    message=error_message,
                    context=error_context,
                    cause=e,
                ) from e
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except CacheError:
                raise
            except Exception as e:
                error_message = message or f"Cache operation failed: {str(e)}"
                error_context = {**context}
                
                if hasattr(e, 'args') and e.args:
                    error_context['error_details'] = str(e)
                
                raise error_class(
                    message=error_message,
                    context=error_context,
                    cause=e,
                ) from e
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
