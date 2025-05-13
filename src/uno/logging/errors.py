import asyncio
import logging
from typing import Any
from pydantic import BaseModel
from enum import Enum


class ErrorSeverity(str, Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class LoggingErrorContext(BaseModel):
    code: str
    severity: ErrorSeverity = ErrorSeverity.ERROR
    context: dict[str, str] = {}


class LoggingError(Exception):
    """Base class for all Uno logging-related errors (Uno idiom: local, Pydantic context)."""

    def __init__(
        self,
        message: str,
        code: str = "LOG_ERROR",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        **context: str,
    ) -> None:
        self.message = message
        self.context = LoggingErrorContext(
            code=code,
            severity=severity,
            context=context,
        )
        super().__init__(message)


class ErrorLogger:
    """
    Utility for logging Uno logging errors with context and async support.
    Logger instance must be provided via DI.
    """

    def __init__(self, logger: logging.Logger) -> None:
        if logger is None:
            raise ValueError("Logger instance must be provided via DI")
        self.logger = logger

    async def log_error(self, error: LoggingError) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._log_error_sync, error)

    async def _log_error_sync(self, error: LoggingError) -> None:
        level = logging.ERROR
        severity = error.context.severity
        if severity == ErrorSeverity.CRITICAL:
            level = logging.CRITICAL
        elif severity == ErrorSeverity.WARNING:
            level = logging.WARNING
        elif severity == ErrorSeverity.INFO:
            level = logging.INFO
        log_data = {
            "code": error.context.code,
            "message": str(error),
            "severity": severity.value,
            "context": error.context.context,
        }
        await self.logger.log(level, "Error occurred", extra={"error": log_data})
        if hasattr(error, "__traceback__") and error.__traceback__ is not None:
            await self.logger.debug(
                f"Traceback for {error.context.code}:", exc_info=error
            )
