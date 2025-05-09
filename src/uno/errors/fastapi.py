# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
FastAPI-specific error context middleware implementation.

This module provides a concrete implementation of the ErrorContextMiddleware
for FastAPI applications, automatically enriching error context with request
information.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, Optional, Set, Union

from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.types import ASGIApp

from uno.errors.context import (
    ErrorContext,
    ErrorContextMiddleware,
    add_async_context,
    reset_async_context,
)


class FastAPIErrorContextMiddleware(ErrorContextMiddleware, BaseHTTPMiddleware):
    """FastAPI middleware for error context enrichment.

    This middleware automatically adds standard request information to the
    error context for any errors raised during request processing.

    Example:
        ```python
        from fastapi import FastAPI
        from uno.errors.fastapi import FastAPIErrorContextMiddleware

        app = FastAPI()
        app.add_middleware(FastAPIErrorContextMiddleware)

        @app.get("/items/{item_id}")
        async def read_item(item_id: int):
            # Any UnoError raised here will have request context
            # ...
        ```
    """

    def __init__(
        self,
        app: ASGIApp,
        include_headers: bool = True,
        include_body: bool = False,
        include_query_params: bool = True,
        mask_sensitive_fields: bool = True,
        sensitive_fields: set[str] | None = None,
        request_id_header: str = "X-Request-ID",
        generate_request_id: bool = True,
    ):
        """Initialize the FastAPI error context middleware.

        Args:
            app: The ASGI application
            include_headers: Whether to include request headers in the context
            include_body: Whether to include request body in the context
            include_query_params: Whether to include query parameters in the context
            mask_sensitive_fields: Whether to mask sensitive fields
            sensitive_fields: Set of field names to mask
            request_id_header: Header name for request ID
            generate_request_id: Whether to generate a request ID if not provided
        """
        # Initialize both parent classes
        ErrorContextMiddleware.__init__(
            self,
            include_headers=include_headers,
            include_body=include_body,
            include_query_params=include_query_params,
            mask_sensitive_fields=mask_sensitive_fields,
            sensitive_fields=sensitive_fields,
        )
        BaseHTTPMiddleware.__init__(self, app)

        self.request_id_header = request_id_header
        self.generate_request_id = generate_request_id

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and add error context.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint

        Returns:
            The response
        """
        # Extract request information
        context = await self._extract_request_context(request)

        # Add context for the duration of the request
        tokens = []
        try:
            # Add each context item to the async context
            for key, value in context.items():
                token = add_async_context(key, value)
                tokens.append(token)

            # Process the request
            response = await call_next(request)
            return response
        finally:
            # Reset the async context
            for token in reversed(tokens):
                reset_async_context(token)

    async def _extract_request_context(self, request: Request) -> dict[str, Any]:
        """Extract context information from the request.

        Args:
            request: The incoming request

        Returns:
            A dictionary of context values
        """
        context = {}

        # Add request ID
        request_id = request.headers.get(self.request_id_header)
        if not request_id and self.generate_request_id:
            request_id = str(uuid.uuid4())
        if request_id:
            context["request_id"] = request_id

        # Add basic request information
        context["http_method"] = request.method
        context["path"] = request.url.path
        context["client_ip"] = request.client.host if request.client else None

        # Add user agent
        user_agent = request.headers.get("user-agent")
        if user_agent:
            context["user_agent"] = user_agent

        # Add headers if configured
        if self.include_headers:
            headers = {}
            for key, value in request.headers.items():
                headers[key] = self.mask_value(key, value)
            context["headers"] = headers

        # Add query parameters if configured
        if self.include_query_params:
            query_params = {}
            for key, value in request.query_params.items():
                query_params[key] = self.mask_value(key, value)
            context["query_params"] = query_params

        # Body handling would require await request.body() which would consume
        # the body stream, so we skip it here. Applications can add body
        # context in their request handling if needed.

        return context


def add_error_context_middleware(
    app: FastAPI,
    include_headers: bool = True,
    include_body: bool = False,
    include_query_params: bool = True,
    mask_sensitive_fields: bool = True,
    sensitive_fields: set[str] | None = None,
    request_id_header: str = "X-Request-ID",
    generate_request_id: bool = True,
) -> None:
    """Add error context middleware to a FastAPI application.

    Convenience function to add the FastAPIErrorContextMiddleware.

    Args:
        app: The FastAPI application
        include_headers: Whether to include request headers in the context
        include_body: Whether to include request body in the context
        include_query_params: Whether to include query parameters in the context
        mask_sensitive_fields: Whether to mask sensitive fields
        sensitive_fields: Set of field names to mask
        request_id_header: Header name for request ID
        generate_request_id: Whether to generate a request ID if not provided
    """
    app.add_middleware(
        FastAPIErrorContextMiddleware,
        include_headers=include_headers,
        include_body=include_body,
        include_query_params=include_query_params,
        mask_sensitive_fields=mask_sensitive_fields,
        sensitive_fields=sensitive_fields,
        request_id_header=request_id_header,
        generate_request_id=generate_request_id,
    )
