"""
API schemas for the TodoList bounded context.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from uno.examples.todolist.domain.models import TodoStatus, TodoPriority


class CreateTodoRequest(BaseModel):
    """Schema for creating a new todo item."""

    title: str
    description: str | None = None
    priority: TodoPriority = TodoPriority.MEDIUM
    due_date: Optional[datetime] = None


class UpdateTodoRequest(BaseModel):
    """Schema for updating an existing todo item."""

    title: str | None = None
    description: str | None = None
    priority: Optional[TodoPriority] = None
    due_date: Optional[datetime] = None


class TodoItemResponse(BaseModel):
    """Schema for todo item responses."""

    id: str
    title: str
    description: str | None = None
    status: TodoStatus
    priority: TodoPriority
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
