"""
UnitOfWorkProtocol: Abstract base class for unit of work pattern.
Extend this protocol for transactional boundaries in services.
"""

from typing import Protocol


class UnitOfWorkProtocol(Protocol):
    """Protocol for unit of work implementations."""

    def __enter__(self) -> "UnitOfWorkProtocol": ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
