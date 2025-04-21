"""
TodoList bounded context initialization.
"""

from uno.core.application.commands import CommandBus
from uno.core.application.queries import QueryBus
from uno.core.domain.core import DomainEventDispatcher
from uno.database.session import get_async_session

from uno.examples.todolist.application.commands import (
    CreateTodoItemCommand,
    CompleteTodoItemCommand,
    CancelTodoItemCommand,
)
from uno.examples.todolist.application.queries import (
    GetTodoItemQuery,
    ListTodoItemsQuery,
)
from uno.examples.todolist.application.handlers import (
    CreateTodoItemHandler,
    CompleteTodoItemHandler,
    CancelTodoItemHandler,
    GetTodoItemHandler,
    ListTodoItemsHandler,
)
from uno.examples.todolist.application.middleware import (
    logging_middleware,
    validation_middleware,
)
from uno.examples.todolist.application.event_handlers import (
    handle_todo_created,
    handle_todo_completed,
    handle_todo_cancelled,
)
from uno.examples.todolist.domain.models import (
    TodoItemCreatedEvent,
    TodoItemCompletedEvent,
    TodoItemCancelledEvent,
)
from uno.examples.todolist.infrastructure.repositories import TodoItemRepository


async def register_handlers():
    """Register all command, query, and event handlers."""
    # Get a session
    session = await get_async_session()

    # Create repositories
    todo_repo = TodoItemRepository(session)

    # Register command handlers
    CommandBus.register_handler(CreateTodoItemCommand, CreateTodoItemHandler(todo_repo))
    CommandBus.register_handler(
        CompleteTodoItemCommand, CompleteTodoItemHandler(todo_repo)
    )
    CommandBus.register_handler(CancelTodoItemCommand, CancelTodoItemHandler(todo_repo))

    # Register query handlers
    QueryBus.register_handler(GetTodoItemQuery, GetTodoItemHandler(todo_repo))
    QueryBus.register_handler(ListTodoItemsQuery, ListTodoItemsHandler(todo_repo))

    # Register event handlers
    DomainEventDispatcher.register(TodoItemCreatedEvent, handle_todo_created)
    DomainEventDispatcher.register(TodoItemCompletedEvent, handle_todo_completed)
    DomainEventDispatcher.register(TodoItemCancelledEvent, handle_todo_cancelled)

    # Register middleware
    CommandBus.add_middleware(logging_middleware)
    CommandBus.add_middleware(validation_middleware)
    QueryBus.add_middleware(logging_middleware)


async def initialize_todolist():
    """Initialize the TodoList bounded context."""
    await register_handlers()
