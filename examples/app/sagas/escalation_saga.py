"""
Example EscalationSaga: demonstrates escalation/alerting and human-in-the-loop in Uno sagas.
"""
from typing import Any
from uno.core.events.sagas import Saga

class EscalationSaga(Saga):
    """
    Orchestrates a process with escalation on repeated failure and human approval.
    """
    def __init__(self) -> None:
        super().__init__()
        self.data = {
            "attempts": 0,
            "max_attempts": 2,
            "escalated": False,
            "approved": False,
            "completed": False,
        }
        self.status = "pending"

    async def handle_event(self, event: Any) -> None:
        if event["type"] == "StepFailed":
            self.data["attempts"] += 1
            if self.data["attempts"] > self.data["max_attempts"]:
                self.status = "escalated"
                self.data["escalated"] = True
        elif event["type"] == "EscalationApproved":
            self.data["approved"] = True
            self.status = "approved"
        elif event["type"] == "StepCompleted":
            self.data["completed"] = True
            self.status = "completed"

    async def is_completed(self) -> bool:
        return self.status in ("completed", "approved")
