"""
Shared logger setup for Uno example sagas.
Provides a DI-friendly logger for all saga classes.
"""

from uno.logging import LoggerService, LoggingConfig


def get_saga_logger(saga_name: str | None = None) -> LoggerService:
    # In real DI, this would come from the container
    config = LoggingConfig()
    name = f"uno.sagas.{saga_name}" if saga_name else "uno.sagas"
    # TODO: Use DI or a logger factory for contextual/named loggers if needed.
    return LoggerService(config)
