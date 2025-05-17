"""Unit of Work pattern implementation for managing transactions and atomic operations.

This module provides the infrastructure for managing units of work in a domain-driven design,
ensuring atomic operations across multiple aggregates and repositories.
"""

from typing import TypeVar, Generic, Type, Any

from .protocols import UnitOfWorkProtocol, UnitOfWorkManagerProtocol
from .unit_of_work import UnitOfWork, Savepoint, get_current_uow
from .redis_unit_of_work import RedisUnitOfWork, RedisRepository
from .errors import (
    UnitOfWorkError,
    ConcurrencyError,
    RepositoryError,
    TransactionError,
)

# Re-export types for easier imports
UnitOfWork = UnitOfWork
Savepoint = Savepoint
RedisUnitOfWork = RedisUnitOfWork
RedisRepository = RedisRepository

# Type variables for generic parameters
E = TypeVar("E")  # Event type
A = TypeVar("A")  # Aggregate type
S = TypeVar("S")  # Snapshot type

__all__ = [
    # Protocols and Base Classes
    "UnitOfWorkProtocol",
    "UnitOfWorkManager",
    "RepositoryFactory",
    "UnitOfWork",
    "Savepoint",
    "get_current_uow",
    # Redis Implementations
    "RedisUnitOfWork",
    "RedisRepository",
    # Exceptions
    "UnitOfWorkError",
    "ConcurrencyError",
    "OptimisticConcurrencyError",
    "RepositoryError",
    "TransactionError",
    # Type Variables
    "E",
    "A",
    "S",
]
