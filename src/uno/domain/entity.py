"""
Entity base class for Uno's DDD model.
"""

from __future__ import annotations
from typing import Any,TypeVar

T_ID = TypeVar("T_ID")


from uno.core.di import DIContainer
from uno.core.config import Config
from uno.core.logging import LoggerProtocol

class Entity:
    """
    Uno idiom: Protocol-based entity template for DDD.

    Required dependencies (injected via constructor):
      - logger: LoggerProtocol (Uno DI)
      - config: Config (Uno DI)

    - DO NOT inherit from this class; instead, implement all required attributes/methods from EntityProtocol directly.
    - Inherit from Pydantic's BaseModel if validation/serialization is needed.
    - This class serves as a template/example only.
    - All type checking should use EntityProtocol, not this class.
    """

    id: object
    logger: LoggerProtocol
    config: Config

    def __init__(self, id: object, logger: LoggerProtocol, config: Config) -> None:
        if not logger or not isinstance(logger, LoggerProtocol):
            raise ValueError("logger (LoggerProtocol) is required via DI")
        if not config or not isinstance(config, Config):
            raise ValueError("config (Config) is required via DI")
        self.id = id
        self.logger = logger
        self.config = config

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Entity) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
