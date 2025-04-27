# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Domain model: InventoryItem aggregate and events (vertical slice reference).
Implements Uno canonical serialization, DDD, and event sourcing contracts.
"""
from pydantic import PrivateAttr
from typing import Self
from uno.core.domain.aggregate import AggregateRoot
from uno.core.domain.event import DomainEvent

# --- Events ---
class InventoryItemCreated(DomainEvent):
    item_id: str
    name: str
    quantity: int

class InventoryItemRenamed(DomainEvent):
    item_id: str
    new_name: str

class InventoryItemAdjusted(DomainEvent):
    item_id: str
    adjustment: int  # positive or negative

# --- Aggregate ---
class InventoryItem(AggregateRoot[str]):
    name: str
    quantity: int
    _domain_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    @classmethod
    def create(cls, item_id: str, name: str, quantity: int) -> Self:
        item = cls(id=item_id, name=name, quantity=quantity)
        event = InventoryItemCreated(item_id=item_id, name=name, quantity=quantity)
        item._record_event(event)
        return item

    def rename(self, new_name: str) -> None:
        event = InventoryItemRenamed(item_id=self.id, new_name=new_name)
        self._record_event(event)

    def adjust_quantity(self, adjustment: int) -> None:
        event = InventoryItemAdjusted(item_id=self.id, adjustment=adjustment)
        self._record_event(event)

    def _record_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)
        self._apply_event(event)

    def _apply_event(self, event: DomainEvent) -> None:
        if isinstance(event, InventoryItemCreated):
            self.name = event.name
            self.quantity = event.quantity
        elif isinstance(event, InventoryItemRenamed):
            self.name = event.new_name
        elif isinstance(event, InventoryItemAdjusted):
            self.quantity += event.adjustment
        else:
            raise ValueError(f"Unhandled event: {event}")

    # Canonical serialization already handled by AggregateRoot/Entity base
