"""
Canonical event base for Uno's DDD/event sourcing system.
All domain/integration events should inherit from this class.
"""

from __future__ import annotations

import logging
import uuid
import time
import json
import decimal
import enum
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Self

from uno.core.base_model import FrameworkBaseModel
from pydantic import Field, ConfigDict, model_validator

from uno.core.errors.result import Failure, Success

if TYPE_CHECKING:
    import collections.abc
    from uno.core.errors.result import Failure as FailureType, Success as SuccessType
    from uno.core.services.default_hash_service import DefaultHashService
    from uno.core.services.hash_service_protocol import HashServiceProtocol


def uno_json_encoder(obj: Any) -> Any:
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, FrameworkBaseModel):
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            return obj.to_dict()
        return obj.model_dump(
            mode="json", exclude_none=True, exclude_unset=True, by_alias=True
        )
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    raise RuntimeError(
        f"Object of type {type(obj)} is not JSON serializable. Implement to_dict or inherit FrameworkBaseModel."
    )


class DomainEvent(FrameworkBaseModel):
    # --- Event class registry for dynamic resolution ---
    _event_class_registry: ClassVar[dict[str, type["DomainEvent"]]] = {}

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        # Register by class name and event_type if available
        DomainEvent._event_class_registry[cls.__name__] = cls
        event_type = getattr(cls, "event_type", None)
        if event_type and event_type != "domain_event":
            DomainEvent._event_class_registry[event_type] = cls

    @classmethod
    def get_event_class(cls, event_type: str) -> type["DomainEvent"]:
        """
        Look up the event class by event_type or class name.
        Raises KeyError if not found.
        Uno canonical Pydantic base model for all events.

        Canonical serialization and hashing contract (Uno standard):
        - Always use `model_dump(exclude_none=True, exclude_unset=True, by_alias=True, sort_keys=True)` for event serialization, hashing, storage, and transport.
        - Unset and None fields are treated identically; they are excluded from serialization and do not affect event_hash.
        - This contract is enforced by dedicated tests (see test_event_serialization_is_deterministic).

        - All model-wide concerns (e.g., upcasting, hash computation) are handled via @model_validator methods.
        - All type hints use modern Python syntax (str, int, dict[str, Any], Self, etc.).
        - All serialization/deserialization uses Pydantic's built-in methods (`model_dump`, `model_validate`).
        - If broader Python idioms are needed, thin wrappers (e.g., to_dict, from_dict) are provided that simply call the canonical Pydantic methods.
        - This is the **only** pattern permitted for Uno base models.

        Base class for all domain and integration events in Uno.
        Events are immutable and serializable.
        Implements canonical event hash chaining for tamper detection.

        - 'version' is an instance field (serialized with the event)
        - '__version__' is a class-level canonical version (used for upcasting logic)
        - 'event_hash' is computed automatically at creation time (model_validator)
        """
        try:
            return cls._event_class_registry[event_type]
        except KeyError:
            raise RuntimeError(
                f"No DomainEvent class registered for event_type '{event_type}'"
            )

    version: int = 1
    __version__: ClassVar[int] = 1
    event_id: str = Field(default_factory=lambda: "evt_" + uuid.uuid4().hex)
    event_type: ClassVar[str] = "domain_event"
    timestamp: float = Field(default_factory=lambda: time.time())
    correlation_id: str | None = None
    causation_id: str | None = None
    metadata: dict[str, Any] = {}
    previous_hash: str | None = None
    event_hash: str | None = None

    model_config = ConfigDict(
        frozen=True,
        json_encoders={Enum: lambda e: e.value},
    )

    @model_validator(mode="after")
    def _set_event_hash(self) -> Self:
        """
        Pydantic model-wide validator: Compute and set the event_hash field after model creation.
        Uses DI to resolve the hash service (HashServiceProtocol) for compliance and flexibility.
        Falls back to sha256 if DI is not available.

        Returns:
            Self
        """
        from uno.core.services.default_hash_service import DefaultHashService
        from uno.core.services.hash_service_protocol import HashServiceProtocol
        from uno.infrastructure.di import get_service_provider

        d = self.model_dump(
            exclude={"event_hash"},
            exclude_none=True,
            exclude_unset=True,
            by_alias=True,
        )
        payload = json.dumps(
            d, sort_keys=True, separators=(",", ":"), default=uno_json_encoder
        )

        hash_service: HashServiceProtocol | None = None
        try:
            provider = get_service_provider()
            result = provider.try_get_service(HashServiceProtocol)
            if getattr(result, "is_success", False):
                hash_service = getattr(result, "value", None)
        except Exception as exc:
            logging.getLogger("uno.events").warning(
                "Could not resolve HashServiceProtocol from DI: %s. Falling back to DefaultHashService.",
                exc,
            )
        if hash_service is None:
            hash_service = DefaultHashService("sha256")
        object.__setattr__(self, "event_hash", hash_service.compute_hash(payload))
        return self

    def to_dict(self) -> dict[str, Any]:
        """
        Canonical serialization: returns dict using Uno contract.
        Uses model_dump(exclude_none=True, exclude_unset=True, by_alias=True).

        Returns:
            dict[str, Any]: The event as a dict, suitable for serialization or storage.
        """
        return self.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)

    @classmethod
    def from_dict(
        cls, data: dict[str, Any]
    ) -> Success[Self, Exception] | Failure[Self, Exception]:
        """
        Thin wrapper for Pydantic's `model_validate()`. Returns Result for Uno error handling.
        Upcasting and hash computation are handled by model validators.
        Use this only if a broader Python API is required; otherwise, prefer `model_validate()` directly.

        Args:
            data (dict[str, Any]): The event data dict.
        Returns:
            Success[Self, Exception](event) if valid, Failure[Self, Exception](error) otherwise.
        """
        from uno.core.errors.result import Failure, Success

        try:
            return Success[Self, Exception](cls.model_validate(data))
        except Exception as exc:
            return Failure[Self, Exception](
                Exception(f"Failed to create {cls.__name__} from dict: {exc}")
            )

    def validate_event(self) -> Success[None, Exception] | Failure[None, Exception]:
        """
        Validate the event's invariants. Override in subclasses for custom validation.
        Returns:
            Success[None, Exception](None) if valid, Failure[None, Exception](error) otherwise.
        """
        return Success[None, Exception](None)


def verify_event_stream_integrity(events: list[DomainEvent]) -> bool:
    """
    Verify the integrity of a sequence of events using hash chaining.
    Raises ValueError if the chain is broken or tampered with.
    Returns True if the chain is valid.
    """
    if not events:
        return True
    prev_hash = None
    for idx, event in enumerate(events):
        # Recompute hash and compare
        if idx > 0 and event.previous_hash != prev_hash:
            raise ValueError(
                f"Chain broken at index {idx}: previous_hash does not match"
            )
        prev_hash = event.event_hash
    return True


class EventUpcasterRegistry:
    """
    Registry for event upcasters, supporting versioned event migration.
    Usage:
        @EventUpcasterRegistry.register(MyEvent, 1)
        def upcast_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
            ...
        # OR
        EventUpcasterRegistry.register_upcaster(MyEvent, 1, upcast_v1_to_v2)
        migrated = EventUpcasterRegistry.apply(MyEvent, old_data, 1, 2)
    """

    _registry: ClassVar[
        dict[
            tuple[type, int],
            collections.abc.Callable[[dict[str, Any]], dict[str, Any]],
        ]
    ] = {}

    @classmethod
    def register(
        cls, event_type: type, from_version: int
    ) -> collections.abc.Callable[
        [collections.abc.Callable[[dict[str, Any]], dict[str, Any]]],
        collections.abc.Callable[[dict[str, Any]], dict[str, Any]],
    ]:
        def decorator(
            func: collections.abc.Callable[[dict[str, Any]], dict[str, Any]],
        ) -> collections.abc.Callable[[dict[str, Any]], dict[str, Any]]:
            cls._registry[(event_type, from_version)] = func
            return func

        return decorator

    @classmethod
    def register_upcaster(
        cls,
        event_type: type,
        from_version: int,
        upcaster_fn: collections.abc.Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        cls._registry[(event_type, from_version)] = upcaster_fn

    @classmethod
    def apply(
        cls, event_type: type, data: dict[str, Any], from_version: int, to_version: int
    ) -> dict[str, Any]:
        v = from_version
        while v < to_version:
            upcaster = cls._registry.get((event_type, v))
            if not upcaster:
                raise ValueError(
                    f"No upcaster for {event_type.__name__} v{v} -> v{v + 1}"
                )
            data = upcaster(data)
            v += 1
        return data
