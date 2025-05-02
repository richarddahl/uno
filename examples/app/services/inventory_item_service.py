# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Service layer for InventoryItem workflows in Uno.
Implements orchestration, error context propagation, and DI-ready business logic.
"""

from uno.core.errors.definitions import DomainValidationError
from uno.core.errors.result import Failure, Result, Success
from uno.core.logging import LoggerService
from examples.app.domain.inventory.item import InventoryItem
from examples.app.persistence.inventory_item_repository_protocol import (
    InventoryItemRepository,
)


class InventoryItemService:
    """
    Service for InventoryItem workflows.
    Orchestrates domain logic, repository, and error context propagation.
    """

    def __init__(self, repo: InventoryItemRepository, logger: LoggerService) -> None:
        self.repo = repo
        self.logger = logger

    def create_inventory_item(
        self, aggregate_id: str, name: str, quantity: int
    ) -> Result[InventoryItem, Exception]:
        """
        Create a new InventoryItem. Returns Success(InventoryItem) or Failure(DomainValidationError) with error context.
        """
        result = self.repo.get(aggregate_id)
        if not isinstance(result, Failure):
            self.logger.warning(
                {
                    "event": "inventory_item_exists",
                    "aggregate_id": aggregate_id,
                    "service": "InventoryItemService.create_inventory_item",
                }
            )
            return Failure(
                DomainValidationError(
                    f"InventoryItem already exists: {aggregate_id}",
                    details={
                        "aggregate_id": aggregate_id,
                        "service": "InventoryItemService.create_inventory_item",
                    },
                )
            )
        item_result = InventoryItem.create(
            aggregate_id=aggregate_id, name=name, quantity=quantity
        )
        if isinstance(item_result, Failure):
            self.logger.warning(
                {
                    "event": "inventory_item_create_failed",
                    "aggregate_id": aggregate_id,
                    "error": str(item_result.error),
                    "service": "InventoryItemService.create_inventory_item",
                }
            )
            err = item_result.error
            # Attach service context if not already present
            if isinstance(err, DomainValidationError):
                err.details = {
                    **err.details,
                    "aggregate_id": aggregate_id,
                    "service": "InventoryItemService.create_inventory_item",
                }
            return Failure(err)
        item = item_result.unwrap()
        save_result = self.repo.save(item)
        if isinstance(save_result, Failure):
            self.logger.error(
                {
                    "event": "inventory_item_save_failed",
                    "aggregate_id": aggregate_id,
                    "error": str(save_result.error),
                    "service": "InventoryItemService.create_inventory_item",
                }
            )
            err = save_result.error
            return Failure(err)
        self.logger.info(
            {
                "event": "inventory_item_created",
                "aggregate_id": aggregate_id,
                "service": "InventoryItemService.create_inventory_item",
            }
        )
        return Success(item)

    def rename_inventory_item(
        self, aggregate_id: str, new_name: str
    ) -> Result[InventoryItem, Exception]:
        """
        Rename an InventoryItem. Returns Success(InventoryItem) or Failure(DomainValidationError) with error context.
        """
        result = self.repo.get(aggregate_id)
        if isinstance(result, Failure):
            self.logger.warning(
                {
                    "event": "inventory_item_not_found",
                    "aggregate_id": aggregate_id,
                    "service": "InventoryItemService.rename_inventory_item",
                }
            )
            err = result.error
            if isinstance(err, DomainValidationError):
                err.details = {
                    **err.details,
                    "aggregate_id": aggregate_id,
                    "service": "InventoryItemService.rename_inventory_item",
                }
            return Failure(err)
        item = result.value
        rename_result = item.rename(new_name)
        if isinstance(rename_result, Failure):
            self.logger.warning(
                {
                    "event": "inventory_item_rename_failed",
                    "aggregate_id": aggregate_id,
                    "error": str(rename_result.error),
                    "service": "InventoryItemService.rename_inventory_item",
                }
            )
            err = rename_result.error
            if isinstance(err, DomainValidationError):
                err.details = {
                    **err.details,
                    "aggregate_id": aggregate_id,
                    "service": "InventoryItemService.rename_inventory_item",
                }
            return Failure(err)
        save_result = self.repo.save(item)
        if isinstance(save_result, Failure):
            self.logger.error(
                {
                    "event": "inventory_item_save_failed",
                    "aggregate_id": aggregate_id,
                    "error": str(save_result.error),
                    "service": "InventoryItemService.rename_inventory_item",
                }
            )
            err = save_result.error
            return Failure(err)
        self.logger.info(
            {
                "event": "inventory_item_renamed",
                "aggregate_id": aggregate_id,
                "new_name": new_name,
                "service": "InventoryItemService.rename_inventory_item",
            }
        )
        return Success(item)

    def adjust_inventory_quantity(
        self, aggregate_id: str, adjustment: int
    ) -> Result[InventoryItem, Exception]:
        """
        Adjust the quantity of an InventoryItem. Returns Success(InventoryItem) or Failure(DomainValidationError) with error context.
        """
        result = self.repo.get(aggregate_id)
        if isinstance(result, Failure):
            self.logger.warning(
                {
                    "event": "inventory_item_not_found",
                    "aggregate_id": aggregate_id,
                    "service": "InventoryItemService.adjust_inventory_quantity",
                }
            )
            err = result.error
            if isinstance(err, DomainValidationError):
                err.details = {
                    **err.details,
                    "aggregate_id": aggregate_id,
                    "service": "InventoryItemService.adjust_inventory_quantity",
                }
            return Failure(err)
        item = result.value
        adjust_result = item.adjust_quantity(adjustment)
        if isinstance(adjust_result, Failure):
            self.logger.warning(
                {
                    "event": "inventory_item_adjust_failed",
                    "aggregate_id": aggregate_id,
                    "adjustment": adjustment,
                    "error": str(adjust_result.error),
                    "service": "InventoryItemService.adjust_inventory_quantity",
                }
            )
            err = adjust_result.error
            if isinstance(err, DomainValidationError):
                err.details = {
                    **err.details,
                    "aggregate_id": aggregate_id,
                    "adjustment": adjustment,
                    "service": "InventoryItemService.adjust_inventory_quantity",
                }
            return Failure(err)
        save_result = self.repo.save(item)
        if isinstance(save_result, Failure):
            self.logger.error(
                {
                    "event": "inventory_item_save_failed",
                    "aggregate_id": aggregate_id,
                    "adjustment": adjustment,
                    "error": str(save_result.error),
                    "service": "InventoryItemService.adjust_inventory_quantity",
                }
            )
            err = save_result.error
            return Failure(err)
        self.logger.info(
            {
                "event": "inventory_item_quantity_adjusted",
                "aggregate_id": aggregate_id,
                "adjustment": adjustment,
                "service": "InventoryItemService.adjust_inventory_quantity",
            }
        )
        return Success(item)
