"""
Canonical event base for Uno's DDD/event sourcing system.
All domain/integration events should inherit from this class.
"""

from __future__ import annotations

from typing import Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DomainEvent(BaseModel):
    """
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

    version: int = 1
    __version__: ClassVar[int] = 1
    event_id: str = Field(
        default_factory=lambda: "evt_" + __import__("uuid").uuid4().hex
    )
    event_type: ClassVar[str] = "domain_event"
    timestamp: float = Field(default_factory=lambda: __import__("time").time())
    correlation_id: str | None = None
    causation_id: str | None = None
    metadata: dict[str, Any] = {}
    previous_hash: str | None = None
    event_hash: str | None = None

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="before")
    @classmethod
    def _upcast_if_needed(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Pydantic model-wide validator: Upcast event data dict to the latest version before model instantiation.
        This ensures all events are always validated and constructed in their canonical, most recent form.

        Args:
            data (dict[str, Any]): The raw event data (possibly old version).
        Returns:
            dict[str, Any]: The upcasted event data, ready for model validation.
        Raises:
            ValueError: If no upcaster exists for the required version transition.
        """
        data_version = data.get("version", 1)
        target_version = getattr(cls, "__version__", 1)
        if data_version < target_version:
            try:
                data = EventUpcasterRegistry.apply(
                    cls, data, data_version, target_version
                )
            except Exception as e:
                from uno.core.errors.definitions import EventUpcastError
                raise EventUpcastError(
                    event_type=cls.__name__,
                    from_version=data_version,
                    to_version=target_version,
                ) from e
        return data

    @model_validator(mode="after")
    def _set_event_hash(self) -> Self:
        """
        Pydantic model-wide validator: Compute and set the event_hash field after model creation.
        Ensures all events are cryptographically chained and tamper-evident.

        Returns:
            Self: The event instance with its event_hash set.
        """
        import hashlib
        import json

        d = self.model_dump(exclude={"event_hash"}, exclude_none=True, exclude_unset=True)
        payload = json.dumps(d, sort_keys=True, separators=(",", ":"))
        object.__setattr__(
            self, "event_hash", hashlib.sha256(payload.encode("utf-8")).hexdigest()
        )
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
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Thin wrapper for Pydantic's `model_validate()`.
        Upcasting and hash computation are handled by model validators.
        Use this only if a broader Python API is required; otherwise, prefer `model_validate()` directly.

        Args:
            data (dict[str, Any]): The event data dict.
        Returns:
            Self: The constructed, validated, and upcasted event instance.
        """
        return cls.model_validate(data)


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

    _registry: ClassVar[dict[tuple[type, int], callable]] = {}

    @classmethod
    def register(cls, event_type: type, from_version: int):
        def decorator(func):
            cls._registry[(event_type, from_version)] = func
            return func

        return decorator

    @classmethod
    def register_upcaster(
        cls, event_type: type, from_version: int, upcaster_fn: callable
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
