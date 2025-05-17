# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Value objects for inventory domain.
"""

from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Literal,
    Self,
    TypeVar,
)

from pydantic import (
    ConfigDict,
    Field,
    field_validator,
)

from uno.domain.value_object import ValueObject
from uno.errors import UnoError
from uno.errors.codes import ErrorCode

if TYPE_CHECKING:
    from examples.app.domain.inventory.measurement import Measurement

# NOTE: Do NOT import or re-export Measurement here.
# Measurement must be imported directly from measurement.py to avoid circular imports.


T = TypeVar("T")

# String type alias for type hints (avoids circular imports in annotations)
MeasurementTypeStr = "Mass | Volume | Dimension | Count"


class CountUnit(Enum):
    """Count units (each, dozen, etc.)."""

    EACH = "each"
    DOZEN = "dozen"
    CASE = "case"
    PALLET = "pallet"

    def __str__(self) -> str:
        return self.value


class Count(ValueObject):
    type: Literal["count"] = Field("count", frozen=True)
    value: float
    unit: CountUnit

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float | int) -> float:
        """Validate count value."""
        if v < 0:
            raise ValueError("Count value must be non-negative")
        return v

    def __str__(self) -> str:
        return f"{self.value} {self.unit}"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Count):
            return False
        return self.value == other.value and self.unit == other.unit

    def __hash__(self) -> int:
        return hash((self.type, self.value, self.unit))

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, Count):
            return False
        return self.value < other.value

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, Count):
            return False
        return self.value > other.value

    def __le__(self, other: Any) -> bool:
        if not isinstance(other, Count):
            return False
        return self.value <= other.value

    def __ge__(self, other: Any) -> bool:
        if not isinstance(other, Count):
            return False
        return self.value >= other.value

    def __add__(self, other: Any) -> "Count":
        if not isinstance(other, Count):
            raise ValueError("Can only add Count to Count")
        if self.unit != other.unit:
            raise ValueError("Cannot add counts with different units")
        return Count(type="count", value=self.value + other.value, unit=self.unit)

    def __sub__(self, other: Any) -> "Count":
        if not isinstance(other, Count):
            raise ValueError("Can only subtract Count from Count")
        if self.unit != other.unit:
            raise ValueError("Cannot subtract counts with different units")
        return Count(type="count", value=self.value - other.value, unit=self.unit)

    def __mul__(self, other: Any) -> "Count":
        if not isinstance(other, int | float):
            raise ValueError("Can only multiply Count by number")
        return Count(type="count", value=self.value * float(other), unit=self.unit)

    def __truediv__(self, other: Any) -> "Count":
        if not isinstance(other, int | float):
            raise ValueError("Can only divide Count by number")
        return Count(type="count", value=self.value / float(other), unit=self.unit)

    @classmethod
    def from_each(cls, value: int | float) -> "Count":
        """Create a count from a number of each."""
        return cls(type="count", value=float(value), unit=CountUnit.EACH)

    @classmethod
    def from_dozen(cls, value: int | float) -> "Count":
        """Create a count from a number of dozen."""
        return cls(type="count", value=float(value), unit=CountUnit.DOZEN)

    @classmethod
    def from_case(cls, value: int | float) -> "Count":
        """Create a count from a number of cases."""
        return cls(type="count", value=float(value), unit=CountUnit.CASE)

    @classmethod
    def from_pallet(cls, value: int | float) -> "Count":
        """Create a count from a number of pallets."""
        return cls(type="count", value=float(value), unit=CountUnit.PALLET)

    def to_each(self) -> float:
        """Convert count to number of each."""
        if self.unit == CountUnit.DOZEN:
            return self.value * 12
        elif self.unit == CountUnit.CASE:
            return self.value * 144
        elif self.unit == CountUnit.PALLET:
            return self.value * 1728
        return self.value

    def to_dozen(self) -> float:
        """Convert count to number of dozen."""
        if self.unit == CountUnit.EACH:
            return self.value / 12
        elif self.unit == CountUnit.CASE:
            return self.value * 12
        elif self.unit == CountUnit.PALLET:
            return self.value * 144
        return self.value

    def to_case(self) -> float:
        """Convert count to number of cases."""
        if self.unit == CountUnit.EACH:
            return self.value / 144
        elif self.unit == CountUnit.DOZEN:
            return self.value / 12
        elif self.unit == CountUnit.PALLET:
            return self.value * 12
        return self.value

    def to_pallet(self) -> float:
        """Convert count to number of pallets."""
        if self.unit == CountUnit.EACH:
            return self.value / 1728
        elif self.unit == CountUnit.DOZEN:
            return self.value / 144
        elif self.unit == CountUnit.CASE:
            return self.value / 12
        return self.value


class MassUnit(Enum):
    """Mass units (kg, g, lb, oz, etc.)."""

    KILOGRAM = ("kg", 1.0)
    GRAM = ("g", 0.001)
    POUND = ("lb", 0.45359237)
    OUNCE = ("oz", 0.0283495231)
    STONE = ("stone", 6.35029318)
    TONNE = ("tonne", 1000.0)

    @property
    def symbol(self) -> str:
        """The unit symbol."""
        return self.value[0]

    @property
    def to_kg(self) -> float:
        """Convert to kilograms."""
        return self.value[1]

    def to_standard(self, amount: float) -> float:
        """Convert to standard unit (kilograms)."""
        return amount * self.to_kg

    def from_standard(self, kg: float) -> float:
        """Convert from standard unit (kilograms)."""
        return kg / self.to_kg


class Mass(ValueObject):
    type: Literal["mass"] = Field("mass", frozen=True)
    value: float
    unit: MassUnit

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    """Value object representing a mass with units (kg, g, etc.).

    Attributes:
        value: float value in the specified unit
        unit: MassUnit enum value
    """

    MIN_MASS: ClassVar[float] = 0.0

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float | int | str) -> float:
        """Validate amount is non-negative."""
        if not isinstance(v, float):
            v = float(str(v))
        if v < cls.MIN_MASS:
            raise ValueError(f"Mass must be >= {cls.MIN_MASS}")
        return v

    def __str__(self) -> str:
        """Return string representation of mass."""
        return f"{self.value} {self.unit.symbol}"

    @classmethod
    def from_kg(cls, kg: float) -> Self:
        """Create a Mass from a kilogram value."""
        return cls(type="mass", value=float(kg), unit=MassUnit.KILOGRAM)

    @classmethod
    def from_value(cls, value: float, unit: MassUnit) -> Self:
        """Create a Mass from a value and unit."""
        return cls(type="mass", value=float(value), unit=unit)

    def to_kg(self) -> float:
        """Convert to kilograms."""
        return self.unit.to_standard(self.value)

    def to_unit(self, target_unit: MassUnit) -> Self:
        """Convert to a different unit."""
        # First convert to standard unit (kg)
        kg = self.to_kg()
        # Then convert from standard to target
        value = target_unit.from_standard(kg)
        return self.__class__(type="mass", value=value, unit=target_unit)

    def to_measurement(self) -> "Measurement":
        """Convert mass to a measurement."""
        from examples.app.domain.inventory.measurement import Measurement

        return Measurement(type="mass", value=self)


class DimensionUnit(Enum):
    """Dimension units (m, cm, mm, in, ft, etc.)."""

    METER = ("m", 1.0)
    CENTIMETER = ("cm", 0.01)
    MILLIMETER = ("mm", 0.001)
    INCH = ("in", 0.0254)
    FOOT = ("ft", 0.3048)
    YARD = ("yd", 0.9144)

    @property
    def symbol(self) -> str:
        """The unit symbol."""
        return self.value[0]

    @property
    def to_meter(self) -> float:
        """Convert to meters."""
        return self.value[1]

    def to_standard(self, amount: float) -> float:
        """Convert to standard unit (meters)."""
        return amount * self.to_meter

    def from_standard(self, meters: float) -> float:
        """Convert from standard unit (meters)."""
        return meters / self.to_meter


class Dimension(ValueObject):
    type: Literal["dimension"] = Field("dimension", frozen=True)
    value: float
    unit: DimensionUnit

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    """Value object representing a dimension with units (m, cm, mm, in, ft, etc.).

    Attributes:
        value: float value in the specified unit
        unit: DimensionUnit enum value
    """

    MIN_DIMENSION: ClassVar[float] = 0.0

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float | int | str) -> float:
        """Validate amount is non-negative."""
        if not isinstance(v, float):
            v = float(str(v))
        if v < cls.MIN_DIMENSION:
            raise ValueError(f"Dimension must be >= {cls.MIN_DIMENSION}")
        return v

    def __str__(self) -> str:
        """Return string representation of dimension."""
        return f"{self.value} {self.unit.symbol}"

    @classmethod
    def from_meter(cls, meter: float) -> Self:
        """Create a Dimension from a meter value."""
        return cls(type="dimension", value=meter, unit=DimensionUnit.METER)

    @classmethod
    def from_value(cls, value: float, unit: DimensionUnit) -> Self:
        """Create a Dimension from a value and unit."""
        return cls(type="dimension", value=value, unit=unit)

    def to_meter(self) -> float:
        """Convert to meters."""
        return self.unit.to_standard(self.value)

    def to_unit(self, target_unit: DimensionUnit) -> Self:
        """Convert to a different unit."""
        # First convert to standard unit (m)
        meter = self.to_meter()
        # Then convert from standard to target
        value = target_unit.from_standard(meter)
        return self.__class__(type="dimension", value=value, unit=target_unit)

    def to_measurement(self) -> "Measurement":
        """Convert dimension to a measurement."""

        return Measurement(type="dimension", value=self)


class VolumeUnit(Enum):
    """Volume units (L, mL, gal, etc.)."""

    LITER = ("L", 1.0)
    MILLILITER = ("mL", 0.001)
    CUBIC_METER = ("m³", 1000.0)
    CUBIC_CENTIMETER = ("cm³", 0.001)
    GALLON_US = ("gal", 3.78541)
    QUART_US = ("qt", 0.946353)
    PINT_US = ("pt", 0.473176)
    FLUID_OUNCE_US = ("fl oz", 0.0295735)

    @property
    def symbol(self) -> str:
        """The unit symbol."""
        return self.value[0]

    @property
    def to_liter(self) -> float:
        """Convert to liters."""
        return self.value[1]

    def to_standard(self, amount: float) -> float:
        """Convert to standard unit (liters)."""
        return amount * self.to_liter

    def from_standard(self, liters: float) -> float:
        """Convert from standard unit (liters)."""
        return liters / self.to_liter


class Volume(ValueObject):
    type: Literal["volume"] = Field("volume", frozen=True)
    value: float
    unit: VolumeUnit

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    """Value object representing a volume with units (L, mL, gal, etc.).

    Attributes:
        value: float value in the specified unit
        unit: VolumeUnit enum value
    """

    MIN_VOLUME: ClassVar[float] = 0.0

    model_config = ConfigDict(frozen=True)

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: float) -> float:
        """Validate value is non-negative."""
        v_float = float(v)
        if v_float < cls.MIN_VOLUME:
            raise ValueError(f"Volume must be >= {cls.MIN_VOLUME}")
        return v_float

    def __str__(self) -> str:
        """Return string representation of volume."""
        return f"{self.value} {self.unit.symbol}"

    @classmethod
    def from_liter(cls, liter: float) -> Self:
        """Create a Volume from a liter value."""
        return cls(type="volume", value=liter, unit=VolumeUnit.LITER)

    @classmethod
    def from_value(cls, value: float, unit: VolumeUnit) -> Self:
        """Create a Volume from a value and unit."""
        return cls(type="volume", value=value, unit=unit)

    def to_liter(self) -> float:
        """Convert to liters."""
        return self.unit.to_standard(self.value)

    def to_unit(self, target_unit: VolumeUnit) -> Self:
        """Convert to a different unit."""
        # First convert to standard unit (L)
        liter = self.to_liter()
        # Then convert from standard to target
        value = target_unit.from_standard(liter)
        return self.__class__(type="volume", value=value, unit=target_unit)

    def to_measurement(self) -> "Measurement":
        """Convert volume to a measurement."""

        return Measurement(type="volume", value=self)


class Currency(Enum):
    """Currency codes (USD, EUR, etc.)."""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"


class Money(ValueObject):
    """Value object representing an amount of money with currency."""

    amount: Decimal
    currency: Currency

    model_config = ConfigDict(frozen=True, from_attributes=True)

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: Decimal | float | int | str) -> Decimal:
        """Round amount to 2 decimal places."""
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        if v < 0:
            raise ValueError("Money amount must be non-negative")
        return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def __str__(self) -> str:
        """Return string representation of money."""
        return f"{self.amount} {self.currency.value}"

    def __float__(self) -> float:
        """Return float representation of amount."""
        return float(self.amount)

    def __repr__(self) -> str:
        """Return string representation with currency."""
        return f"Money(amount={self.amount}, currency={self.currency.value})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Money):
            return self.amount == other.amount and self.currency == other.currency
        return False

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))

    def to_dict(self) -> dict[str, Any]:
        """Convert Money to dictionary with proper types."""
        return {"amount": float(self.amount), "currency": self.currency.value}

    def pretty(self) -> str:
        """Return formatted representation with currency symbol."""
        symbols = {
            Currency.USD: "$",
            Currency.EUR: "€",
            Currency.GBP: "£",
            Currency.JPY: "¥",
            Currency.CAD: "C$",
            Currency.AUD: "A$",
        }
        symbol = symbols.get(self.currency, "")
        return f"{symbol}{self.amount}"

    def to(self, target_currency: Currency, fx_rate: Decimal | None = None) -> "Money":
        """Convert to another currency using provided fx rate.

        Args:
            target_currency: The target currency to convert to.
            fx_rate: Exchange rate for conversion. Required.

        Returns:
            New Money object in target currency.
        Raises:
            Error: If exchange rate is not provided or conversion fails.
        """
        if target_currency == self.currency:
            return self

        if fx_rate is None:
            raise UnoError(
                code=ErrorCode.INVALID_INPUT,
                message="Exchange rate is required for currency conversion",
            )

        try:
            new_amount = (self.amount * Decimal(str(fx_rate))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            return Money(amount=new_amount, currency=target_currency)
        except Exception as e:
            raise UnoError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Currency conversion failed: {e}",
            ) from e

    @classmethod
    def from_value(cls, value: Decimal | float | int, currency: Currency) -> "Money":
        """Create Money from a value and currency with validation.

        Args:
            value: The monetary value.
            currency: The currency.

        Returns:
            New Money object.

        Raises:
            Error: If the value is invalid or negative.
        """
        try:
            if isinstance(value, int | float):
                value = Decimal(str(value))

            if value < 0:
                raise UnoError(
                    code=ErrorCode.INVALID_INPUT,
                    message="Money amount must be non-negative",
                )

            return cls(amount=value, currency=currency)
        except UnoError:
            raise
        except Exception as e:
            raise UnoError(
                code=ErrorCode.INVALID_INPUT, message=f"Invalid money value: {e}"
            ) from e


class Grade(ValueObject):
    """Value object representing a grade (A, B, C, etc.)."""

    value: float = Field(gt=0.0, le=100.0, description="The grade of the item")

    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        """Return string representation of grade."""
        return str(self.value)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Grade):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Grade):
            return self.value < other.value
        return False

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, Grade):
            return self.value > other.value
        return False

    def __le__(self, other: Any) -> bool:
        if isinstance(other, Grade):
            return self.value <= other.value
        return False

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, Grade):
            return self.value >= other.value
        return False


class AlcoholContent(ValueObject):
    """Value object representing an alcohol content by volume (ABV)."""

    # Constant for maximum ABV percentage
    MAX_ABV_PERCENT: ClassVar[int] = 100

    percentage: float  # ABV percentage

    model_config = ConfigDict(frozen=True)

    @field_validator("percentage")
    @classmethod
    def validate_percentage(cls, v: float | int | str) -> float:
        """Validate alcohol content percentage."""
        if not isinstance(v, float):
            v = float(str(v))
        if v < 0 or v > cls.MAX_ABV_PERCENT:
            raise ValueError(
                f"Alcohol content must be between 0 and {cls.MAX_ABV_PERCENT}%"
            )
        return v

    def __str__(self) -> str:
        """Return string representation of alcohol content."""
        return f"{self.percentage}% ABV"
