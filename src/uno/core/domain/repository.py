from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """Port for repository implementations."""

    @abstractmethod
    async def get_by_id(self, id: str) -> T | None: ...

    @abstractmethod
    async def list(self) -> list[T]: ...

    @abstractmethod
    async def add(self, entity: T) -> None: ...

    @abstractmethod
    async def remove(self, id: str) -> None: ...
