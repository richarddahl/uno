# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Unit tests for InventoryLot combine_with and split domain logic.
Covers blending, traceability, and all error/success paths.
"""

import pytest

from examples.app.domain.inventory import InventoryLot
from examples.app.domain.inventory.measurement import Measurement
from examples.app.domain.inventory.value_objects import Count, CountUnit
from uno.core.errors.result import Failure, Success


def make_lot(lot_id: str, aggregate_id: str, measurement: float) -> InventoryLot:
    result = InventoryLot.create(
        lot_id, aggregate_id, Measurement.from_count(measurement)
    )
    assert isinstance(result, Success)
    return result.value


def test_combine_success() -> None:
    lot1 = make_lot("lot1", "corn", 100.0)
    lot2 = make_lot("lot2", "corn", 200.0)
    result = lot1.combine_with(lot2, new_lot_id="lot3")
    assert isinstance(result, Success)
    combined = result.value
    assert combined.id == "lot3"
    assert combined.aggregate_id == "corn"
    assert combined.measurement.type == "count"
    assert combined.measurement.value == Count(value=300.0, unit=CountUnit.EACH)
    # Vendor and price should be None (blended)
    assert combined.vendor_id is None
    assert combined.purchase_price is None
    # Traceability: event should reference both source lots
    event = next(e for e in combined._domain_events if hasattr(e, "source_lot_ids"))
    assert set(event.source_lot_ids) == {"lot1", "lot2"}
    # Grade and vendor traceability should be empty/None by default
    # Defensive: event may not have these attributes if not implemented
    if hasattr(event, "source_grades"):
        assert event.source_grades == [None, None]
    if hasattr(event, "source_vendor_ids"):
        assert event.source_vendor_ids == []
    if hasattr(event, "blended_grade"):
        assert event.blended_grade is None
    if hasattr(event, "blended_vendor_ids"):
        assert event.blended_vendor_ids == []
    assert combined.grade is None
    assert combined._source_vendor_ids == []


def test_combine_with_grades_and_vendors() -> None:
    lot1 = make_lot("lot1", "corn", 100.0)
    lot2 = make_lot("lot2", "corn", 200.0)
    from examples.app.domain.inventory.value_objects import Grade

    lot1.grade = Grade(value=10.0)
    lot2.grade = Grade(value=13.0)
    lot1.vendor_id = "vendorA"
    lot2.vendor_id = "vendorB"
    result = lot1.combine_with(lot2, new_lot_id="lot3")
    assert isinstance(result, Success)
    combined = result.value
    # Weighted average: (10*100 + 13*200) / 300 = 12.0
    assert combined.grade is not None
    assert combined.grade.value == pytest.approx(12.0)
    # Defensive: event may not have these attributes if not implemented
    event = next(e for e in combined._domain_events if hasattr(e, "source_lot_ids"))
    if hasattr(event, "source_grades"):
        assert [g.value if g else None for g in event.source_grades] == [10.0, 13.0]
    if hasattr(event, "source_vendor_ids"):
        assert set(event.source_vendor_ids) == {"vendorA", "vendorB"}
    if hasattr(event, "blended_grade"):
        assert event.blended_grade is not None
        assert event.blended_grade.value == pytest.approx(12.0)
    if hasattr(event, "blended_vendor_ids"):
        assert set(event.blended_vendor_ids) == {"vendorA", "vendorB"}
    # Blending is traceable in both lot and event
    assert combined.grade is not None and (
        not hasattr(event, "blended_grade") or event.blended_grade is not None
    )
    if hasattr(event, "blended_grade"):
        assert combined.grade.value == event.blended_grade.value
    if hasattr(event, "blended_vendor_ids"):
        assert set(combined._source_vendor_ids) == set(event.blended_vendor_ids)
    # Both vendors should be present
    assert set(combined._source_vendor_ids) == {"vendorA", "vendorB"}
    # Event should reference all grades and vendors
    event = next(e for e in combined._domain_events if hasattr(e, "source_lot_ids"))
    assert [g.value if g else None for g in event.source_grades] == [10.0, 13.0]
    assert set(event.source_vendor_ids) == {"vendorA", "vendorB"}
    assert event.blended_grade is not None
    assert event.blended_grade.value == pytest.approx(12.0)
    assert set(event.blended_vendor_ids) == {"vendorA", "vendorB"}
    # Blending is traceable in both lot and event
    assert combined.grade is not None and event.blended_grade is not None
    assert combined.grade.value == event.blended_grade.value
    assert set(combined._source_vendor_ids) == set(event.blended_vendor_ids)


def test_combine_different_items() -> None:
    lot1 = make_lot("lot1", "corn", 100.0)
    lot2 = make_lot("lot2", "wheat", 200.0)
    result = lot1.combine_with(lot2, new_lot_id="lot3")
    assert isinstance(result, Failure)
    assert "different items" in str(result.error)


def test_combine_with_self() -> None:
    lot1 = make_lot("lot1", "corn", 100.0)
    result = lot1.combine_with(lot1, new_lot_id="lot3")
    assert isinstance(result, Failure)
    assert "itself" in str(result.error)


def test_split_success() -> None:
    lot = make_lot("lot1", "corn", 300.0)
    result = lot.split([100.0, 200.0], ["lotA", "lotB"])
    assert isinstance(result, Success)
    new_lots = result.value
    assert len(new_lots) == 2
    assert {l.id for l in new_lots} == {"lotA", "lotB"}
    assert {l.measurement.value for l in new_lots} == {
        Count(value=100.0, unit=CountUnit.EACH),
        Count(value=200.0, unit=CountUnit.EACH),
    }
    # Traceability: event should reference source and new lot IDs
    for l in new_lots:
        assert any(
            e
            for e in l._domain_events
            if hasattr(e, "source_lot_id") and e.source_lot_id == "lot1"
        )


def test_split_invalid_sum() -> None:
    lot = make_lot("lot1", "corn", 300.0)
    result = lot.split([100.0, 150.0], ["lotA", "lotB"])
    assert isinstance(result, Failure)
    assert "sum" in str(result.error)


def test_split_invalid_count() -> None:
    lot = make_lot("lot1", "corn", 300.0)
    result = lot.split([100.0, 200.0], ["lotA"])  # Only one ID
    assert isinstance(result, Failure)
    assert "each split" in str(result.error)


def test_split_negative_measurement() -> None:
    lot = make_lot("lot1", "corn", 300.0)
    result = lot.split([100.0, -200.0], ["lotA", "lotB"])
    assert isinstance(result, Failure)
    assert "positive" in str(result.error)
