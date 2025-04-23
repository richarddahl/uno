# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework

from uno.application.event_bus import IEventBus
from uno.domain.repository import Repository
from uno.domain.user import User


class UserService:
    """Application service for managing users."""
    def __init__(self, repo: Repository[User], event_bus: IEventBus):
        self._repo = repo
        self._event_bus = event_bus

    async def create_user(self, username: str, email: str) -> User:
        user = User(username=username, email=email)
        await self._repo.add(user)
        events = user.clear_events()
        for event in events:
            self._event_bus.publish(event)
        return user

    async def get_user(self, user_id: str) -> User | None:
        return await self._repo.get_by_id(user_id)
