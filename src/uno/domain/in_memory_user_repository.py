from uno.core.domain.repository import Repository
from uno.domain.user import User


class InMemoryUserRepository(Repository[User]):
    def __init__(self):
        self._store: dict[str, User] = {}

    async def get_by_id(self, id: str) -> User | None:
        return self._store.get(id)

    async def list(self) -> list[User]:
        return list(self._store.values())

    async def add(self, entity: User) -> None:
        self._store[entity.id] = entity

    async def remove(self, id: str) -> None:
        if id in self._store:
            del self._store[id]
