# SPDX-FileCopyrightText: 2025-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Service layer for InventoryItem workflows in Uno.
Implements orchestration, error context propagation, and DI-ready business logic.
"""

from uno.domain.errors import DomainValidationError
from examples.app.api.errors import InventoryItemNotFoundError
from uno.logging.protocols import LoggerProtocol
from uno.domain.config import DomainConfig

from examples.app.domain.inventory.item import InventoryItem
from examples.app.persistence.inventory_item_repository_protocol import (
    InventoryItemRepository,
)


class InventoryItemService:
    """
    Service for InventoryItem workflows.
    Orchestrates domain logic, repository, and error context propagation.
    """

    def __init__(
        self,
        repo: InventoryItemRepository,
        logger: LoggerProtocol,
        config: DomainConfig = None,
    ) -> None:
        """
        Initialize the service with its dependencies.

        Args:
            repo: Repository for InventoryItem entities
            logger: Logger for structured logging
            config: Optional domain configuration settings
        """
        self.repo = repo
        self.logger = logger
        self.config = config

    async def create_inventory_item(
        self, aggregate_id: str, name: str, measurement: int
    ) -> InventoryItem:
        """
        Create a new InventoryItem.

        Args:
            aggregate_id: Unique identifier for the inventory item
            name: Name of the inventory item
            measurement: Initial measurement value

        Returns:
            The created InventoryItem

        Raises:
            DomainValidationError: If validation fails or item already exists
        """
        # Check if item already exists
        existing_item = await self.repo.get(aggregate_id)

        if existing_item:
            await self.logger.warning(
                "Inventory item already exists",
                aggregate_id=aggregate_id,
                service="InventoryItemService.create_inventory_item",
            )

            raise DomainValidationError(
                message=f"InventoryItem already exists: {aggregate_id}",
                details={
                    "aggregate_id": aggregate_id,
                    "service": "InventoryItemService.create_inventory_item",
                },
            )

        # Create the new item
        try:
            item = await InventoryItem(
                aggregate_id=aggregate_id, name=name, measurement=measurement
            )

            # Save the item
            await self.repo.save(item)

            await self.logger.info(
                "Inventory item created",
                aggregate_id=aggregate_id,
                name=name,
                measurement=measurement,
                service="InventoryItemService.create_inventory_item",
            )

            return item

        except DomainValidationError as error:
            # Log the error with context
            await self.logger.warning(
                "Failed to create inventory item",
                aggregate_id=aggregate_id,
                error=str(error),
                service="InventoryItemService.create_inventory_item",
            )

            # Add service context if not already present
            if hasattr(error, "details"):
                error.details.update(
                    {
                        "aggregate_id": aggregate_id,
                        "service": "InventoryItemService.create_inventory_item",
                    }
                )

            raise
        except Exception as error:
            # Log unexpected errors
            await self.logger.error(
                "Unexpected error creating inventory item",
                aggregate_id=aggregate_id,
                error=str(error),
                service="InventoryItemService.create_inventory_item",
                exc_info=error,
            )

            # Wrap in domain error
            raise DomainValidationError(
                message=f"Failed to create inventory item: {error}",
                details={
                    "aggregate_id": aggregate_id,
                    "service": "InventoryItemService.create_inventory_item",
                },
            ) from error

    async def rename_inventory_item(
        self, aggregate_id: str, new_name: str
    ) -> InventoryItem:
        """
        Rename an InventoryItem.

        Args:
            aggregate_id: ID of the inventory item to rename
            new_name: New name for the inventory item

        Returns:
            The updated InventoryItem

        Raises:
            InventoryItemNotFoundError: If the item doesn't exist
            DomainValidationError: If validation fails
        """
        # Get the item
        item = await self.repo.get(aggregate_id)

        if not item:
            await self.logger.warning(
                "Inventory item not found",
                aggregate_id=aggregate_id,
                service="InventoryItemService.rename_inventory_item",
            )

            raise InventoryItemNotFoundError(
                entity_type="InventoryItem",
                entity_id=aggregate_id,
                service="InventoryItemService.rename_inventory_item",
            )

        try:
            # Rename the item
            item.rename(new_name)

            # Save the updated item
            await self.repo.save(item)

            await self.logger.info(
                "Inventory item renamed",
                aggregate_id=aggregate_id,
                new_name=new_name,
                service="InventoryItemService.rename_inventory_item",
            )

            return item

        except DomainValidationError as error:
            # Log the error with context
            await self.logger.warning(
                "Failed to rename inventory item",
                aggregate_id=aggregate_id,
                new_name=new_name,
                error=str(error),
                service="InventoryItemService.rename_inventory_item",
            )

            # Add service context if not already present
            if hasattr(error, "details"):
                error.details.update(
                    {
                        "aggregate_id": aggregate_id,
                        "service": "InventoryItemService.rename_inventory_item",
                    }
                )

            raise
        except Exception as error:
            # Log unexpected errors
            await self.logger.error(
                "Unexpected error renaming inventory item",
                aggregate_id=aggregate_id,
                new_name=new_name,
                error=str(error),
                service="InventoryItemService.rename_inventory_item",
                exc_info=error,
            )

            # Wrap in domain error
            raise DomainValidationError(
                message=f"Failed to rename inventory item: {error}",
                details={
                    "aggregate_id": aggregate_id,
                    "service": "InventoryItemService.rename_inventory_item",
                },
            ) from error

    async def adjust_inventory_measurement(
        self, aggregate_id: str, adjustment: int
    ) -> InventoryItem:
        """
        Adjust the measurement of an InventoryItem.

        Args:
            aggregate_id: ID of the inventory item to adjust
            adjustment: Amount to adjust the measurement by (positive or negative)

        Returns:
            The updated InventoryItem

        Raises:
            InventoryItemNotFoundError: If the item doesn't exist
            DomainValidationError: If validation fails
        """
        # Get the item
        item = await self.repo.get(aggregate_id)

        if not item:
            await self.logger.warning(
                "Inventory item not found",
                aggregate_id=aggregate_id,
                service="InventoryItemService.adjust_inventory_measurement",
            )

            raise InventoryItemNotFoundError(
                entity_type="InventoryItem",
                entity_id=aggregate_id,
                service="InventoryItemService.adjust_inventory_measurement",
            )

        try:
            # Apply configuration-based rules if available
            if (
                self.config
                and hasattr(self.config, "strict_validation")
                and self.config.strict_validation
            ):
                # In strict validation mode, don't allow negative adjustments that would result in negative inventory
                if adjustment < 0 and (item.measurement + adjustment) < 0:
                    raise DomainValidationError(
                        message="Adjustment would result in negative inventory",
                        details={
                            "aggregate_id": aggregate_id,
                            "current_measurement": item.measurement,
                            "adjustment": adjustment,
                            "service": "InventoryItemService.adjust_inventory_measurement",
                        },
                    )

            # Adjust the measurement
            item.adjust_measurement(adjustment)

            # Save the updated item
            await self.repo.save(item)

            await self.logger.info(
                "Inventory measurement adjusted",
                aggregate_id=aggregate_id,
                adjustment=adjustment,
                new_measurement=item.measurement,
                service="InventoryItemService.adjust_inventory_measurement",
            )

            return item

        except DomainValidationError as error:
            # Log the error with context
            await self.logger.warning(
                "Failed to adjust inventory measurement",
                aggregate_id=aggregate_id,
                adjustment=adjustment,
                error=str(error),
                service="InventoryItemService.adjust_inventory_measurement",
            )

            # Add service context if not already present
            if hasattr(error, "details"):
                error.details.update(
                    {
                        "aggregate_id": aggregate_id,
                        "service": "InventoryItemService.adjust_inventory_measurement",
                    }
                )

            raise
        except Exception as error:
            # Log unexpected errors
            await self.logger.error(
                "Unexpected error adjusting inventory measurement",
                aggregate_id=aggregate_id,
                adjustment=adjustment,
                error=str(error),
                service="InventoryItemService.adjust_inventory_measurement",
                exc_info=error,
            )

            # Wrap in domain error
            raise DomainValidationError(
                message=f"Failed to adjust inventory measurement: {error}",
                details={
                    "aggregate_id": aggregate_id,
                    "adjustment": adjustment,
                    "service": "InventoryItemService.adjust_inventory_measurement",
                },
            ) from error
