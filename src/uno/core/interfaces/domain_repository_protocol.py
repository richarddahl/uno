"""
DomainRepositoryProtocol: Protocol for async domain repositories.
"""
from typing import Protocol, TypeVar, Generic, Any

EntityT = TypeVar("EntityT")

class DomainRepositoryProtocol(Protocol, Generic[EntityT]):
    async def get(self, id: str) -> EntityT | None:
        ...
    async def list(
        self,
        filters: dict[str, Any] | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[EntityT]:
        ...
    async def add(self, entity: EntityT) -> EntityT:
        ...
    async def update(self, entity: EntityT) -> EntityT:
        ...
    async def remove(self, entity: EntityT) -> None:
        ...
    async def remove_by_id(self, id: str) -> bool:
        ...
    async def exists(self, id: str) -> bool:
        ...
    async def count(self, filters: dict[str, Any] | None = None) -> int:
        ...
