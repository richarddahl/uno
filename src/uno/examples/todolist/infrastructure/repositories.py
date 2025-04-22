# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Repository implementations for the TodoList bounded context.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from uno.database.repositories import SQLAlchemyRepository
from uno.examples.todolist.domain.models import TodoItem
from uno.examples.todolist.infrastructure.database import TodoItemModel


class TodoItemRepository(SQLAlchemyRepository[TodoItem, str]):
    """Repository for TodoItem aggregates."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, TodoItem, TodoItemModel)

    async def find_by_status(self, status) -> list[TodoItem]:
        """Find todo items by status."""
        stmt = select(self.db_model_class).where(self.db_model_class.status == status)
        result = await self.session.execute(stmt)
        db_entities = result.scalars().all()
        return [self._to_domain_entity(e) for e in db_entities]

    async def find_by_priority(self, priority) -> list[TodoItem]:
        """Find todo items by priority."""
        stmt = select(self.db_model_class).where(
            self.db_model_class.priority == priority
        )
        result = await self.session.execute(stmt)
        db_entities = result.scalars().all()
        return [self._to_domain_entity(e) for e in db_entities]
