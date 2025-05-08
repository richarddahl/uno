from typing import Protocol, runtime_checkable

import pytest

from uno.infrastructure.di.container import Container


# Define test protocols and implementations
@runtime_checkable
class IService(Protocol):
    def get_data(self) -> str: ...


@runtime_checkable
class IDataAccess(Protocol):
    def fetch(self) -> str: ...


class DataAccess:
    def __init__(self) -> None:
        self.data = "test_data"

    def fetch(self) -> str:
        return self.data


class Service:
    def __init__(self, data_access: IDataAccess) -> None:
        self.data_access = data_access

    def get_data(self) -> str:
        return self.data_access.fetch()


@pytest.mark.asyncio
async def test_complex_dependency_chain() -> None:
    container = Container()

    # Define a chain of dependencies
    await container.register_singleton(IDataAccess, DataAccess)

    # Register with a factory that resolves dependencies
    async def create_service(container: Container) -> IService:
        data_access = await container.resolve(IDataAccess)
        return Service(data_access)

    await container.register_singleton(IService, create_service)

    # Resolve the service
    service = await container.resolve(IService)

    # Verify the dependency chain works
    assert service.get_data() == "test_data"
