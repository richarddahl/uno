"""
Example EscalationSaga: demonstrates escalation/alerting and human-in-the-loop in Uno sagas.
"""

from typing import Any

from uno.events.saga_store import SagaState
from uno.events.sagas import Saga
from uno.logging import LoggerProtocol


class EscalationSaga(Saga):
    """
    Orchestrates a process with escalation on repeated failure and human approval.
    """

    def __init__(self, logger: LoggerProtocol) -> None:
        """
        Args:
            logger: Logger instance (must be injected via DI).
        """
        super().__init__()
        self.data = {
            "attempts": 0,
            "max_attempts": 2,
            "escalated": False,
            "approved": False,
            "completed": False,
        }
        self.status = "pending"
        self.logger = logger

    async def handle_event(self, event: Any) -> None:
        try:
            self.logger.structured_log(
                "INFO",
                f"Saga event received",
                saga_type="EscalationSaga",
                event_type=event.get("type"),
                status=self.status,
                data=self.data.copy(),
            )
            if event["type"] == "StepFailed":
                self.data["attempts"] += 1
                if self.data["attempts"] > self.data["max_attempts"]:
                    self.status = "escalated"
                    self.data["escalated"] = True
                    self.logger.structured_log(
                        "WARNING",
                        f"Escalation triggered",
                        status=self.status,
                    )
            elif event["type"] == "EscalationApproved":
                self.data["approved"] = True
                self.status = "approved"
                self.logger.structured_log(
                    "INFO",
                    f"Escalation approved",
                    status=self.status,
                )
            elif event["type"] == "StepCompleted":
                self.data["completed"] = True
                self.status = "completed"
                self.logger.structured_log(
                    "INFO",
                    f"Saga completed",
                    status=self.status,
                )
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error handling event: {e}",
                saga_type="EscalationSaga",
                error=str(e),
            )
            raise

    async def is_completed(self) -> bool:
        return self.status in ("completed", "approved")

    def set_state(self, state: SagaState) -> None:
        self.status = state.status
        self.data = state.data.copy()
