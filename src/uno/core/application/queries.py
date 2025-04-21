"""
Query handling infrastructure for the Uno framework.

This module provides base classes for implementing the Query pattern,
which formalizes data retrieval operations as explicit query objects.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar, Dict, Any, Type, Callable, List, Optional

T = TypeVar("T")  # Query result type
Q = TypeVar("Q")  # Query type


@dataclass
class Query:
    """Base class for all queries in the system."""

    pass


class QueryHandler(Generic[Q, T], ABC):
    """Base class for query handlers."""

    @abstractmethod
    async def handle(self, query: Q) -> T:
        """Handle the given query and return a result."""
        pass


class QueryBus:
    """Query bus for dispatching queries to their handlers."""

    _handlers: dict[type[Query], QueryHandler] = {}
    _middleware: list[Callable] = []

    @classmethod
    def register_handler(cls, query_type: type[Query], handler: QueryHandler) -> None:
        """Register a handler for a specific query type."""
        cls._handlers[query_type] = handler

    @classmethod
    def add_middleware(cls, middleware: Callable) -> None:
        """Add middleware to the query processing pipeline."""
        cls._middleware.append(middleware)

    @classmethod
    async def dispatch(cls, query: Query) -> Any:
        """Dispatch a query to its registered handler."""
        query_type = type(query)

        if query_type not in cls._handlers:
            raise ValueError(
                f"No handler registered for query type {query_type.__name__}"
            )

        handler = cls._handlers[query_type]

        # Apply middleware (if any)
        if cls._middleware:
            return await cls._execute_middleware_chain(query, handler)

        # No middleware, execute handler directly
        return await handler.handle(query)

    @classmethod
    async def _execute_middleware_chain(
        cls, query: Query, handler: QueryHandler
    ) -> Any:
        """Execute the middleware chain."""

        async def execute_handler(qry):
            return await handler.handle(qry)

        # Build the middleware chain
        chain = execute_handler
        for middleware in reversed(cls._middleware):
            next_chain = chain
            chain = lambda qry, next_chain=next_chain: middleware(qry, next_chain)

        # Execute the chain
        return await chain(query)
