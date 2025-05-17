# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno
from typing import Any

from uno.errors.base import UnoError
from uno.utilities.security import sanitize_sensitive_info


def to_http_error_response(error: UnoError) -> dict[str, Any]:
    """
    Convert an UnoError instance to a standard HTTP error response format.

    Args:
        error: The UnoError instance to convert.

    Returns:
        A dictionary representing the HTTP error response.
    """
    response = {
        "code": error.code,
        "message": error.message,
        "category": error.category.name,
        "severity": error.severity.name,
        "context": sanitize_sensitive_info(error.context),
        "timestamp": error.timestamp.isoformat(),
    }
    return response
