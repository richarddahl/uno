"""
Example ParallelStepsSaga: demonstrates fork/join (parallel step) orchestration in Uno sagas.
"""
from typing import Any
from uno.core.events.sagas import Saga

class ParallelStepsSaga(Saga):
    """
    Orchestrates a process where multiple independent steps must complete before proceeding.
    """
    def __init__(self) -> None:
        super().__init__()
        self.data = {
            "step_a_done": False,
            "step_b_done": False,
            "joined": False,
        }
        self.status = "waiting_parallel"

    async def handle_event(self, event: Any) -> None:
        if event["type"] == "StepACompleted":
            self.data["step_a_done"] = True
        elif event["type"] == "StepBCompleted":
            self.data["step_b_done"] = True
        # Join when both are done
        if self.data["step_a_done"] and self.data["step_b_done"]:
            self.data["joined"] = True
            self.status = "joined"
        if event["type"] == "Finalize" and self.data["joined"]:
            self.status = "completed"

    async def is_completed(self) -> bool:
        return self.status == "completed"
