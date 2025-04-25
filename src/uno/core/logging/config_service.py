"""
Runtime-updatable LoggingConfigService for Uno logging system.

Allows dynamic updates to logging configuration at runtime, including log level, format, output, and more.
Integrates with LoggerService to apply changes immediately.
"""
from __future__ import annotations

from typing import Any

from uno.core.errors.base import FrameworkError
from uno.core.logging.logger import LoggerService, LoggingConfig


class LoggingConfigUpdateError(FrameworkError):
    """Raised when an invalid logging config update is attempted."""
    def __init__(self, message: str):
        super().__init__(message, error_code="LOGGING_CONFIG_UPDATE_ERROR")

class LoggingConfigService:
    """
    Service for managing and updating logging configuration at runtime.
    """
    def __init__(self, logger_service: LoggerService) -> None:
        self._logger_service = logger_service
        self._config = logger_service._config

    def get_config(self) -> LoggingConfig:
        """Return the current logging configuration (as a pydantic object)."""
        return self._config

    def update_config(self, **kwargs: Any) -> LoggingConfig:
        """
        Update the logging configuration at runtime. Supported fields are those in LoggingConfig.
        Applies changes immediately to all loggers and handlers via LoggerService.reload_config().
        Raises LoggingConfigUpdateError on invalid update.
        """
        valid_fields = set(type(self._config).model_fields.keys())
        invalid = [k for k in kwargs if k not in valid_fields]
        if invalid:
            raise LoggingConfigUpdateError(f"Invalid logging config field(s): {invalid}")
        try:
            # Validate and create a new config
            new_config = self._config.model_copy(update=kwargs)
            # Apply to logger service
            self._logger_service._config = new_config
            self._logger_service.reload_config()
            self._config = new_config
            return new_config
        except Exception as exc:
            raise LoggingConfigUpdateError(f"Invalid logging config update: {exc}") from exc

    def set_level(self, level: str) -> None:
        """Convenience: update log level at runtime."""
        self.update_config(LEVEL=level)

    def set_json_format(self, enabled: bool) -> None:
        """Convenience: toggle JSON log output at runtime."""
        self.update_config(JSON_FORMAT=enabled)

    def set_file_output(self, enabled: bool, file_path: str | None = None) -> None:
        """Convenience: enable/disable file output and optionally set file path at runtime."""
        update = {"FILE_OUTPUT": enabled}
        if file_path is not None:
            update["FILE_PATH"] = file_path
        self.update_config(**update)

    def set_console_output(self, enabled: bool) -> None:
        """Convenience: enable/disable console output at runtime."""
        self.update_config(CONSOLE_OUTPUT=enabled)
