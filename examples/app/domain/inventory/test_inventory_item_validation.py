"""
Unit tests for the InventoryItem aggregate validate() method.
"""

import pytest

from examples.app.domain.inventory.item import InventoryItem
from examples.app.domain.value_objects import Quantity
from uno.core.errors.result import Failure, Success


def test_inventory_item_validate_domain_invariants():
    # Valid case
    item = InventoryItem(id="I1", name="Widget", quantity=Quantity.from_count(10))
    assert isinstance(item.validate(), Success)

    # Domain invariant: name must not be empty
    item_with_empty_name = InventoryItem(
        id="I1", name="", quantity=Quantity.from_count(10)
    )
    assert isinstance(item_with_empty_name.validate(), Failure)
