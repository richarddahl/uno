# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Value objects for Uno example app: Grade, EmailAddress, etc.
"""
from uno.core.domain.value_object import ValueObject
from uno.core.errors.result import Success, Failure
from uno.core.errors.definitions import DomainValidationError
from pydantic import field_validator, EmailStr
from typing import ClassVar

class Grade(ValueObject):
    """
    Value object representing a grade (0-100).

    Usage:
        Grade.from_value(95.5) -> Success(Grade)
        Grade.from_value(150) -> Failure(DomainValidationError)
    """
    value: float

    @classmethod
    def from_value(cls, value: float) -> Success["Grade", Exception] | Failure["Grade", Exception]:
        """Construct a Grade from a value, returning Success/Failure."""
        try:
            grade = cls(value=value)
            return Success(grade)
        except Exception as exc:
            return Failure(DomainValidationError("Invalid grade", details={"value": value, "error": str(exc)}))

    @classmethod
    def validate(cls, value: float) -> Success[float, Exception] | Failure[float, Exception]:
        """Validate the grade value, returning Success/Failure."""
        if not (0.0 <= value <= 100.0):
            return Failure(DomainValidationError("Grade must be between 0 and 100", details={"value": value}))
        return Success(value)

    @field_validator("value")
    @classmethod
    def validate_grade(cls, v: float) -> float:
        result = cls.validate(v)
        if isinstance(result, Failure):
            raise ValueError("Grade must be between 0 and 100")
        return v

    model_config: ClassVar = {"frozen": True}

class EmailAddress(ValueObject):
    """
    Value object representing an email address.

    Usage:
        EmailAddress.from_value("user@example.com") -> Success(EmailAddress)
        EmailAddress.from_value("bad-email") -> Failure(DomainValidationError)
    """
    value: EmailStr

    @classmethod
    def from_value(cls, value: str) -> Success["EmailAddress", Exception] | Failure["EmailAddress", Exception]:
        """Construct an EmailAddress, returning Success/Failure."""
        try:
            email = cls(value=value)
            return Success(email)
        except Exception as exc:
            return Failure(DomainValidationError("Invalid email address", details={"value": value, "error": str(exc)}))

    @classmethod
    def validate(cls, value: str) -> Success[str, Exception] | Failure[str, Exception]:
        """Validate the email address, returning Success/Failure."""
        try:
            EmailStr.validate(value)
            return Success(value)
        except Exception as exc:
            return Failure(DomainValidationError("Invalid email address", details={"value": value, "error": str(exc)}))

    model_config: ClassVar = {"frozen": True}
