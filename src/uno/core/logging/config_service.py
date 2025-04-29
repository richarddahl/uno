"""
Runtime-updatable LoggingConfigService for Uno logging system.

Allows dynamic updates to logging configuration at runtime, including log level, format, output, and more.
Integrates with LoggerService to apply changes immediately.
"""
from __future__ import annotations

from typing import Any

from uno.core.errors.base import FrameworkError

from uno.core.errors.result import Result, Success, Failure


class LoggingConfigUpdateError(FrameworkError):
    """Raised when an invalid logging config update is attempted."""
    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message, error_code="LOGGING_CONFIG_UPDATE_ERROR")
        self.context = context or {}

class LoggingConfigService:
    """
    Service for managing and updating logging configuration at runtime.
    """
    def __init__(self, logger_service):
        from uno.core.logging.logger import LoggerService
        self._logger_service: LoggerService = logger_service
        self._config = logger_service._config

    def get_config(self):
        from uno.core.logging.logger import LoggingConfig
        return self._config

    def update_config(self, **kwargs: Any):
        from uno.core.logging.logger import LoggingConfig
        valid_fields = set(type(self._config).model_fields.keys())
        invalid = [k for k in kwargs if k not in valid_fields]
        if invalid:
            err = LoggingConfigUpdateError(
                f"Invalid logging config field(s): {invalid}",
                context={"invalid_fields": invalid, "update": kwargs},
            )
            self._logger_service.structured_log(
                "ERROR",
                f"Invalid logging config field(s): {invalid}",
                name="uno.core.logging.config_service.update_config",
                error=err,
                invalid_fields=invalid,
                update_kwargs=kwargs,
            )
            return Failure(err)
        try:
            # Validate and create a new config
            new_config = self._config.model_copy(update=kwargs)
            # Apply to logger service
            self._logger_service._config = new_config
            self._logger_service.reload_config()
            self._config = new_config
            return Success(new_config)
        except Exception as exc:
            err = LoggingConfigUpdateError(
                f"Invalid logging config update: {exc}",
                context={"update": kwargs, "error_message": str(exc)},
            )
            self._logger_service.structured_log(
                "ERROR",
                f"Failed to update logging config: {exc}",
                name="uno.core.logging.config_service.update_config",
                error=exc,
                update_kwargs=kwargs,
            )
            return Failure(err)

    def set_level(self, level: str) -> Result[LoggingConfig, LoggingConfigUpdateError]:
        """Convenience: update log level at runtime."""
        return self.update_config(LEVEL=level)

    def set_json_format(self, enabled: bool) -> Result[LoggingConfig, LoggingConfigUpdateError]:
        """Convenience: toggle JSON log output at runtime."""
        return self.update_config(JSON_FORMAT=enabled)

    def set_file_output(self, enabled: bool, file_path: str | None = None) -> Result[LoggingConfig, LoggingConfigUpdateError]:
        """Convenience: enable/disable file output and optionally set file path at runtime."""
        update = {"FILE_OUTPUT": enabled}
        if file_path is not None:
            update["FILE_PATH"] = file_path
        return self.update_config(**update)

    def set_console_output(self, enabled: bool) -> Result[LoggingConfig, LoggingConfigUpdateError]:
        """Convenience: enable/disable console output at runtime."""
        return self.update_config(CONSOLE_OUTPUT=enabled)
