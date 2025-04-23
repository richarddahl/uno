# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Queries for the TodoList bounded context.
"""

from dataclasses import dataclass

from uno.core.application.queries import Query
from uno.examples.todolist.domain.models import TodoPriority, TodoStatus


@dataclass
class GetTodoItemQuery(Query):
    """Query to get a specific todo item."""

    todo_id: str


@dataclass
class ListTodoItemsQuery(Query):
    """Query to list todo items with optional filtering."""

    status: TodoStatus | None = None
    priority: TodoPriority | None = None
