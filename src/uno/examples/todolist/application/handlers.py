"""
Command and query handlers for the TodoList bounded context.
"""

from typing import List, Optional

from uno.core.application.commands import CommandHandler
from uno.core.application.queries import QueryHandler
from uno.examples.todolist.domain.models import TodoItem
from uno.examples.todolist.infrastructure.repositories import TodoItemRepository
from uno.examples.todolist.application.commands import (
    CreateTodoItemCommand,
    CompleteTodoItemCommand,
    CancelTodoItemCommand,
)
from uno.examples.todolist.application.queries import (
    GetTodoItemQuery,
    ListTodoItemsQuery,
)

from uno.core.errors.result import Success, Failure


class CreateTodoItemHandler(CommandHandler[CreateTodoItemCommand, TodoItem]):
    """Handler for creating new todo items."""

    def __init__(self, repository: TodoItemRepository):
        self.repository = repository

    async def handle(self, command: CreateTodoItemCommand) -> TodoItem:
        """Handle the create todo item command."""
        # Create domain entity
        todo_item = TodoItem.create(
            title=command.title,
            description=command.description,
            priority=command.priority,
            due_date=command.due_date,
        )

        # Persist and return
        return await self.repository.save(todo_item)


class CompleteTodoItemHandler(CommandHandler[CompleteTodoItemCommand, TodoItem]):
    """Handler for completing todo items."""

    def __init__(self, repository: TodoItemRepository):
        self.repository = repository

    async def handle(self, command: CompleteTodoItemCommand) -> "Success[TodoItem] | Failure[ValueError]":
        """Handle the complete todo item command.
        Returns Success(TodoItem) if completed, or Failure(ValueError) if not found.
        """
        todo_item = await self.repository.get_by_id(command.todo_id)
        if not todo_item:
            return Failure(ValueError(f"Todo item {command.todo_id} not found"))
        todo_item.complete()
        return Success(await self.repository.save(todo_item))


class CancelTodoItemHandler(CommandHandler[CancelTodoItemCommand, TodoItem]):
    """Handler for cancelling todo items."""

    def __init__(self, repository: TodoItemRepository):
        self.repository = repository

    async def handle(self, command: CancelTodoItemCommand) -> "Success[TodoItem] | Failure[ValueError]":
        """Handle the cancel todo item command.
        Returns Success(TodoItem) if cancelled, or Failure(ValueError) if not found.
        """
        todo_item = await self.repository.get_by_id(command.todo_id)
        if not todo_item:
            return Failure(ValueError(f"Todo item {command.todo_id} not found"))
        todo_item.cancel(command.reason)
        return Success(await self.repository.save(todo_item))


class GetTodoItemHandler(QueryHandler[GetTodoItemQuery, Optional[TodoItem]]):
    """Handler for retrieving a specific todo item."""

    def __init__(self, repository: TodoItemRepository):
        self.repository = repository

    async def handle(self, query: GetTodoItemQuery) -> Optional[TodoItem]:
        """Handle the get todo item query."""
        return await self.repository.get_by_id(query.todo_id)


class ListTodoItemsHandler(QueryHandler[ListTodoItemsQuery, list[TodoItem]]):
    """Handler for listing todo items."""

    def __init__(self, repository: TodoItemRepository):
        self.repository = repository

    async def handle(self, query: ListTodoItemsQuery) -> list[TodoItem]:
        """Handle the list todo items query."""
        # Apply filters if provided
        if query.status is not None and query.priority is not None:
            # Need to filter by both status and priority
            # This would be better with a more flexible repository method
            todos_by_status = await self.repository.find_by_status(query.status)
            return [t for t in todos_by_status if t.priority == query.priority]
        elif query.status is not None:
            return await self.repository.find_by_status(query.status)
        elif query.priority is not None:
            return await self.repository.find_by_priority(query.priority)
        else:
            # No filters, return all
            return await self.repository.list()
