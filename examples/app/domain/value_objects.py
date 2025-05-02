# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Value objects for Uno example app: Grade, EmailAddress, etc.
"""

from enum import Enum
from typing import Any, ClassVar, Literal

import pydantic
from pydantic import (
    ConfigDict,
    EmailStr,
    field_validator,
    model_validator,
)

from uno.core.domain.value_object import ValueObject
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Success


class Grade(ValueObject):
    """
    Value object representing a grade (0-100).

    Usage:
        Grade.from_value(95.5) -> Success(Grade)
        Grade.from_value(150) -> Failure(DomainValidationError)
    """

    value: float

    @classmethod
    def from_value(
        cls, value: float
    ) -> Success["Grade", Exception] | Failure["Grade", Exception]:
        """Construct a Grade from a value, returning Success/Failure."""
        validation = cls.validate_value(value)
        if isinstance(validation, Failure):
            return validation
        try:
            grade = cls(value=value)
            return Success(grade)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Invalid grade", details={"value": value, "error": str(exc)}
                )
            )

    @classmethod
    def validate_value(
        cls,
        value: float,
    ) -> Success[None, Exception] | Failure[None, Exception]:
        """Validate the grade value, returning Success/Failure."""
        if not (0.0 <= value <= 100.0):
            return Failure(
                DomainValidationError(
                    "Grade must be between 0 and 100",
                    details={"value": value, "error": "out of bounds"},
                )
            )
        return Success(None)

    def validate(self) -> Success[None, Exception] | Failure[None, Exception]:
        """Validate the grade instance using its value."""
        return self.validate_value(self.value)

    @field_validator("value")
    @classmethod
    def validate_grade(
        cls,
        v: float,
    ) -> float:
        result = cls.validate_value(v)
        if isinstance(result, Failure):
            raise ValueError("Grade must be between 0 and 100")
        return v

    model_config: ClassVar = {"frozen": True}


# --- Count ---


class CountUnit(Enum):
    EACH = ("each", 1.0)
    HALF_DOZEN = ("half_dozen", 6.0)
    DOZEN = ("dozen", 12.0)
    GROSS = ("gross", 144.0)

    @property
    def symbol(self) -> str:
        return self.value[0]

    @property
    def to_each(self) -> float:
        return self.value[1]

    def to_standard(self, amount: float) -> float:
        return amount * self.to_each

    def from_standard(self, each: float) -> float:
        return each / self.to_each


class Count(ValueObject):
    model_config = ConfigDict(frozen=True)

    @pydantic.field_serializer('unit')
    def serialize_unit(self, unit: CountUnit, _info):
        return unit.name

    @pydantic.field_serializer('value')
    def serialize_value(self, value, _info):
        return float(value)

    @pydantic.model_serializer(mode="plain")
    def serialize_count(self):
        return {"value": float(self.value), "unit": self.unit.name}

    @classmethod
    def from_each(cls, each: float | int) -> "Count":
        """
        Create a Count value object from a float or int.
        Accepts both float and int for compatibility with event replay and domain logic.
        """
        try:
            value = float(each)
        except Exception:
            raise ValueError("Count value must be a non-negative float or int")
        if value < 0.0:
            raise ValueError("Count value must be a non-negative float or int")
        return cls(value=value, unit=CountUnit.EACH)

    value: float
    unit: CountUnit

    @classmethod
    def from_value(
        cls, value: float | int, unit: CountUnit
    ) -> Success["Count", Exception] | Failure["Count", Exception]:
        # Accept anything castable to float
        try:
            value = float(value)
        except Exception:
            return Failure(
                DomainValidationError(
                    "Count value must be a number",
                    details={
                        "value": value.model_dump()
                        if hasattr(value, "model_dump")
                        else value,
                        "unit": unit.name if isinstance(unit, Enum) else unit,
                    },
                )
            )
        if value < 0:
            return Failure(
                DomainValidationError(
                    "Count cannot be negative",
                    details={
                        "value": value.model_dump()
                        if hasattr(value, "model_dump")
                        else value,
                        "unit": unit.name if isinstance(unit, Enum) else unit,
                    },
                )
            )
        return Success(cls(value=float(value), unit=unit))

    @model_validator(mode="before")
    @classmethod
    def validate_value(cls, data: dict[str, Any]) -> dict[str, Any]:
        v = data.get("value")
        if not isinstance(v, float) or v < 0:
            raise ValueError(
                "Count value must be a non-negative float"
            )  # details omitted for ValueError
        return data

    def __add__(self, other: "Count") -> "Count":
        if not isinstance(other, Count):
            return NotImplemented
        if self.unit != other.unit:
            raise ValueError(
                f"Cannot add Count with different units: {self.unit} and {other.unit}"
            )
        return Count(value=self.value + other.value, unit=self.unit)

    def __sub__(self, other: "Count") -> "Count":
        if not isinstance(other, Count):
            return NotImplemented
        if self.unit != other.unit:
            raise ValueError(
                f"Cannot subtract Count with different units: {self.unit} and {other.unit}"
            )
        result = self.value - other.value
        if result < 0:
            raise ValueError("Resulting Count cannot be negative")
        return Count(value=result, unit=self.unit)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Count):
            return False
        return self.value == other.value and self.unit == other.unit

    def __hash__(self) -> int:
        return hash((self.value, self.unit))

    def __repr__(self) -> str:
        return f"Count(value={self.value}, unit='{self.unit}')"

    def to_each(self) -> float:
        return self.unit.to_standard(self.value)


# --- Mass ---
class MassUnit(Enum):
    KILOGRAM = ("kg", 1.0)
    GRAM = ("g", 0.001)
    POUND = ("lb", 0.45359237)
    OUNCE = ("oz", 0.0283495231)
    STONE = ("stone", 6.35029318)
    TONNE = ("tonne", 1000.0)

    @property
    def symbol(self) -> str:
        return self.value[0]

    @property
    def to_kg(self) -> float:
        return self.value[1]

    def to_standard(self, amount: float) -> float:
        return amount * self.to_kg

    def from_standard(self, kg: float) -> float:
        return kg / self.to_kg


class Mass(ValueObject):
    model_config = ConfigDict(frozen=True)

    @pydantic.field_serializer('unit')
    def serialize_unit(self, unit: MassUnit, _info):
        return unit.name

    @pydantic.field_serializer('amount')
    def serialize_amount(self, amount, _info):
        return float(amount)

    @pydantic.model_serializer(mode="plain")
    def serialize_mass(self):
        return {"amount": float(self.amount), "unit": self.unit.name}

    amount: float
    unit: MassUnit

    @classmethod
    def from_value(
        cls, amount: float, unit: MassUnit
    ) -> Success["Mass", Exception] | Failure["Mass", Exception]:
        if amount < 0:
            return Failure(
                DomainValidationError(
                    "Mass cannot be negative",
                    details={
                        "amount": amount,
                        "unit": unit.name if hasattr(unit, "name") else unit,
                    },
                )
            )
        return Success(cls(amount=amount, unit=unit))

    def to(
        self, target_unit: MassUnit
    ) -> Success["Mass", Exception] | Failure["Mass", Exception]:
        try:
            kg = self.unit.to_standard(self.amount)
            target_amount = target_unit.from_standard(kg)
            return Success(Mass(amount=target_amount, unit=target_unit))
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Mass conversion failed", details={"error": str(exc)}
                )
            )


# --- Volume ---
class VolumeUnit(Enum):
    LITER = ("L", 1.0)
    MILLILITER = ("mL", 0.001)
    GALLON_US = ("gal_us", 3.78541)
    GALLON_UK = ("gal_uk", 4.54609)
    QUART = ("qt", 0.946353)
    PINT = ("pt", 0.473176)
    FLUID_OUNCE = ("fl_oz", 0.0295735)
    BUSHEL = ("bu", 35.2391)
    BARREL_BEER = ("bbl_beer", 117.3478)  # US beer barrel
    BARREL_WINE = ("bbl_wine", 119.2405)  # US wine barrel

    @property
    def symbol(self) -> str:
        return self.value[0]

    @property
    def to_liter(self) -> float:
        return self.value[1]

    def to_standard(self, amount: float) -> float:
        return amount * self.to_liter

    def from_standard(self, liters: float) -> float:
        return liters / self.to_liter


class Volume(ValueObject):
    model_config = ConfigDict(frozen=True)
    amount: float
    unit: VolumeUnit

    @pydantic.field_serializer('unit')
    def serialize_unit(self, unit: VolumeUnit, _info):
        return unit.name

    @pydantic.field_serializer('amount')
    def serialize_amount(self, amount, _info):
        return float(amount)

    @pydantic.model_serializer(mode="plain")
    def serialize_volume(self):
        return {"amount": float(self.amount), "unit": self.unit.name}

    @classmethod
    def from_value(
        cls, amount: float, unit: VolumeUnit
    ) -> Success["Volume", Exception] | Failure["Volume", Exception]:
        if amount < 0:
            return Failure(
                DomainValidationError(
                    "Volume cannot be negative",
                    details={
                        "amount": amount,
                        "unit": unit.name if hasattr(unit, "name") else unit,
                    },
                )
            )
        return Success(cls(amount=amount, unit=unit))

    def to(
        self, target_unit: VolumeUnit
    ) -> Success["Volume", Exception] | Failure["Volume", Exception]:
        try:
            liters = self.unit.to_standard(self.amount)
            target_amount = target_unit.from_standard(liters)
            return Success(Volume(amount=target_amount, unit=target_unit))
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Volume conversion failed", details={"error": str(exc)}
                )
            )


# --- Dimension ---
class DimensionUnit(Enum):
    METER = ("m", 1.0)
    CENTIMETER = ("cm", 0.01)
    MILLIMETER = ("mm", 0.001)
    INCH = ("in", 0.0254)
    FOOT = ("ft", 0.3048)
    YARD = ("yd", 0.9144)

    @property
    def symbol(self) -> str:
        return self.value[0]

    @property
    def to_meter(self) -> float:
        return self.value[1]

    def to_standard(self, amount: float) -> float:
        return amount * self.to_meter

    def from_standard(self, meters: float) -> float:
        return meters / self.to_meter


class Dimension(ValueObject):
    model_config = ConfigDict(frozen=True)
    amount: float
    unit: DimensionUnit

    @pydantic.field_serializer('unit')
    def serialize_unit(self, unit: DimensionUnit, _info):
        return unit.name

    @pydantic.field_serializer('amount')
    def serialize_amount(self, amount, _info):
        return float(amount)

    @pydantic.model_serializer(mode="plain")
    def serialize_dimension(self):
        return {"amount": float(self.amount), "unit": self.unit.name}

    @classmethod
    def from_value(
        cls, amount: float, unit: DimensionUnit
    ) -> Success["Dimension", Exception] | Failure["Dimension", Exception]:
        if amount < 0:
            return Failure(
                DomainValidationError(
                    "Dimension cannot be negative",
                    details={
                        "amount": amount,
                        "unit": unit.name if hasattr(unit, "name") else unit,
                    },
                )
            )
        return Success(cls(amount=amount, unit=unit))

    def to(
        self, target_unit: DimensionUnit
    ) -> Success["Dimension", Exception] | Failure["Dimension", Exception]:
        try:
            meters = self.unit.to_standard(self.amount)
            target_amount = target_unit.from_standard(meters)
            return Success(Dimension(amount=target_amount, unit=target_unit))
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Dimension conversion failed", details={"error": str(exc)}
                )
            )


# --- Alcohol Content (ABV/Proof) ---
class AlcoholContent(ValueObject):
    abv: float  # canonical, percent (0-100)
    model_config: ClassVar = {"frozen": True}

    @classmethod
    def from_abv(
        cls, abv: float
    ) -> Success["AlcoholContent", Exception] | Failure["AlcoholContent", Exception]:
        if not (0.0 <= abv <= 100.0):
            return Failure(
                DomainValidationError("ABV must be 0-100", details={"abv": abv})
            )
        return Success(cls(abv=abv))

    @classmethod
    def from_proof(
        cls, proof: float, system: str = "US"
    ) -> Success["AlcoholContent", Exception] | Failure["AlcoholContent", Exception]:
        if system == "US":
            abv = proof / 2.0
        elif system == "UK":
            abv = proof * 7.692 / 13.571
        else:
            return Failure(
                DomainValidationError(
                    "Unknown proof system", details={"system": system}
                )
            )
        return cls.from_abv(abv)

    def to_proof(self, system: str = "US") -> float:
        if system == "US":
            return self.abv * 2.0
        elif system == "UK":
            return self.abv * 13.571 / 7.692
        else:
            raise ValueError("Unknown proof system")

    def pretty(self) -> str:
        return f"{self.abv:.2f}% ABV ({self.to_proof():.1f} US proof)"


# --- Quantity (Polymorphic) ---


class Quantity(ValueObject):
    """
    Polymorphic value object for representing quantity as mass, volume, dimension, or count.
    Uno idiomatic discriminated union using Pydantic 2.
    """

    model_config = ConfigDict(
        frozen=True,
        json_encoders={
            Enum: lambda e: e.value,
            # Value objects: use model_dump() for Pydantic models, .value for primitives
            "Count": lambda c: c.model_dump()
            if hasattr(c, "model_dump")
            else c.value
            if hasattr(c, "value")
            else c,
            "Mass": lambda m: m.model_dump()
            if hasattr(m, "model_dump")
            else m.value
            if hasattr(m, "value")
            else m,
            "Volume": lambda v: v.model_dump()
            if hasattr(v, "model_dump")
            else v.value
            if hasattr(v, "value")
            else v,
            "Dimension": lambda d: d.model_dump()
            if hasattr(d, "model_dump")
            else d.value
            if hasattr(d, "value")
            else d,
        },
    )

    type: Literal["mass", "volume", "dimension", "count"]
    value: Mass | Volume | Dimension | Count

    @model_validator(mode="before")
    @classmethod
    def validate_type_and_value(cls, data: dict[str, Any]) -> dict[str, Any]:
        t = data.get("type")
        v = data.get("value")
        if t == "mass" and not isinstance(v, Mass):
            raise ValueError("For type 'mass', value must be Mass")
        if t == "volume" and not isinstance(v, Volume):
            raise ValueError("For type 'volume', value must be Volume")
        if t == "dimension" and not isinstance(v, Dimension):
            raise ValueError("For type 'dimension', value must be Dimension")
        if t == "count" and not isinstance(v, Count):
            raise ValueError("For type 'count', value must be Count")
        return data

    @classmethod
    def from_mass(cls, mass: Mass) -> "Quantity":
        return cls(type="mass", value=mass)

    @classmethod
    def from_volume(cls, volume: Volume) -> "Quantity":
        return cls(type="volume", value=volume)

    @classmethod
    def from_dimension(cls, dimension: Dimension) -> "Quantity":
        return cls(type="dimension", value=dimension)

    @classmethod
    def from_count(cls, count: float | int | Count) -> "Quantity":
        """
        Create a Quantity of type 'count' from a float, int, or Count value.
        Accepts both float and int for compatibility with event replay and domain logic.
        """
        if isinstance(count, Count):
            return cls(type="count", value=count)
        try:
            value = float(count)
        except Exception:
            raise TypeError("Count must be a float or int")
        if value < 0.0:
            raise ValueError("Count must be a non-negative float or int")
        return cls(type="count", value=Count.from_each(value))

    model_config: ClassVar = {"frozen": True}


from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


class Currency(Enum):
    USD = ("USD", "$", 2)
    EUR = ("EUR", "€", 2)
    GBP = ("GBP", "£", 2)
    JPY = ("JPY", "¥", 0)
    CAD = ("CAD", "$", 2)
    AUD = ("AUD", "$", 2)
    CHF = ("CHF", "Fr.", 2)
    # Extend as needed for demo

    @property
    def code(self) -> str:
        return self.value[0]

    @property
    def symbol(self) -> str:
        return self.value[1]

    @property
    def decimals(self) -> int:
        return self.value[2]


class Money(ValueObject):
    amount: Decimal
    currency: Currency
    model_config = ConfigDict(frozen=True)

    @pydantic.field_serializer('amount')
    def serialize_amount(self, amount, _info):
        return float(amount)

    @pydantic.field_serializer('currency')
    def serialize_currency(self, currency: Currency, _info):
        return currency.value

    @pydantic.model_serializer(mode="plain")
    def serialize_money(self):
        return {"amount": float(self.amount), "currency": self.currency.value}

    @classmethod
    def from_value(
        cls, amount: float | str | Decimal, currency: Currency
    ) -> Success["Money", Exception] | Failure["Money", Exception]:
        try:
            dec_amount = Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError) as exc:
            return Failure(
                DomainValidationError(
                    "Invalid amount for Money",
                    details={"amount": amount, "error": str(exc)},
                )
            )
        if dec_amount < 0:
            return Failure(
                DomainValidationError(
                    "Money amount cannot be negative",
                    details={
                        "amount": amount,
                        "unit": currency.name
                        if hasattr(currency, "name")
                        else currency,
                    },
                )
            )
        quantized = cls._quantize(dec_amount, currency)
        return Success(cls(amount=quantized, currency=currency))

    @staticmethod
    def _quantize(amount: Decimal, currency: Currency) -> Decimal:
        decimals = currency.decimals
        quant = Decimal("1") / (Decimal("10") ** decimals)
        return amount.quantize(quant, rounding=ROUND_HALF_UP)

    def pretty(self) -> str:
        decimals = self.currency.decimals
        return f"{self.currency.symbol}{self.amount:,.{decimals}f} {self.currency.code}"

    def to(
        self, target_currency: Currency, fx_rate: float | str | Decimal | None = None
    ) -> Success["Money", Exception] | Failure["Money", Exception]:
        if target_currency == self.currency:
            return Success(self)
        if fx_rate is None:
            return Failure(
                DomainValidationError(
                    "FX rate required for currency conversion",
                    details={"from": self.currency.code, "to": target_currency.code},
                )
            )
        try:
            rate = Decimal(str(fx_rate))
            target_amount = self.amount * rate
            quantized = self._quantize(target_amount, target_currency)
            return Success(Money(amount=quantized, currency=target_currency))
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Money conversion failed", details={"error": str(exc)}
                )
            )


class EmailAddress(ValueObject):
    """
    Value object representing an email address.

    Usage:
        EmailAddress.from_value("user@example.com") -> Success(EmailAddress)
        EmailAddress.from_value("bad-email") -> Failure(DomainValidationError)
    """

    value: EmailStr

    @classmethod
    def from_value(
        cls, value: str
    ) -> Success["EmailAddress", Exception] | Failure["EmailAddress", Exception]:
        """Construct an EmailAddress, returning Success/Failure."""
        try:
            email = cls(value=value)
            return Success(email)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Invalid email address", details={"value": value, "error": str(exc)}
                )
            )

    @classmethod
    def validate(cls, value: str) -> Success[str, Exception] | Failure[str, Exception]:
        """Validate the email address, returning Success/Failure."""
        try:
            EmailStr.validate(value)
            return Success(value)
        except Exception as exc:
            return Failure(
                DomainValidationError(
                    "Invalid email address", details={"value": value, "error": str(exc)}
                )
            )

    model_config: ClassVar = {"frozen": True}
