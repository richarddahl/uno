from __future__ import annotations

"""
Centralized logger abstraction for Uno framework.

Wraps Python's standard logging, loads config from uno.core.config, and exposes a DI-friendly logger.
"""

import contextvars
import logging
import os
import sys
import uuid

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

from uno.core.config.base import (
    DevSettingsConfigDict,
    ProdSettingsConfigDict,
    TestSettingsConfigDict,
)

# Type alias for logger
Logger = logging.Logger



class LoggingConfig(BaseSettings):
    LEVEL: str = "INFO"
    FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    JSON_FORMAT: bool = False
    CONSOLE_OUTPUT: bool = True
    FILE_OUTPUT: bool = False
    FILE_PATH: str | None = None
    BACKUP_COUNT: int = 5
    MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
    PROPAGATE: bool = False
    INCLUDE_LOGGER_CONTEXT: bool = True
    INCLUDE_EXCEPTION_TRACEBACK: bool = True

    model_config = ConfigDict(env_prefix="UNO_LOG_")


class Prod(LoggingConfig):
    model_config = ProdSettingsConfigDict


class Dev(LoggingConfig):
    model_config = DevSettingsConfigDict


class Test(LoggingConfig):
    model_config = TestSettingsConfigDict


# DI-managed LoggerService implementation
# NOTE: Local import to break circular dependency
class LoggerService:
    """
    Dependency-injected singleton logging service for Uno.
    Handles logger configuration, lifecycle, and DI-friendly logger retrieval.
    Provides robust trace/correlation/request ID propagation for observability.
    
    Usage:
        logger = LoggerService(LoggingConfig())
        await logger.initialize()
        logger.info("Hello, Uno!")
    """
    def __init__(self, config: LoggingConfig):
        self.config = config
        self._logger: Logger | None = None
        self._initialized = False
        self._trace_id: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default=str(uuid.uuid4()))

    async def initialize(self) -> None:
        """
        Initialize the logger with the current config.
        Safe to call multiple times (idempotent).
        """
        if self._initialized:
            return
        self._logger = self._create_logger()
        self._initialized = True

    def _create_logger(self) -> Logger:
        logger = logging.getLogger("uno")
        logger.setLevel(self.config.LEVEL)
        formatter = logging.Formatter(self.config.FORMAT, self.config.DATE_FORMAT)
        if self.config.CONSOLE_OUTPUT:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        if self.config.FILE_OUTPUT and self.config.FILE_PATH:
            from logging.handlers import RotatingFileHandler
            handler = RotatingFileHandler(
                self.config.FILE_PATH,
                maxBytes=self.config.MAX_BYTES,
                backupCount=self.config.BACKUP_COUNT,
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.propagate = self.config.PROPAGATE
        return logger

    def get_logger(self) -> Logger:
        """
        Get the underlying Python logger instance.
        """
        if not self._initialized or self._logger is None:
            raise RuntimeError("LoggerService not initialized. Call 'await initialize()' first.")
        return self._logger

    def set_trace_id(self, trace_id: str) -> None:
        """
        Set the trace/correlation ID for the current context.
        """
        self._trace_id.set(trace_id)

    def get_trace_id(self) -> str:
        """
        Get the trace/correlation ID for the current context.
        """
        return self._trace_id.get()

    def info(self, msg: str, *args, **kwargs) -> None:
        self.get_logger().info(self._format(msg), *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs) -> None:
        self.get_logger().debug(self._format(msg), *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self.get_logger().warning(self._format(msg), *args, **kwargs)

    def error(self, msg: str, *args, exc_info: bool = True, **kwargs) -> None:
        self.get_logger().error(self._format(msg), *args, exc_info=exc_info, **kwargs)

    def _format(self, msg: str) -> str:
        # Optionally add trace ID or other context
        if self.config.INCLUDE_LOGGER_CONTEXT:
            return f"[trace_id={self.get_trace_id()}] {msg}"
        return msg


    def __init__(self, config: LoggingConfig) -> None:
        """
        LoggerService uses composition for lifecycle management. Requires a LoggingConfig instance.
        If ServiceLifecycle methods are needed, assign a ServiceLifecycle-compatible object to self._lifecycle.
        """
        self._lifecycle = None  # type: ignore
        self._config: LoggingConfig = config
        self._initialized: bool = False
        self._loggers: dict[str, Logger] = {}

    def debug(self, msg: str, *args, name: str | None = None, **kwargs) -> None:
        """Log a debug message via the Uno logger."""
        self.get_logger(name).debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, name: str | None = None, **kwargs) -> None:
        """Log an info message via the Uno logger."""
        self.get_logger(name).info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, name: str | None = None, **kwargs) -> None:
        """Log a warning message via the Uno logger."""
        self.get_logger(name).warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, name: str | None = None, **kwargs) -> None:
        """Log an error message via the Uno logger."""
        self.get_logger(name).error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, name: str | None = None, **kwargs) -> None:
        """Log a critical message via the Uno logger."""
        self.get_logger(name).critical(msg, *args, **kwargs)

    """
    Dependency-injected singleton logging service for Uno.
    Handles logger configuration, lifecycle, and DI-friendly logger retrieval.
    Provides robust trace/correlation/request ID propagation for observability.
    """

    # Context variable for trace context (correlation/request/trace IDs)
    _trace_context_var: contextvars.ContextVar[dict[str, str]] = contextvars.ContextVar("uno_trace_context", default={})


    def _load_config(self) -> LoggingConfig:
        env_settings: dict[str, type[LoggingConfig]] = {
            "dev": Dev,
            "test": Test,
            "prod": Prod,
        }
        env = os.environ.get("ENV", "dev").lower()
        return env_settings.get(env, Dev)()

    async def initialize(self) -> None:
        if self._initialized:
            return
        self._configure_root_logger()
        self._initialized = True

    async def dispose(self) -> None:
        # Optionally flush/close handlers or perform cleanup
        self._loggers.clear()
        self._initialized = False

    def get_logger(self, name: str | None = None) -> Logger:
        """
        Returns a logger with the given name, supporting structured logging via the standard logging 'extra' argument.
        Ensures logger is always initialized (robust singleton).
        """
        if not self._initialized:
            self._configure_root_logger()
            self._initialized = True
        logger_name = name or "uno"
        if logger_name not in self._loggers:
            self._loggers[logger_name] = logging.getLogger(logger_name)
        return self._loggers[logger_name]

    def get_child_logger(self, parent_name: str, child: str) -> Logger:
        """
        Returns a child logger with a dotted name (e.g., 'parent.child').
        """
        full_name = f"{parent_name}.{child}"
        return self.get_logger(full_name)

    def with_context(self, name: str | None = None, trace_context: dict[str, str] | None = None, **context: object) -> Logger:
        """
        Returns a logger that always injects the given context into log records.
        If trace_context is not provided, uses the current trace context from contextvars (if any).
        Usage:
            logger = logger_service.with_context("my.module", user_id=123)
            logger.info("Something happened")
            # With trace context:
            logger = logger_service.with_context(trace_context={"correlation_id": "abc-123"}, user_id=123)
        """
        base_logger = self.get_logger(name)
        # Merge trace_context from contextvars if not provided
        merged_context = dict(context)
        if trace_context is None:
            trace_context = self._trace_context_var.get({})
        if trace_context:
            merged_context.update(trace_context)
        class ContextLogger(logging.LoggerAdapter):
            def __init__(self, logger, extra):
                super().__init__(logger, extra)
            def process(self, msg, kwargs):
                extra = kwargs.get("extra", {})
                context = dict(self.extra)
                context.update(extra.get("context", {}))
                extra["context"] = context
                kwargs["extra"] = extra
                return msg, kwargs
        return ContextLogger(base_logger, merged_context)

    def structured_log(
        self,
        level: str,
        msg: str,
        name: str | None = None,
        *,
        error_context: dict[str, object] | None = None,
        trace_context: dict[str, object] | None = None,
        exc_info: Exception | tuple | None = None,
        **context: object,
    ) -> None:
        """
        Log a message at the given level with structured/context fields, error context, and trace context.
        Always injects error context (exception info, error codes, stack traces, etc.) and trace/correlation IDs into log records.
        If trace_context is not provided, uses the current trace context from contextvars (if any).
        Example:
            logger_service.structured_log(
                'error',
                'Failed to process request',
                user_id=123,
                error_context={'error_code': 'E123', 'details': 'Validation failed'},
                trace_context={'correlation_id': 'abc-123', 'trace_id': 'xyz-789'},
                exc_info=exception,
            )
        """
        logger = self.get_logger(name)
        log_method = getattr(logger, level.lower(), None)
        if not callable(log_method):
            raise ValueError(f"Invalid log level: {level}")
        merged_context = dict(context)
        # Always inject error_context and trace_context
        if error_context:
            merged_context.update(error_context)
        # Use explicit trace_context if provided, else from contextvars
        if trace_context is None:
            trace_context = self._trace_context_var.get({})
        if trace_context:
            merged_context.update(trace_context)
        # If exc_info is present, add structured exception info
        if exc_info:
            import traceback
            if isinstance(exc_info, BaseException):
                exc_type = type(exc_info).__name__
                exc_message = str(exc_info)
                tb = ''.join(traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__))
            elif isinstance(exc_info, tuple):
                exc_type = str(exc_info[0].__name__)
                exc_message = str(exc_info[1])
                tb = ''.join(traceback.format_exception(*exc_info))
            else:
                # exc_info=True: use sys.exc_info()
                import sys
                ei = sys.exc_info()
                exc_type = str(ei[0].__name__) if ei[0] else None
                exc_message = str(ei[1]) if ei[1] else None
                tb = ''.join(traceback.format_exception(*ei)) if ei[0] else None
            merged_context["exception_type"] = exc_type
            merged_context["exception_message"] = exc_message
            merged_context["exception_traceback"] = tb
        log_method(msg, extra={"context": merged_context if merged_context else None}, exc_info=exc_info)

    def _get_formatter(self) -> logging.Formatter:
        """
        Returns a formatter: JSON if config.JSON_FORMAT is True, otherwise standard formatter.
        JSON: error/trace context fields are flattened at the top level.
        Standard: error/trace context fields appended to the log message if present.
        """
        cfg = self._config
        if cfg.JSON_FORMAT:
            import json
            class JsonFormatter(logging.Formatter):
                def format(self, record: logging.LogRecord) -> str:
                    base = {
                        "timestamp": self.formatTime(record, cfg.DATE_FORMAT),
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                    }
                    # Merge context fields if present
                    if hasattr(record, "context") and isinstance(record.context, dict):
                        base.update(record.context)
                    # Remove None values for cleaner output
                    base = {k: v for k, v in base.items() if v is not None}
                    return json.dumps(base, default=str)
            return JsonFormatter()
        else:
            class StandardFormatter(logging.Formatter):
                def format(self, record: logging.LogRecord) -> str:
                    msg = super().format(record)
                    # If context has error/trace info, append as suffix
                    if hasattr(record, "context") and isinstance(record.context, dict):
                        context = record.context
                        extras = []
                        for key in ("error_code", "exception_type", "exception_message", "correlation_id", "trace_id", "request_id"):
                            if context.get(key):
                                extras.append(f"{key}={context[key]}")
                        if extras:
                            msg = f"{msg} | {' '.join(extras)}"
                    return msg
            return StandardFormatter(fmt=cfg.FORMAT, datefmt=cfg.DATE_FORMAT)

    def reload_config(self) -> None:
        """
        Re-apply the current logging config to all loggers and handlers at runtime.
        Updates log level, handlers, and formatters for all managed loggers.
        Call after updating config for dynamic, no-restart changes.
        """
        self._configure_root_logger()
        cfg = self._config
        formatter = self._get_formatter()
        level = getattr(logging, cfg.LEVEL.upper(), logging.INFO)
        for name, logger in self._loggers.items():
            logger.setLevel(level)
            # Remove all handlers robustly (including inherited ones)
            while logger.handlers:
                logger.removeHandler(logger.handlers[0])
            # Prevent duplicate handlers by checking existing ones
            handler_ids = set()
            if cfg.CONSOLE_OUTPUT:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
                if id(console_handler) not in handler_ids:
                    logger.addHandler(console_handler)
                    handler_ids.add(id(console_handler))
            if cfg.FILE_OUTPUT and cfg.FILE_PATH:
                file_handler = logging.handlers.RotatingFileHandler(
                    cfg.FILE_PATH,
                    maxBytes=cfg.MAX_BYTES,
                    backupCount=cfg.BACKUP_COUNT,
                )
                file_handler.setFormatter(formatter)
                if id(file_handler) not in handler_ids:
                    logger.addHandler(file_handler)
                    handler_ids.add(id(file_handler))
            logger.propagate = cfg.PROPAGATE
        # For test isolation: clear loggers if not initialized
        if not self._initialized:
            self._loggers.clear()

    def new_trace_context(self) -> dict[str, str]:
        """
        Generate a new trace context with a unique correlation_id (UUID4).
        Returns: {"correlation_id": ...}
        """
        return {"correlation_id": str(uuid.uuid4())}

    class trace_scope:
        """
        Context manager to set a trace context (correlation/request/trace ID) for the duration of a code block.
        If no correlation_id is provided, a new one is generated.
        Usage:
            with logger_service.trace_scope():
                logger_service.structured_log(...)
        """
        def __init__(self, logger_service: LoggerService, correlation_id: str | None = None, trace_context: dict[str, str] | None = None):
            self._logger_service = logger_service
            if trace_context is not None:
                self._trace_context = dict(trace_context)
            else:
                self._trace_context = {"correlation_id": correlation_id or str(uuid.uuid4())}
            self._token = None
        def __enter__(self):
            self._token = self._logger_service._trace_context_var.set(self._trace_context)
            return self._trace_context
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self._token is not None:
                self._logger_service._trace_context_var.reset(self._token)

    def _configure_root_logger(self) -> None:
        cfg = self._config
        level = getattr(logging, cfg.LEVEL.upper(), logging.INFO)
        handlers = []
        formatter = self._get_formatter()
        # Clear all handlers from root logger to allow reconfiguration (important for tests!)
        root_logger = logging.getLogger()
        for h in list(root_logger.handlers):
            root_logger.removeHandler(h)
        if cfg.CONSOLE_OUTPUT:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            handlers.append(console_handler)
        if cfg.FILE_OUTPUT and cfg.FILE_PATH:
            file_handler = logging.handlers.RotatingFileHandler(
                cfg.FILE_PATH,
                maxBytes=cfg.MAX_BYTES,
                backupCount=cfg.BACKUP_COUNT,
            )
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        logging.basicConfig(
            level=level,
            handlers=handlers if handlers else None,
            format=cfg.FORMAT,
            datefmt=cfg.DATE_FORMAT,
        )


