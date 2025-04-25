# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
TodoList domain model - example implementation using the Uno DDD framework.
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import Field

from uno.core.domain.core import AggregateRoot, DomainEvent


class TodoPriority(Enum):
    """Priority levels for todo items."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TodoStatus(Enum):
    """Status values for todo items."""

    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


from uno.core.events.events import DomainEvent


class TodoItemCreatedEvent(DomainEvent):
    """Event raised when a new todo item is created."""

    todo_id: str
    title: str


class TodoItemCompletedEvent(DomainEvent):
    """Event raised when a todo item is marked as completed."""

    todo_id: str
    completed_at: datetime


class TodoItemCancelledEvent(DomainEvent):
    """Event raised when a todo item is cancelled."""

    todo_id: str
    reason: str | None = None


class TodoItem(AggregateRoot[str]):
    """A todo item in the system."""

    title: str
    description: str | None = None
    status: TodoStatus = Field(default=TodoStatus.PENDING)
    priority: TodoPriority = Field(default=TodoPriority.MEDIUM)
    due_date: datetime | None = None
    completed_at: datetime | None = None

    @classmethod
    def create(
        cls,
        title: str,
        description: str | None = None,
        priority: TodoPriority = TodoPriority.MEDIUM,
        due_date: datetime | None = None,
    ) -> "TodoItem":
        """Create a new todo item."""
        todo = cls(
            title=title, description=description, priority=priority, due_date=due_date
        )

        # Add created event
        todo.add_event(TodoItemCreatedEvent(todo_id=todo.id, title=todo.title))

        return todo

    def complete(self) -> None:
        """Mark the todo item as completed."""
        if self.status == TodoStatus.COMPLETED:
            return  # Already completed

        self.status = TodoStatus.COMPLETED
        self.completed_at = datetime.now(UTC)

        # Add completed event
        self.add_event(
            TodoItemCompletedEvent(todo_id=self.id, completed_at=self.completed_at)
        )

    def cancel(self, reason: str | None = None) -> None:
        """Cancel the todo item."""
        if self.status != TodoStatus.PENDING:
            return  # Can only cancel pending items

        self.status = TodoStatus.CANCELLED

        # Add cancelled event
        self.add_event(TodoItemCancelledEvent(todo_id=self.id, reason=reason))
