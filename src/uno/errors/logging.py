import logging
import traceback
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Dict, cast


# ... existing code ...


class ErrorLogger:
    """
    Utility for logging UnoErrors with consistent formatting.

    This class provides methods to log errors with proper formatting,
    including all context from the ErrorContext.
    """

    @staticmethod
    def get_logger(name: str = None) -> logging.Logger:
        """Get a logger instance configured for error logging."""
        return logging.getLogger(name or __name__)

    @staticmethod
    def log_error(error: UnoError, logger: logging.Logger = None) -> None:
        """
        Log an error with all its context information.

        Args:
            error: The UnoError to log
            logger: Optional logger to use; if None, a default logger is created
        """
        if logger is None:
            logger = ErrorLogger.get_logger()

        # Determine log level based on severity
        level = logging.ERROR
        if error.context.severity == ErrorSeverity.CRITICAL:
            level = logging.CRITICAL
        elif error.context.severity == ErrorSeverity.WARNING:
            level = logging.WARNING
        elif error.context.severity == ErrorSeverity.INFO:
            level = logging.INFO

        # Create structured log with error details
        log_data = {
            "error_code": error.error_code,
            "category": error.context.category.name,
            "message": error.message,
        }

        # Add all additional context details
        if error.context.details:
            log_data.update(error.context.details)

        # Log the error
        logger.log(level, error.message, extra={"error_data": log_data})

        # For DEBUG level, include traceback if available
        if logger.isEnabledFor(logging.DEBUG) and hasattr(error, "traceback"):
            logger.debug(f"Traceback for {error.error_code}:\n{error.traceback}")

    @staticmethod
    def configure_logger(
        level: int = logging.INFO,
        format_string: str = None,
        include_traceback: bool = True,
    ) -> logging.Logger:
        """
        Configure a logger with standard error formatting.

        Args:
            level: The logging level to set
            format_string: Optional custom format string
            include_traceback: Whether to include tracebacks

        Returns:
            Configured logger
        """
        logger = ErrorLogger.get_logger()
        logger.setLevel(level)

        # Create formatter
        if format_string is None:
            format_string = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            if include_traceback:
                format_string += " (%(error_data)s)"

        formatter = logging.Formatter(format_string)

        # Create handler if none exist
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger
