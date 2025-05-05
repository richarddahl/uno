"""
LoggerProtocol: Abstract base class for logging services.
Extend this protocol for any logger to be injected into core/infrastructure.
"""

from typing import Protocol


class LoggerProtocol(Protocol):
    """Protocol for logger services."""

    def info(self, msg: str, *args, **kwargs) -> None: ...
    def warning(self, msg: str, *args, **kwargs) -> None: ...
    def error(self, msg: str, *args, **kwargs) -> None: ...
    def debug(self, msg: str, *args, **kwargs) -> None: ...
