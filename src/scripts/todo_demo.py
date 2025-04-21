#!/usr/bin/env python
"""
Demo script to showcase the TodoList bounded context.
"""
import asyncio
import sys
from pathlib import Path
import logging

# Ensure the src directory is in the Python path
sys.path.append(str(Path(__file__).parent.parent))

from uno.examples.todolist import initialize_todolist
from uno.examples.todolist.domain.models import TodoPriority
from uno.examples.todolist.application.commands import (
    CreateTodoItemCommand,
    CompleteTodoItemCommand,
)
from uno.core.application.commands import CommandBus
from uno.examples.todolist.application.queries import ListTodoItemsQuery
from uno.core.application.queries import QueryBus


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


async def run_demo():
    """Run the demo."""
    logger.info("Initializing TodoList bounded context...")
    await initialize_todolist()

    logger.info("Creating todo items...")
    # Create some sample todo items
    todo1 = await CommandBus.dispatch(
        CreateTodoItemCommand(
            title="Implement domain model",
            description="Create entities, value objects, and aggregates",
            priority=TodoPriority.HIGH,
        )
    )
    logger.info(f"Created todo: {todo1.id} - {todo1.title}")

    todo2 = await CommandBus.dispatch(
        CreateTodoItemCommand(
            title="Build repository layer",
            description="Implement data access abstractions",
            priority=TodoPriority.MEDIUM,
        )
    )
    logger.info(f"Created todo: {todo2.id} - {todo2.title}")

    todo3 = await CommandBus.dispatch(
        CreateTodoItemCommand(
            title="Add comprehensive tests",
            description="Ensure code quality and correctness",
            priority=TodoPriority.HIGH,
        )
    )
    logger.info(f"Created todo: {todo3.id} - {todo3.title}")

    # List all todos
    logger.info("Listing all todo items:")
    todos = await QueryBus.dispatch(ListTodoItemsQuery())
    for todo in todos:
        logger.info(
            f"- {todo.id}: {todo.title} (Priority: {todo.priority.value}, Status: {todo.status.value})"
        )

    # Complete a todo
    logger.info(f"Completing todo: {todo1.id}")
    updated_todo = await CommandBus.dispatch(CompleteTodoItemCommand(todo_id=todo1.id))
    logger.info(f"Todo {updated_todo.id} is now {updated_todo.status.value}")

    # List high priority todos
    logger.info("Listing high priority todo items:")
    high_priority_todos = await QueryBus.dispatch(
        ListTodoItemsQuery(priority=TodoPriority.HIGH)
    )
    for todo in high_priority_todos:
        status = todo.status.value
        logger.info(f"- {todo.id}: {todo.title} (Status: {status})")

    logger.info("Demo completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_demo())
