"""
SQLEmitterFactoryProtocol: Protocol for SQL emitter factory implementations.
"""

from typing import Protocol, Any


class SQLEmitterFactoryProtocol(Protocol):
    def create(self, emitter_type: str, **kwargs: Any) -> Any: ...
