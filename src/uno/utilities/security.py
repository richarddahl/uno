# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from typing import Any


def sanitize_sensitive_info(context: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize sensitive information from a context dictionary.

    Args:
        context: The context dictionary to sanitize.

    Returns:
        A sanitized copy of the context dictionary.
    """
    sanitized_context = context.copy()
    if "sensitive" in sanitized_context:
        sanitized_context.pop("sensitive", None)
    return sanitized_context
