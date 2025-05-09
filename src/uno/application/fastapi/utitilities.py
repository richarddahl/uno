# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno
from fastapi import Request
from fastapi.responses import JSONResponse

from uno.errors.base import UnoError
from uno.utilities.http import to_http_error_response


def fastapi_exception_handler(request: Request, exc: UnoError) -> JSONResponse:
    """
    FastAPI exception handler for UnoError.

    Args:
        request: The HTTP request that caused the exception.
        exc: The UnoError instance.

    Returns:
        A JSONResponse with the error details.
    """
    error_response = to_http_error_response(exc)
    return JSONResponse(status_code=500, content=error_response)
