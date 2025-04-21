"""
Commands for the TodoList bounded context.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from uno.core.application.commands import Command
from uno.examples.todolist.domain.models import TodoPriority


@dataclass
class CreateTodoItemCommand(Command):
    """Command to create a new todo item."""

    title: str
    description: str | None = None
    priority: TodoPriority = TodoPriority.MEDIUM
    due_date: Optional[datetime] = None


@dataclass
class CompleteTodoItemCommand(Command):
    """Command to mark a todo item as completed."""

    todo_id: str


@dataclass
class CancelTodoItemCommand(Command):
    """Command to cancel a todo item."""

    todo_id: str
    reason: str | None = None
