"""Logging utilities for the cache system."""

import logging
from typing import Any, Optional

from uno.logging import LoggerProtocol, get_logger


class CacheLogger:
    """Logger for cache operations with structured logging."""
    
    def __init__(
        self,
        name: str = "uno.cache",
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """Initialize the cache logger.
        
        Args:
            name: Logger name
            logger: Optional logger instance to use
        """
        self._logger = logger or get_logger(name)
    
    def debug(
        self,
        message: str,
        key: Optional[str] = None,
        ttl: Optional[float] = None,
        **extra: Any,
    ) -> None:
        """Log a debug message."""
        self._log(logging.DEBUG, message, key, ttl, **extra)
    
    def info(
        self,
        message: str,
        key: Optional[str] = None,
        ttl: Optional[float] = None,
        **extra: Any,
    ) -> None:
        """Log an info message."""
        self._log(logging.INFO, message, key, ttl, **extra)
    
    def warning(
        self,
        message: str,
        key: Optional[str] = None,
        ttl: Optional[float] = None,
        **extra: Any,
    ) -> None:
        """Log a warning message."""
        self._log(logging.WARNING, message, key, ttl, **extra)
    
    def error(
        self,
        message: str,
        key: Optional[str] = None,
        ttl: Optional[float] = None,
        **extra: Any,
    ) -> None:
        """Log an error message."""
        self._log(logging.ERROR, message, key, ttl, **extra)
    
    def exception(
        self,
        message: str,
        exc_info: Optional[Any] = None,
        key: Optional[str] = None,
        ttl: Optional[float] = None,
        **extra: Any,
    ) -> None:
        """Log an exception."""
        extra = self._prepare_extra(key, ttl, **extra)
        self._logger.exception(message, exc_info=exc_info, extra=extra)
    
    def _log(
        self,
        level: int,
        message: str,
        key: Optional[str] = None,
        ttl: Optional[float] = None,
        **extra: Any,
    ) -> None:
        """Log a message with the given log level."""
        extra = self._prepare_extra(key, ttl, **extra)
        self._logger.log(level, message, extra=extra)
    
    @staticmethod
    def _prepare_extra(
        key: Optional[str] = None,
        ttl: Optional[float] = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """Prepare extra fields for logging."""
        result = {}
        
        if key is not None:
            result["cache_key"] = key
        
        if ttl is not None:
            result["cache_ttl"] = ttl
        
        result.update(extra)
        return result


# Default logger instance
logger = CacheLogger()
