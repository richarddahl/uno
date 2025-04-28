# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Service layer for InventoryItem workflows in Uno.
Implements orchestration, error context propagation, and DI-ready business logic.
"""
from uno.core.errors.result import Result, Success, Failure
from uno.core.errors.definitions import DomainValidationError
from uno.core.logging import LoggerService
from examples.app.domain.inventory_item import InventoryItem
from examples.app.persistence.repository import InMemoryInventoryItemRepository

class InventoryItemService:
    """
    Service for InventoryItem workflows.
    Orchestrates domain logic, repository, and error context propagation.
    """
    def __init__(self, repo: InMemoryInventoryItemRepository, logger: LoggerService) -> None:
        self.repo = repo
        self.logger = logger

    def create_inventory_item(self, item_id: str, name: str, quantity: int) -> Result[InventoryItem, Exception]:
        # Check for existing item
        result = self.repo.get(item_id)
        if not isinstance(result, Failure):
            self.logger.warning(f"InventoryItem already exists: {item_id}")
            return Failure(DomainValidationError(f"InventoryItem already exists: {item_id}", details={"item_id": item_id}))
        # Create domain aggregate
        item_result = InventoryItem.create(item_id=item_id, name=name, quantity=quantity)
        if isinstance(item_result, Failure):
            self.logger.warning(f"Failed to create InventoryItem: {item_id} ({item_result.error})")
            return item_result
        item = item_result.unwrap()
        self.repo.save(item)
        self.logger.info(f"InventoryItem created: {item_id}")
        return Success(item)

    def rename_inventory_item(self, item_id: str, new_name: str) -> Result[InventoryItem, Exception]:
        result = self.repo.get(item_id)
        if isinstance(result, Failure):
            self.logger.warning(f"InventoryItem not found: {item_id}")
            return result
        item = result.value
        rename_result = item.rename(new_name)
        if isinstance(rename_result, Failure):
            self.logger.warning(f"Failed to rename InventoryItem: {item_id} ({rename_result.error})")
            return rename_result
        self.repo.save(item)
        self.logger.info(f"InventoryItem renamed: {item_id} -> {new_name}")
        return Success(item)

    def adjust_inventory_quantity(self, item_id: str, adjustment: int, reason: str | None = None) -> Result[InventoryItem, Exception]:
        result = self.repo.get(item_id)
        if isinstance(result, Failure):
            self.logger.warning(f"InventoryItem not found: {item_id}")
            return result
        item = result.value
        adjust_result = item.adjust_quantity(adjustment, reason=reason)
        if isinstance(adjust_result, Failure):
            self.logger.warning(f"Failed to adjust InventoryItem quantity: {item_id} ({adjust_result.error})")
            return adjust_result
        self.repo.save(item)
        self.logger.info(f"InventoryItem quantity adjusted: {item_id} by {adjustment}")
        return Success(item)

