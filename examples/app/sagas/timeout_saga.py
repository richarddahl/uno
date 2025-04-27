"""
Example TimeoutSaga: demonstrates how to implement timeouts and retries in a Uno saga.
"""
from typing import Any
from uno.core.events.sagas import Saga

class TimeoutSaga(Saga):
    """
    Orchestrates a process with a timeout and retry pattern.
    """
    def __init__(self) -> None:
        super().__init__()
        self.data = {
            "step_completed": False,
            "retries": 0,
            "max_retries": 2,
            "timeout_triggered": False,
        }
        self.status = "waiting_step"

    async def handle_event(self, event: Any) -> None:
        if event["type"] == "StepCompleted":
            self.data["step_completed"] = True
            self.status = "completed"
        elif event["type"] == "Timeout":
            self.data["timeout_triggered"] = True
            if self.data["retries"] < self.data["max_retries"]:
                self.data["retries"] += 1
                self.status = "waiting_step"
                # Would dispatch a retry command here
            else:
                self.status = "failed"
        # Add more event types as needed

    async def is_completed(self) -> bool:
        return self.status in ("completed", "failed")
