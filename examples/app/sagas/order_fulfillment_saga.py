"""
Example OrderFulfillmentSaga for Uno: demonstrates stateful, multi-step orchestration with compensation.
"""

from typing import Any

from uno.errors import UnoError
from uno.events.saga_store import SagaState
from uno.events.sagas import Saga
from uno.logging import LoggerProtocol


class OrderFulfillmentSaga(Saga):
    """
    Orchestrates order fulfillment: reserve inventory, process payment, complete or compensate.
    """

    def __init__(self, logger: LoggerProtocol) -> None:
        """
        Args:
            logger: Logger instance (must be injected via DI).
        """
        super().__init__()
        self.steps = ["reserve_inventory", "process_payment", "complete_order"]
        self.current_step = 0
        self.data = {
            "inventory_reserved": False,
            "payment_processed": False,
            "compensated": False,
        }
        self._command_bus = None
        self.logger = logger

    def set_command_bus(self, command_bus) -> None:
        self._command_bus = command_bus

    async def handle_event(self, event: Any) -> None:
        try:
            await self.logger.structured_log(
                "INFO",
                f"Saga event received",
                saga_id=self.saga_id,
                saga_type="OrderFulfillmentSaga",
                event_type=event.get("type"),
                status=self.status,
                data=self.data.copy(),
            )

            if event["type"] == "OrderPlaced":
                self.saga_id = event["order_id"]
                self.status = "waiting_inventory"
                await self.logger.structured_log(
                    "INFO",
                    f"Order placed",
                    status=self.status,
                )
                if self._command_bus:
                    await self._command_bus.dispatch(
                        {"type": "ReserveInventory", "order_id": self.saga_id}
                    )
                return

            elif event["type"] == "InventoryReserved":
                self.data["inventory_reserved"] = True
                self.status = "waiting_payment"
                await self.logger.structured_log(
                    "INFO",
                    f"Inventory reserved",
                    status=self.status,
                )
                if self._command_bus:
                    await self._command_bus.dispatch(
                        {"type": "ProcessPayment", "order_id": self.saga_id}
                    )
                return

            elif event["type"] == "PaymentProcessed":
                self.data["payment_processed"] = True
                self.status = "completed"
                await self.logger.structured_log(
                    "INFO",
                    f"Payment processed",
                    status=self.status,
                )
                return

            elif event["type"] == "PaymentFailed":
                self.status = "compensating"
                await self.logger.structured_log(
                    "ERROR",
                    f"Payment failed: starting compensation",
                    saga_id=self.saga_id,
                    status=self.status,
                )
                await self.compensate()
                raise UnoError(
                    message="Payment failed",
                    code=UnoError.ErrorCode.INTERNAL_ERROR,
                    saga_id=self.saga_id,
                    saga_type="OrderFulfillmentSaga",
                    event_type="PaymentFailed",
                )

            elif event["type"] == "InventoryReservationFailed":
                self.status = "failed"
                await self.logger.structured_log(
                    "ERROR",
                    f"Inventory reservation failed",
                    status=self.status,
                )
                raise UnoError(
                    message="Inventory reservation failed",
                    code=UnoError.ErrorCode.INTERNAL_ERROR,
                    saga_id=self.saga_id,
                    saga_type="OrderFulfillmentSaga",
                    event_type="InventoryReservationFailed",
                )

            # Default return for unrecognized events
            return

        except Exception as e:
            await self.logger.structured_log(
                "ERROR",
                f"Error handling event: {e}",
                saga_id=self.saga_id,
                saga_type="OrderFulfillmentSaga",
                error=str(e),
            )
            raise

    async def compensate(self) -> None:
        await self.logger.structured_log(
            "INFO",
            f"Compensating: releasing inventory",
            saga_id=self.saga_id,
            status=self.status,
        )
        self.data["compensated"] = True
        self.status = "compensated"
        await self.logger.structured_log(
            "INFO",
            f"Compensation complete",
            saga_id=self.saga_id,
            status=self.status,
        )

    async def is_completed(self) -> bool:
        return self.status in ("completed", "compensated")

    def get_state(self) -> SagaState:
        # Save all relevant state
        return SagaState(
            saga_id=self.saga_id or "", status=self.status, data=self.data.copy()
        )

    def set_state(self, state: SagaState) -> None:
        self.saga_id = state.saga_id
        self.status = state.status
        self.data = state.data.copy()
