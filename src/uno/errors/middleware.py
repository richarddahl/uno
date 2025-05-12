"""
Error middleware for handling and formatting API errors.

This module provides middleware for catching and properly formatting errors
in API responses, including context information from UnoErrors.
"""

import logging
import traceback
from typing import Any, Callable, Dict, List, Optional, Type

from uno.errors.base import ErrorCategory, ErrorSeverity, UnoError
from uno.errors.logging import ErrorLogger


class ErrorMiddleware:
    """
    Middleware for handling errors in API routes.

    This middleware catches exceptions, formats them appropriately for API responses,
    and logs them with context information.
    """

    def __init__(
        self,
        *,
        logger: "LoggerProtocol",
        include_traceback: bool = False,
        handle_non_uno_errors: bool = True,
    ) -> None:
        """
        Initialize the error middleware (DI required).

        Args:
            logger: Logger instance (must be provided via DI)
            include_traceback: Whether to include traceback in API responses
            handle_non_uno_errors: Whether to handle non-UnoError exceptions
        """
        if logger is None:
            raise ValueError("LoggerProtocol instance must be provided via DI.")
        self.include_traceback = include_traceback
        self.logger = logger
        self.handle_non_uno_errors = handle_non_uno_errors

    async def __call__(
        self,
        request: Any,
        call_next: Callable,
    ) -> Any:
        """
        Process a request and handle any errors.

        Args:
            request: The request object
            call_next: Function to call the next middleware

        Returns:
            The response object
        """
        try:
            return await call_next(request)
        except UnoError as e:
            # Log the error
            ErrorLogger.log_error(e, self.logger)

            # Create response with error details
            return self._create_error_response(e)
        except Exception as e:
            if not self.handle_non_uno_errors:
                raise

            # Wrap in UnoError
            wrapped = UnoError(
                message=str(e),
                code="UNHANDLED_ERROR",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.ERROR,
                exception_type=type(e).__name__,
            )

            # Log the error
            ErrorLogger.log_error(wrapped, self.logger)

            # Create response with error details
            return self._create_error_response(wrapped)

    def _create_error_response(self, error: UnoError) -> Any:
        """
        Create an API response for an error.

        This method must be implemented by framework-specific subclasses
        since the response format depends on the web framework.

        Args:
            error: The error to create a response for

        Returns:
            A framework-specific response object
        """
        # Base implementation just creates a dict with error details
        # Subclasses should override this to create proper response objects
        response_data = {
            "error": {
                "code": error.code,
                "message": error.message,
                "category": error.context.category.name,
            }
        }

        # Include additional context if available
        if error.context.details:
            response_data["error"]["details"] = error.context.details

        # Include traceback if configured
        if self.include_traceback and hasattr(error, "traceback"):
            response_data["error"]["traceback"] = error.traceback

        return response_data


# Framework-specific implementation examples could be provided here
