# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Middleware for the TodoList bounded context.
"""

# from uno.core.logging.logger import get_logger  # Removed for DI-based injection
import logging
from typing import Any, Callable, TypeVar

from uno.core.application.commands import Command
from uno.core.application.queries import Query

T = TypeVar("T")  # Return type



async def logging_middleware(request: Command | Query, next_handler: Callable, logger: logging.Logger) -> Any:
    """Middleware that logs command/query execution."""
    request_type = type(request).__name__
    logger.info(f"Processing {request_type}: {request}")

    try:
        result = await next_handler(request)
        logger.info(f"Successfully processed {request_type}")
        return result
    except Exception as e:
        logger.error(f"Error processing {request_type}: {e}")
        raise


async def validation_middleware(
    request: Command | Query, next_handler: Callable
) -> Any:
    """Middleware that validates commands and queries."""
    # Simple validation example - you can make this more sophisticated
    if isinstance(request, Command) and hasattr(request, "validate"):
        request.validate()

    return await next_handler(request)
