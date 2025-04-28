"""
Example OrderFulfillmentSaga for Uno: demonstrates stateful, multi-step orchestration with compensation.
"""

from typing import Any

from uno.core.events.saga_store import SagaState
from uno.core.events.sagas import Saga
from examples.app.sagas.saga_logging import get_saga_logger
from uno.core.logging import LoggerService


class OrderFulfillmentSaga(Saga):
    """
    Orchestrates order fulfillment: reserve inventory, process payment, complete or compensate.
    """

    def __init__(self, logger: LoggerService | None = None) -> None:
        """
        Args:
            logger: Optional DI-injected logger. If not provided, uses get_saga_logger().
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
        self.logger = logger or get_saga_logger("order_fulfillment")

    def set_command_bus(self, command_bus) -> None:
        self._command_bus = command_bus

    async def handle_event(self, event: Any) -> None:
        try:
            self.logger.structured_log(
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
                self.logger.structured_log(
                    "INFO",
                    f"OrderPlaced: dispatching ReserveInventory",
                    saga_id=self.saga_id,
                    status=self.status,
                )
                if self._command_bus:
                    await self._command_bus.dispatch({
                        "type": "ReserveInventory",
                        "order_id": self.saga_id
                    })
            elif event["type"] == "InventoryReserved":
                self.data["inventory_reserved"] = True
                self.status = "waiting_payment"
                self.logger.structured_log(
                    "INFO",
                    f"InventoryReserved: dispatching ProcessPayment",
                    saga_id=self.saga_id,
                    status=self.status,
                )
                if self._command_bus:
                    await self._command_bus.dispatch({
                        "type": "ProcessPayment",
                        "order_id": self.saga_id
                    })
            elif event["type"] == "PaymentProcessed":
                self.data["payment_processed"] = True
                self.status = "completed"
                self.logger.structured_log(
                    "INFO",
                    f"PaymentProcessed: saga completed",
                    saga_id=self.saga_id,
                    status=self.status,
                )
            elif event["type"] == "PaymentFailed":
                self.status = "compensating"
                self.logger.structured_log(
                    "WARNING",
                    f"PaymentFailed: starting compensation",
                    saga_id=self.saga_id,
                    status=self.status,
                )
                await self.compensate()
            # Add more event types as needed
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error handling event: {e}",
                saga_id=self.saga_id,
                saga_type="OrderFulfillmentSaga",
                error=str(e),
            )
            raise

    async def compensate(self) -> None:
        self.logger.structured_log(
            "INFO",
            f"Compensating: releasing inventory",
            saga_id=self.saga_id,
            status=self.status,
        )
        self.data["compensated"] = True
        self.status = "compensated"
        self.logger.structured_log(
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

    def load_state(self, state: SagaState) -> None:
        self.saga_id = state.saga_id
        self.status = state.status
        self.data = state.data.copy()
