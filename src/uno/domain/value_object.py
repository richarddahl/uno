"""
Value object base class for Uno's DDD model.
"""

from __future__ import annotations

from typing import Any, Self

from pydantic import ConfigDict, model_validator

from uno.domain.errors import DomainValidationError
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uno.domain.protocols import ValueObjectProtocol
    from uno.logging.protocols import LoggerProtocol

from uno.core.di import DIContainer
from uno.core.config import Config
from uno.core.logging import LoggerProtocol

class ValueObject:
    """
    Uno idiom: Protocol-based value object template for DDD.

    Required dependencies (injected via constructor):
      - logger: LoggerProtocol (Uno DI)
      - config: Config (Uno DI)

    - DO NOT inherit from this class; instead, implement all required attributes/methods from ValueObjectProtocol directly.
    - Inherit from Pydantic's BaseModel if validation/serialization is needed.
    - This class serves as a template/example only.
    - All type checking should use ValueObjectProtocol, not this class.
    """

    value: object
    logger: LoggerProtocol
    config: Config

    def __init__(self, value: object, logger: LoggerProtocol, config: Config) -> None:
        if not logger or not isinstance(logger, LoggerProtocol):
            raise ValueError("logger (LoggerProtocol) is required via DI")
        if not config or not isinstance(config, Config):
            raise ValueError("config (Config) is required via DI")
        self.value = value
        self.logger = logger
        self.config = config

    def __eq__(self, other: Any) -> bool:
        """
        Value objects are equal if their canonical serialization is equal and type matches.
        """
        return isinstance(other, ValueObjectProtocol) and self.model_dump(
            exclude_none=True, exclude_unset=True, by_alias=True
        ) == other.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)

    def __hash__(self) -> int:
        """
        Hash is based on the canonical serialization contract (Uno standard).
        """
        return hash(
            tuple(
                sorted(
                    self.model_dump(
                        exclude_none=True, exclude_unset=True, by_alias=True
                    ).items()
                )
            )
        )
