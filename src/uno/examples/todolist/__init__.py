# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
TodoList bounded context initialization.
"""

from uno.core.application.commands import CommandBus
from uno.core.application.queries import QueryBus
from uno.core.events.events import EventBus, EventBusProtocol
from uno.core.logging.logger import LoggerService

# Create a bus for example/demo registration (replace with DI in real app)
event_bus: EventBusProtocol = EventBus(LoggerService())

# from uno.database.session import get_async_session
from uno.examples.todolist.application.commands import (
    CancelTodoItemCommand,
    CompleteTodoItemCommand,
    CreateTodoItemCommand,
)
from uno.examples.todolist.application.event_handlers import (
    handle_todo_cancelled,
    handle_todo_completed,
    handle_todo_created,
)
from uno.examples.todolist.application.handlers import (
    CancelTodoItemHandler,
    CompleteTodoItemHandler,
    CreateTodoItemHandler,
    GetTodoItemHandler,
    ListTodoItemsHandler,
)
from uno.examples.todolist.application.middleware import (
    logging_middleware,
    validation_middleware,
)
from uno.examples.todolist.application.queries import (
    GetTodoItemQuery,
    ListTodoItemsQuery,
)
from uno.examples.todolist.domain.models import (
    TodoItemCancelledEvent,
    TodoItemCompletedEvent,
    TodoItemCreatedEvent,
)
from uno.examples.todolist.infrastructure.repositories import TodoItemRepository


async def register_handlers():
    return
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
    event_bus.subscribe(handle_todo_created, event_type=TodoItemCreatedEvent)
    event_bus.subscribe(handle_todo_completed, event_type=TodoItemCompletedEvent)
    event_bus.subscribe(handle_todo_cancelled, event_type=TodoItemCancelledEvent)

    # Register middleware
    CommandBus.add_middleware(logging_middleware)
    CommandBus.add_middleware(validation_middleware)
    QueryBus.add_middleware(logging_middleware)


async def initialize_todolist():
    """Initialize the TodoList bounded context."""
    await register_handlers()
