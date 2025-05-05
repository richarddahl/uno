# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Unit tests for InventoryItemCreated event (Uno example app).
Covers Result-based construction, error context, versioning, and upcast behavior.
"""

import pytest

from examples.app.domain.inventory import (
    InventoryItemAdjusted,
    InventoryItemCreated,
    InventoryItemRenamed,
)
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Success


def test_inventory_item_created_create_success() -> None:
    result = InventoryItemCreated.create(
        aggregate_id="sku-123",
        name="Widget",
        measurement=10,
    )
    assert isinstance(result, Success)
    event = result.value
    assert event.aggregate_id == "sku-123"
    assert event.name == "Widget"
    assert event.measurement.value.value == 10
    assert event.version == 1


def test_inventory_item_created_create_failure_missing_aggregate_id() -> None:
    result = InventoryItemCreated.create(
        aggregate_id="",
        name="Widget",
        measurement=10,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "aggregate_id" in result.error.details


def test_inventory_item_created_create_failure_missing_name() -> None:
    result = InventoryItemCreated.create(
        aggregate_id="sku-123",
        name="",
        measurement=10,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "name" in result.error.details


def test_inventory_item_created_create_failure_invalid_measurement() -> None:
    result = InventoryItemCreated.create(
        aggregate_id="sku-123",
        name="Widget",
        measurement=-1,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "measurement" in result.error.details


def test_inventory_item_created_upcast_identity() -> None:
    result = InventoryItemCreated.create(
        aggregate_id="sku-123",
        name="Widget",
        measurement=10,
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(event.version)
    assert isinstance(upcast_result, Success)
    assert upcast_result.value is event


def test_inventory_item_created_upcast_unimplemented() -> None:
    result = InventoryItemCreated.create(
        aggregate_id="sku-123",
        name="Widget",
        measurement=10,
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(99)
    assert isinstance(upcast_result, Failure)
    assert isinstance(upcast_result.error, DomainValidationError)
    assert upcast_result.error.details["from"] == 1
    assert upcast_result.error.details["to"] == 99


def test_inventory_item_adjusted_create_success() -> None:
    result = InventoryItemAdjusted.create(
        aggregate_id="sku-123",
        adjustment=5,
    )
    assert isinstance(result, Success)
    event = result.value
    assert event.aggregate_id == "sku-123"
    assert event.adjustment == 5
    assert event.version == 1


def test_inventory_item_adjusted_create_failure_missing_aggregate_id() -> None:
    result = InventoryItemAdjusted.create(
        aggregate_id="",
        adjustment=5,
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "aggregate_id" in result.error.details


def test_inventory_item_adjusted_create_failure_invalid_adjustment() -> None:
    result = InventoryItemAdjusted.create(
        aggregate_id="sku-123",
        adjustment="not-an-int",
    )
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "adjustment" in result.error.details


def test_inventory_item_adjusted_upcast_identity() -> None:
    result = InventoryItemAdjusted.create(
        aggregate_id="sku-123",
        adjustment=5,
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(event.version)
    assert isinstance(upcast_result, Success)
    assert upcast_result.value is event


def test_inventory_item_adjusted_upcast_unimplemented() -> None:
    result = InventoryItemAdjusted.create(
        aggregate_id="sku-123",
        adjustment=5,
    )
    assert isinstance(result, Success)
    event = result.value
    upcast_result = event.upcast(99)
    assert isinstance(upcast_result, Failure)
    assert isinstance(upcast_result.error, DomainValidationError)
    assert upcast_result.error.details["from"] == 1
    assert upcast_result.error.details["to"] == 99
