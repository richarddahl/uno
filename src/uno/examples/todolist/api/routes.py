# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
API routes for the TodoList bounded context.
"""

from fastapi import APIRouter, HTTPException

from uno.core.application.commands import CommandBus
from uno.core.application.queries import QueryBus
from uno.core.errors.result import Failure
from uno.examples.todolist.api.schemas import (
    CreateTodoRequest,
    TodoItemResponse,
)
from uno.examples.todolist.application.commands import (
    CancelTodoItemCommand,
    CompleteTodoItemCommand,
    CreateTodoItemCommand,
)
from uno.examples.todolist.application.queries import (
    GetTodoItemQuery,
    ListTodoItemsQuery,
)
from uno.examples.todolist.domain.models import TodoPriority, TodoStatus

router = APIRouter(prefix="/todos", tags=["todos"])


@router.post("/", response_model=TodoItemResponse)
async def create_todo(request: CreateTodoRequest):
    """Create a new todo item."""
    command = CreateTodoItemCommand(
        title=request.title,
        description=request.description,
        priority=request.priority,
        due_date=request.due_date,
    )
    result = await CommandBus.dispatch(command)
    if isinstance(result, Failure):
        raise HTTPException(status_code=400, detail=str(result.error))
    return result.value


@router.get("/{todo_id}", response_model=TodoItemResponse)
async def get_todo(todo_id: str):
    """Get a specific todo item."""
    query = GetTodoItemQuery(todo_id=todo_id)
    result = await QueryBus.dispatch(query)
    if isinstance(result, Failure):
        raise HTTPException(status_code=404, detail=str(result.error))
    if result.value is None:
        raise HTTPException(status_code=404, detail="Todo item not found")
    return result.value


@router.get("/", response_model=list[TodoItemResponse])
async def list_todos(
    status: TodoStatus | None = None, priority: TodoPriority | None = None
):
    """List todo items with optional filtering."""
    query = ListTodoItemsQuery(status=status, priority=priority)
    result = await QueryBus.dispatch(query)
    if isinstance(result, Failure):
        raise HTTPException(status_code=400, detail=str(result.error))
    return result.value


@router.put("/{todo_id}/complete")
async def complete_todo(todo_id: str):
    """Mark a todo item as completed."""
    command = CompleteTodoItemCommand(todo_id=todo_id)
    result = await CommandBus.dispatch(command)
    if isinstance(result, Failure):
        raise HTTPException(status_code=404, detail=str(result.error))
    return result.value


@router.put("/{todo_id}/cancel")
async def cancel_todo(todo_id: str, reason: str | None = None):
    """Cancel a todo item."""
    command = CancelTodoItemCommand(todo_id=todo_id, reason=reason)
    result = await CommandBus.dispatch(command)
    if isinstance(result, Failure):
        raise HTTPException(status_code=404, detail=str(result.error))
    return result.value
