# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
API schemas for the TodoList bounded context.
"""

from datetime import datetime

from pydantic import BaseModel

from uno.examples.todolist.domain.models import TodoPriority, TodoStatus


class CreateTodoRequest(BaseModel):
    """Schema for creating a new todo item."""

    title: str
    description: str | None = None
    priority: TodoPriority = TodoPriority.MEDIUM
    due_date: datetime | None = None


class UpdateTodoRequest(BaseModel):
    """Schema for updating an existing todo item."""

    title: str | None = None
    description: str | None = None
    priority: TodoPriority | None = None
    due_date: datetime | None = None


class TodoItemResponse(BaseModel):
    """Schema for todo item responses."""

    id: str
    title: str
    description: str | None = None
    status: TodoStatus
    priority: TodoPriority
    due_date: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
