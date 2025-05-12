"""
Example CompensationChainSaga: demonstrates multi-step compensation in a Uno saga.
"""

from typing import Any

from uno.events.saga_store import SagaState
from uno.events.sagas import Saga
from uno.logging import LoggerProtocol


class CompensationChainSaga(Saga):
    """
    Orchestrates a process with multiple steps and chained compensations on failure.
    """

    def __init__(self, logger: LoggerProtocol) -> None:
        """
        Args:
            logger: Logger instance (must be injected via DI).
        """
        super().__init__()
        self.data = {
            "step1_completed": False,
            "step2_completed": False,
            "compensated": False,
            "compensation_log": [],
        }
        self.status = "waiting_step1"
        self.logger = logger

    async def handle_event(self, event: Any) -> None:
        try:
            self.logger.structured_log(
                "INFO",
                f"Saga event received",
                saga_type="CompensationChainSaga",
                event_type=event.get("type"),
                status=self.status,
                data=self.data.copy(),
            )
            if event["type"] == "Step1Completed":
                self.data["step1_completed"] = True
                self.status = "waiting_step2"
                self.logger.structured_log(
                    "INFO",
                    f"Step1 completed",
                    status=self.status,
                )
            elif event["type"] == "Step2Completed":
                self.data["step2_completed"] = True
                self.status = "completed"
                self.logger.structured_log(
                    "INFO",
                    f"Step2 completed: saga completed",
                    status=self.status,
                )
            elif event["type"] == "Step2Failed":
                self.status = "compensating"
                self.logger.structured_log(
                    "WARNING",
                    f"Step2 failed: starting compensation",
                    status=self.status,
                )
                await self.compensate()
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error handling event: {e}",
                saga_type="CompensationChainSaga",
                error=str(e),
            )
            raise

    async def compensate(self) -> None:
        self.logger.structured_log(
            "INFO",
            f"Starting compensation chain",
            status=self.status,
        )
        # Compensation chain: Step2 compensation, then Step1
        if self.data["step2_completed"]:
            self.data["compensation_log"].append("Compensate Step2")
            self.data["step2_completed"] = False
        if self.data["step1_completed"]:
            self.data["compensation_log"].append("Compensate Step1")
            self.data["step1_completed"] = False
        self.data["compensated"] = True
        self.status = "compensated"
        self.logger.structured_log(
            "INFO",
            f"Compensation chain complete",
            status=self.status,
        )

    async def is_completed(self) -> bool:
        return self.status in ("completed", "compensated")

    def set_state(self, state: SagaState) -> None:
        self.status = state.status
        self.data = state.data.copy()
