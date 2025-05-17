# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno

"""PostgreSQL Unit of Work implementations."""

from typing import Any, TypeVar

from uno.injection import ContainerProtocol
from uno.persistence.uow.postgres import PostgresUnitOfWork
from uno.uow.protocols import UnitOfWorkProtocol

A = TypeVar("A", bound="AggregateRoot[Any]")

__all__ = ["PostgresUnitOfWork", "create_postgres_uow"]


async def create_postgres_uow(
    container: ContainerProtocol,
    **kwargs: Any,
) -> UnitOfWorkProtocol[A]:
    """Create a new PostgreSQL Unit of Work instance.
    
    Args:
        container: The dependency injection container
        **kwargs: Additional keyword arguments
        
    Returns:
        A new PostgresUnitOfWork instance
    """
    return await PostgresUnitOfWork.create(container, **kwargs)
