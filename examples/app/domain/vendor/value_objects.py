# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Value objects for Uno example app: Grade, EmailAddress, etc.
"""

from pydantic import (
    ConfigDict,
    EmailStr,
    model_serializer,
)

from uno.domain import ValueObject


# --- Email Address ---
class EmailAddress(ValueObject):
    """
    Value object for email addresses with validation.

    Usage:
        EmailAddress(value="user@example.com")  # Valid, creates instance
        EmailAddress(value="invalid")  # Raises ValueError for invalid format
    """

    value: EmailStr

    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        """Return the email address as a string."""
        return self.value

    @model_serializer(mode="plain")
    def serialize_email(self) -> str:
        """Serialize EmailAddress as a plain string for model_dump and JSON."""
        return self.value
