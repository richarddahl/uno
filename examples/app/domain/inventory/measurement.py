"""
Measurement value object for representing polymorphic quantities.
"""

from __future__ import annotations

import enum
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field

from examples.app.domain.inventory.value_objects import (
    Count,
    Dimension,
    Mass,
    Volume,
)
from uno.domain.value_object import ValueObject


class Measurement(ValueObject):
    """Polymorphic value object for representing measurement as mass, volume, dimension, or count.
    Uno idiomatic discriminated union using Pydantic 2."""

    type: Literal["mass", "volume", "dimension", "count"]
    value: Annotated[
        Count | Mass | Volume | Dimension,
        Field(discriminator="type", validate_default=True),
    ]

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    @classmethod
    def from_count(cls, count: Count | int | float | Decimal) -> "Measurement":
        """Create a Measurement of type 'count' from a Count value object or primitive."""
        if isinstance(count, Count):
            return cls(type="count", value=count)
        elif isinstance(count, int | float | Decimal):
            return cls(type="count", value=Count.from_each(float(count)))
        raise TypeError("count must be a Count, int, float, or Decimal")

    @classmethod
    def from_mass(cls, mass: "Mass | float") -> "Measurement":
        """Create a Measurement of type 'mass' from a Mass value object or primitive."""
        from .value_objects import Mass, MassUnit

        if isinstance(mass, Mass):
            return cls(type="mass", value=mass)
        elif isinstance(mass, float):
            return cls(type="mass", value=Mass(amount=mass, unit=MassUnit.KILOGRAM))
        raise TypeError("mass must be a Mass or float")

    @classmethod
    def from_volume(cls, volume: "Volume | float") -> "Measurement":
        """Create a Measurement of type 'volume' from a Volume value object or primitive."""
        from .value_objects import Volume, VolumeUnit

        if isinstance(volume, Volume):
            return cls(type="volume", value=volume)
        elif isinstance(volume, float):
            return cls(
                type="volume", value=Volume(amount=volume, unit=VolumeUnit.LITER)
            )
        raise TypeError("volume must be a Volume or float")

    @classmethod
    def from_dimension(cls, dimension: "Dimension | float") -> "Measurement":
        """Create a Measurement of type 'dimension' from a Dimension value object or primitive."""
        from .value_objects import Dimension, DimensionUnit

        if isinstance(dimension, Dimension):
            return cls(type="dimension", value=dimension)
        elif isinstance(dimension, float):
            return cls(
                type="dimension",
                value=Dimension(amount=dimension, unit=DimensionUnit.METER),
            )
        raise TypeError("dimension must be a Dimension or float")

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_model

    @classmethod
    def validate_model(cls, data: Any) -> "Measurement":
        """Validate model inputs and return a valid Measurement instance."""
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")

        if "type" not in data:
            raise ValueError("Missing 'type' field")

        if "value" not in data:
            raise ValueError("Missing 'value' field")

        if data["type"] == "mass":
            from .value_objects import Mass

            if not isinstance(data["value"], Mass):
                raise ValueError("Value must be of type Mass for type 'mass'")
        elif data["type"] == "volume":
            from .value_objects import Volume

            if not isinstance(data["value"], Volume):
                raise ValueError("Value must be of type Volume for type 'volume'")
        elif data["type"] == "dimension":
            from .value_objects import Dimension

            if not isinstance(data["value"], Dimension):
                raise ValueError("Value must be of type Dimension for type 'dimension'")
        elif data["type"] == "count":
            from .value_objects import Count

            if not isinstance(data["value"], Count):
                raise ValueError("Value must be of type Count for type 'count'")
        else:
            raise ValueError(f"Invalid type: {data['type']}")

        return cls(type=data["type"], value=data["value"])

    def __str__(self) -> str:
        """Return string representation of measurement."""
        return f"{self.type}: {str(self.value)}"

    def __eq__(self, other: object) -> bool:
        """Compare quantities for equality."""
        if not isinstance(other, Measurement):
            return False
        return self.type == other.type and self.value == other.value

    def __hash__(self) -> int:
        """Return hash of measurement."""
        return hash((self.type, self.value))

    @classmethod
    def from_each(cls, each: "Count | int | float") -> "Measurement":
        """Create a Measurement of type 'count' from a Count value object or primitive (int/float, using EACH unit).

        Args:
            each: The Count value object or primitive.

        Returns:
            A new Measurement instance with Count value.

        Raises:
            TypeError: If each is not a Count, int, or float.
        """
        from .value_objects import Count

        if isinstance(each, Count):
            return cls(type="count", value=each)
        elif isinstance(each, (int, float)):
            return cls(type="count", value=Count.from_each(each))
        raise TypeError("each must be a Count, int, or float")
