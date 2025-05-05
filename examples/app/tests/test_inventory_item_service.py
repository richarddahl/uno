# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Unit tests for InventoryItemService (Uno example app).
Covers all Result-based success and error paths, including validation and error context propagation.
"""

import pytest

from examples.app.domain.inventory import InventoryItem
from examples.app.persistence.inventory_item_repository_protocol import (
    InventoryItemRepository,
    InventoryItemNotFoundError,
)
from examples.app.services.inventory_item_service import InventoryItemService
from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Success
from uno.infrastructure.logging import LoggerService, LoggingConfig


class FakeInventoryItemRepository(InventoryItemRepository):
    def __init__(self) -> None:
        self._items: dict[str, InventoryItem] = {}

    def get(
        self, aggregate_id: str
    ) -> Success[InventoryItem, None] | Failure[None, InventoryItemNotFoundError]:
        item = self._items.get(aggregate_id)
        if item is None:
            return Failure(InventoryItemNotFoundError(aggregate_id))
        return Success(item)

    def save(
        self, item: InventoryItem
    ) -> Success[None, None] | Failure[None, Exception]:
        self._items[item.id] = item
        return Success(None)

    def all_ids(self) -> list[str]:
        return list(self._items.keys())


@pytest.fixture
def fake_logger() -> LoggerService:
    return LoggerService(LoggingConfig())


@pytest.fixture
def fake_repo() -> FakeInventoryItemRepository:
    return FakeInventoryItemRepository()


@pytest.fixture
def service(
    fake_repo: InventoryItemRepository, fake_logger: LoggerService
) -> InventoryItemService:
    return InventoryItemService(fake_repo, fake_logger)


def test_create_inventory_item_success(service: InventoryItemService) -> None:
    result = service.create_inventory_item("sku-1", "Widget", 5)
    assert isinstance(result, Success)
    item = result.value
    assert item.id == "sku-1"
    assert item.name == "Widget"
    assert item.measurement.value.value == 5


def test_create_inventory_item_duplicate(service: InventoryItemService) -> None:
    service.create_inventory_item("sku-1", "Widget", 5)
    result = service.create_inventory_item("sku-1", "Widget", 5)
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert "already exists" in str(result.error)
    # Error context details
    assert getattr(result.error, "details", None)
    assert result.error.details["aggregate_id"] == "sku-1"
    assert (
        result.error.details["service"] == "InventoryItemService.create_inventory_item"
    )


def test_create_inventory_item_invalid(service: InventoryItemService) -> None:
    result = service.create_inventory_item("sku-2", "", -1)
    assert isinstance(result, Failure)
    # Accept either DomainValidationError or other error, but check for context if present
    if isinstance(result.error, DomainValidationError):
        assert result.error.details["aggregate_id"] == "sku-2"
        assert (
            result.error.details["service"]
            == "InventoryItemService.create_inventory_item"
        )
    else:
        assert "invalid" in str(result.error).lower()


def test_rename_inventory_item_success(service: InventoryItemService) -> None:
    service.create_inventory_item("sku-3", "Widget", 5)
    result = service.rename_inventory_item("sku-3", "Gadget")
    assert isinstance(result, Success)
    assert result.value.name == "Gadget"


def test_rename_inventory_item_not_found(service: InventoryItemService) -> None:
    result = service.rename_inventory_item("sku-404", "Gadget")
    assert isinstance(result, Failure)
    # Check error context details if present
    if isinstance(result.error, DomainValidationError):
        assert result.error.details["aggregate_id"] == "sku-404"
        assert (
            result.error.details["service"]
            == "InventoryItemService.rename_inventory_item"
        )
    else:
        assert "not found" in str(result.error).lower()


def test_rename_inventory_item_invalid(service: InventoryItemService) -> None:
    service.create_inventory_item("sku-4", "Widget", 5)
    result = service.rename_inventory_item("sku-4", "")
    assert isinstance(result, Failure)
    # Accept either DomainValidationError or other error, but check for context if present
    if isinstance(result.error, DomainValidationError):
        assert result.error.details["aggregate_id"] == "sku-4"
        assert (
            result.error.details["service"]
            == "InventoryItemService.rename_inventory_item"
        )
    else:
        assert "invalid" in str(result.error).lower()


def test_adjust_inventory_measurement_success(service: InventoryItemService) -> None:
    service.create_inventory_item("sku-5", "Widget", 5)
    result = service.adjust_inventory_measurement("sku-5", 3)
    assert isinstance(result, Success)
    assert result.value.measurement.value.value == 8


def test_adjust_inventory_measurement_negative(
    service: InventoryItemService,
) -> None:
    result = service.create_inventory_item("sku-6", "Widget", 5)
    assert isinstance(result, Success)
    item = result.value
    assert item.measurement.value.value == 5

    # Adjustment within bounds (should succeed)
    result1 = service.adjust_inventory_measurement("sku-6", -3)
    assert isinstance(result1, Success)
    assert result1.value.measurement.value.value == 2

    # Adjustment to exactly zero (should succeed)
    result2 = service.adjust_inventory_measurement("sku-6", -2)
    assert isinstance(result2, Success)
    assert result2.value.measurement.value.value == 0

    # Adjustment that would make measurement negative (should fail)
    result3 = service.adjust_inventory_measurement("sku-6", -1)
    assert isinstance(result3, Failure)
    assert isinstance(result3.error, DomainValidationError)
    assert result3.error.details["aggregate_id"] == "sku-6"
    assert (
        result3.error.details["service"]
        == "InventoryItemService.adjust_inventory_measurement"
    )
    assert "resulting measurement cannot be negative" in str(result3.error)


def test_adjust_inventory_measurement_invalid(
    service: InventoryItemService,
) -> None:
    service.create_inventory_item("sku-7", "Widget", 5)
    result = service.adjust_inventory_measurement("sku-7", -99)
    assert isinstance(result, Failure)
    assert isinstance(result.error, DomainValidationError)
    assert result.error.details["aggregate_id"] == "sku-7"
    assert (
        result.error.details["service"]
        == "InventoryItemService.adjust_inventory_measurement"
    )
    assert "resulting measurement cannot be negative" in str(result.error)


def test_adjust_inventory_measurement_not_found(
    service: InventoryItemService,
) -> None:
    result = service.adjust_inventory_measurement("sku-404", 1)
    assert isinstance(result, Failure)
    # Check error context details if present
    if isinstance(result.error, DomainValidationError):
        assert result.error.details["aggregate_id"] == "sku-404"
        assert (
            result.error.details["service"]
            == "InventoryItemService.adjust_inventory_measurement"
        )
    else:
        assert "not found" in str(result.error).lower()
