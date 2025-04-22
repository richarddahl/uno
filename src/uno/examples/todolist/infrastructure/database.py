# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Database models for the TodoList bounded context.
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base

from uno.database.base import Base
from uno.examples.todolist.domain.models import TodoPriority, TodoStatus


class TodoItemModel(Base):
    """SQLAlchemy model for todo items."""

    __tablename__ = "todo_items"

    id = Column(String(36), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TodoStatus), default=TodoStatus.PENDING, nullable=False)
    priority = Column(Enum(TodoPriority), default=TodoPriority.MEDIUM, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
