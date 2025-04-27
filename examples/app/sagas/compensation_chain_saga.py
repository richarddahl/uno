"""
Example CompensationChainSaga: demonstrates multi-step compensation in a Uno saga.
"""
from typing import Any
from uno.core.events.sagas import Saga

class CompensationChainSaga(Saga):
    """
    Orchestrates a process with multiple steps and chained compensations on failure.
    """
    def __init__(self) -> None:
        super().__init__()
        self.data = {
            "step1_completed": False,
            "step2_completed": False,
            "compensated": False,
            "compensation_log": [],
        }
        self.status = "waiting_step1"

    async def handle_event(self, event: Any) -> None:
        if event["type"] == "Step1Completed":
            self.data["step1_completed"] = True
            self.status = "waiting_step2"
        elif event["type"] == "Step2Completed":
            self.data["step2_completed"] = True
            self.status = "completed"
        elif event["type"] == "Step2Failed":
            self.status = "compensating"
            await self.compensate()

    async def compensate(self) -> None:
        # Compensation chain: Step2 compensation, then Step1
        if self.data["step2_completed"]:
            self.data["compensation_log"].append("Compensate Step2")
            self.data["step2_completed"] = False
        if self.data["step1_completed"]:
            self.data["compensation_log"].append("Compensate Step1")
            self.data["step1_completed"] = False
        self.data["compensated"] = True
        self.status = "compensated"

    async def is_completed(self) -> bool:
        return self.status in ("completed", "compensated")
