"""
Example OrderFulfillmentSaga for Uno: demonstrates stateful, multi-step orchestration with compensation.
"""

from typing import Any

from uno.core.events.saga_store import SagaState
from uno.core.events.sagas import Saga


class OrderFulfillmentSaga(Saga):
    """
    Orchestrates order fulfillment: reserve inventory, process payment, complete or compensate.
    """

    def __init__(self) -> None:
        super().__init__()
        self.steps = ["reserve_inventory", "process_payment", "complete_order"]
        self.current_step = 0
        self.data = {
            "inventory_reserved": False,
            "payment_processed": False,
            "compensated": False,
        }
        self._command_bus = None

    def set_command_bus(self, command_bus) -> None:
        self._command_bus = command_bus

    async def handle_event(self, event: Any) -> None:
        # Simulate event routing and step transitions
        if event["type"] == "OrderPlaced":
            self.saga_id = event["order_id"]
            self.status = "waiting_inventory"
            if self._command_bus:
                await self._command_bus.dispatch({
                    "type": "ReserveInventory",
                    "order_id": self.saga_id
                })
        elif event["type"] == "InventoryReserved":
            self.data["inventory_reserved"] = True
            self.status = "waiting_payment"
            if self._command_bus:
                await self._command_bus.dispatch({
                    "type": "ProcessPayment",
                    "order_id": self.saga_id
                })
        elif event["type"] == "PaymentProcessed":
            self.data["payment_processed"] = True
            self.status = "completed"
        elif event["type"] == "PaymentFailed":
            self.status = "compensating"
            await self.compensate()
        # Add more event types as needed

    async def compensate(self) -> None:
        # Compensating action: release inventory
        self.data["compensated"] = True
        self.status = "compensated"

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
