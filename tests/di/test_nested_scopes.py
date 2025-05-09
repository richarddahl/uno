from typing import Protocol, runtime_checkable

import pytest

from uno.di.container import Container
from uno.di.errors import ScopeError


# Define test protocols and implementations
@runtime_checkable
class IRepository(Protocol):
    def get_by_id(self, id: int) -> dict: ...


class MemoryRepository:
    def get_by_id(self, id: int) -> dict:
        return {"id": id}


@pytest.mark.asyncio
async def test_create_nested_scope() -> None:
    container = Container()
    await container.register_scoped(IRepository, MemoryRepository)

    # Create a scope
    async with container.create_scope() as parent_scope:
        repo = await parent_scope.resolve(IRepository)

        # Create a nested scope
        async with parent_scope.create_scope() as nested_scope:
            nested_repo = await nested_scope.resolve(IRepository)

        # Verify different instances in nested scope
        assert repo is not nested_repo

    # Verify parent scope is disposed
    with pytest.raises(ScopeError):
        await parent_scope.resolve(IRepository)
