# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework# core_library/logging/interfaces.py

import logging
from typing import Any


class TextLogger:
    """Standard logger implementation"""

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def debug(self, message: str, **kwargs: Any) -> None:
        self._logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self._logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        self._logger.critical(message, extra=kwargs)


class TextLoggerFactory:
    """Factory for creating TextLogger instances"""

    def __init__(self, root_logger_name: str = "uno"):
        self.root_logger_name = root_logger_name

        # Setup root logger with NullHandler
        self.root_logger = logging.getLogger(root_logger_name)
        self.root_logger.addHandler(logging.NullHandler())

    def create_logger(self, component_name: str) -> TextLogger:
        """Create a component-specific logger"""
        logger_name = f"{self.root_logger_name}.{component_name}"
        return TextLogger(logging.getLogger(logger_name))

    def configure(
        self,
        level: int = logging.INFO,
        handlers: list[logging.Handler] | None = None,
        propagate: bool = True,
    ) -> None:
        """Configure the root logger"""
        self.root_logger.setLevel(level)

        # Remove existing handlers
        for handler in list(self.root_logger.handlers):
            if not isinstance(handler, logging.NullHandler):
                self.root_logger.removeHandler(handler)

        # Add new handlers
        if handlers:
            for handler in handlers:
                self.root_logger.addHandler(handler)

        self.root_logger.propagate = propagate
