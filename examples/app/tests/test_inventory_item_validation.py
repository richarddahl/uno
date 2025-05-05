"""
Unit tests for the InventoryItem aggregate validate() method.
"""

import pytest

from examples.app.domain.inventory.item import InventoryItem
from examples.app.domain.inventory.measurement import Measurement
from uno.core.errors.result import Failure, Success


def test_inventory_item_validate_domain_invariants():
    # Valid case
    item = InventoryItem(id="I1", name="Widget", measurement=Measurement.from_count(10))
    assert isinstance(item.validate(), Success)

    # Domain invariant: name must not be empty
    item_with_empty_name = InventoryItem(
        id="I1", name="", measurement=Measurement.from_count(10)
    )
    assert isinstance(item_with_empty_name.validate(), Failure)
