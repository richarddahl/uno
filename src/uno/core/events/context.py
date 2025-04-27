from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self
from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from uno.core.events.base_event import DomainEvent

class EventHandlerContext(BaseModel):
    """
    Uno canonical Pydantic base model for event handler context objects.

    Canonical serialization contract:
      - Always use `model_dump(exclude_none=True, exclude_unset=True, by_alias=True, sort_keys=True)` for serialization, storage, and transport.
      - Unset and None fields are treated identically; excluded from serialization.
      - This contract is enforced by dedicated tests.
    
    - All model-wide concerns (e.g., validation, serialization) are handled via Pydantic model_config and validators.
    - All type hints use modern Python syntax (str, int, dict[str, Any], Self, etc.).
    - All serialization/deserialization uses Pydantic's built-in methods (`model_dump`, `model_validate`).
    - If broader Python idioms are needed, thin wrappers (e.g., to_dict, from_dict) are provided that simply call the canonical Pydantic methods.
    - This is the **only** pattern permitted for Uno base models.

    Context object passed to event handlers and middleware.
    Encapsulates the event and any relevant metadata for processing.
    """
    event: "DomainEvent"
    metadata: dict[str, Any] = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> dict[str, Any]:
        """
        Canonical serialization: returns dict using Uno contract.
        Uses model_dump(exclude_none=True, exclude_unset=True, by_alias=True).
        """
        return self.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """
        Thin wrapper for Pydantic's `model_validate()`.
        Use this only if a broader Python API is required; otherwise, prefer `model_validate()` directly.
        """
        return cls.model_validate(data)
