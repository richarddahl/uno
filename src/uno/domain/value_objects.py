# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Value Objects for the Uno framework.

Value Objects are immutable domain objects that are defined by their attributes
rather than their identity. They are used to model concepts from the domain
where the identity of the object is not important.

Example:
    class Email(ValueObject):
        address: str

        @model_validator(mode='after')
        def _validate_email(self) -> 'Email':
            if '@' not in self.address or '.' not in self.address.split('@')[-1]:
                raise ValueError(f"Invalid email format: {self.address}")
            return self

    # Usage
    email = Email(address="test@example.com")
"""

from typing import Any, ClassVar, TypeVar, final, cast
from typing_extensions import Self
from pydantic import BaseModel, ConfigDict, model_validator

from uno.domain.protocols import ValueObjectProtocol

T = TypeVar("T", bound="ValueObject")


class ValueObject(BaseModel):
    """Base class for value objects.

    Value objects are immutable domain objects that are defined by their attributes
    rather than their identity. They are equal if all their attributes are equal.

    This class implements the ValueObjectProtocol through its methods, but doesn't
    explicitly inherit from it to avoid metaclass conflicts with Pydantic.

    Features:
    - Immutable after creation
    - Value-based equality
    - Hashable for use in sets and dictionaries
    - Built-in validation
    - JSON serialization
    - Type-safe construction
    """

    # Configuration for Pydantic
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,  # Make instances immutable
        extra="forbid",  # Prevent extra fields
        validate_assignment=True,  # Validate on attribute assignment
        arbitrary_types_allowed=True,  # Allow non-pydantic types
    )

    def __eq__(self, other: object) -> bool:
        """Value objects are equal if their attributes are equal."""
        if not isinstance(other, type(self)):
            return False
        return self.model_dump() == other.model_dump()

    def __hash__(self) -> int:
        """Value objects are hashable based on their attributes."""
        return hash((type(self),) + tuple(self.model_dump().values()))

    def __repr__(self) -> str:
        """String representation for debugging."""
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.model_dump().items())
        return f"{self.__class__.__name__}({attrs})"

    @classmethod
    def create(cls: type[T], **data: Any) -> T:
        """Create a new instance of the value object with the given data.

        This method validates the data before creating the instance.

        Args:
            **data: The data to create the value object with

        Returns:
            A new instance of the value object

        Raises:
            ValueError: If validation fails
        """
        return cls(**data)

    @model_validator(mode="after")
    def _validate_value_object(self: T) -> T:
        """Override this method in subclasses to add custom validation.

        Example:
            @model_validator(mode='after')
            def _validate_email(self) -> 'Email':
                if '@' not in self.address:
                    raise ValueError("Invalid email format")
                return self
        """
        return self

    def copy(self: T, **changes: Any) -> T:
        """Create a copy of the value object with the given changes.

        Args:
            **changes: The attributes to change

        Returns:
            A new instance with the changes applied

        Raises:
            ValueError: If validation fails
        """
        current = self.model_dump()
        return self.__class__.create(**{**current, **changes})
