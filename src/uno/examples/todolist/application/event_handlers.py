# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Event handlers for the TodoList bounded context.
"""

# from uno.core.logging.logger import get_logger  # Removed for DI-based injection
import logging
from datetime import datetime

from uno.examples.todolist.domain.models import (
    TodoItemCreatedEvent,
    TodoItemCompletedEvent,
    TodoItemCancelledEvent,
)



async def handle_todo_created(event: TodoItemCreatedEvent, logger: logging.Logger) -> None:
    """Handle the todo item created event."""
    logger.info(f"Todo item created: {event.todo_id} - '{event.title}'")
    # In a real app, you might want to:
    # - Send a notification
    # - Update statistics
    # - Sync with external systems


async def handle_todo_completed(event: TodoItemCompletedEvent, logger: logging.Logger) -> None:
    """Handle the todo item completed event."""
    logger.info(f"Todo item completed: {event.todo_id} at {event.completed_at}")
    # In a real app, you might want to:
    # - Send a notification
    # - Update statistics
    # - Trigger follow-up workflows


async def handle_todo_cancelled(event: TodoItemCancelledEvent, logger: logging.Logger) -> None:
    """Handle the todo item cancelled event."""
    reason_text = f"Reason: {event.reason}" if event.reason else "No reason provided"
    logger.info(f"Todo item cancelled: {event.todo_id}. {reason_text}")
    # Handle cancellation logic
