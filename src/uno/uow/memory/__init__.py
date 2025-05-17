"""In-memory Unit of Work implementation for testing and development."""

from typing import Any, TypeVar

from uno.injection import ContainerProtocol
from uno.uow.memory import InMemoryUnitOfWork
from uno.uow.protocols import UnitOfWorkProtocol

A = TypeVar("A", bound="AggregateRoot[Any]")

__all__ = ["InMemoryUnitOfWork"]

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
