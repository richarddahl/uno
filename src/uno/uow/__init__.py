"""Unit of Work pattern implementation for managing transactions and atomic operations.

This module provides the infrastructure for managing units of work in a domain-driven design,
ensuring atomic operations across multiple aggregates and repositories.
"""

from typing import TypeVar, Any

from uno.uow.protocols import UnitOfWorkProtocol
from uno.uow.unit_of_work import UnitOfWork, Savepoint, get_current_uow
from uno.uow.memory import InMemoryUnitOfWork
from .errors import (
    UnitOfWorkError,
    ConcurrencyError,
    RepositoryError,
    TransactionError,
)

# Re-export types for easier imports
UnitOfWork = UnitOfWork
Savepoint = Savepoint

# Type variables for generic parameters
E = TypeVar("E")  # Event type
A = TypeVar("A")  # Aggregate type
S = TypeVar("S")  # Snapshot type

def create_in_memory_uow(
    container: ContainerProtocol,
    **kwargs: Any,
) -> UnitOfWorkProtocol[A]:
    """Create a new in-memory Unit of Work instance.
    
    Args:
        container: The dependency injection container
        **kwargs: Additional keyword arguments
        
    Returns:
        A new InMemoryUnitOfWork instance
    """
    return InMemoryUnitOfWork.create(container, **kwargs)

__all__ = [
    # Protocols and Base Classes
    "UnitOfWorkProtocol",
    "UnitOfWorkManager",
    "RepositoryFactory",
    "UnitOfWork",
    "Savepoint",
    "get_current_uow",
    "InMemoryUnitOfWork",
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
