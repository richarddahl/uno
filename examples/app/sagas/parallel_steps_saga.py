"""
Example ParallelStepsSaga: demonstrates fork/join (parallel step) orchestration in Uno sagas.
"""

from typing import Any
from uno.core.events.sagas import Saga
from examples.app.sagas.saga_logging import get_saga_logger
from uno.infrastructure.logging import LoggerService


class ParallelStepsSaga(Saga):
    """
    Orchestrates a process where multiple independent steps must complete before proceeding.
    """

    def __init__(self, logger: LoggerService | None = None) -> None:
        """
        Args:
            logger: Optional DI-injected logger. If not provided, uses get_saga_logger().
        """
        super().__init__()
        self.data = {
            "step_a_done": False,
            "step_b_done": False,
            "joined": False,
        }
        self.status = "waiting_parallel"
        self.logger = logger or get_saga_logger("parallel_steps")

    async def handle_event(self, event: Any) -> None:
        try:
            self.logger.structured_log(
                "INFO",
                f"Saga event received",
                saga_type="ParallelStepsSaga",
                event_type=event.get("type"),
                status=self.status,
                data=self.data.copy(),
            )
            if event["type"] == "StepACompleted":
                self.data["step_a_done"] = True
                self.logger.structured_log(
                    "INFO",
                    f"StepA completed",
                    status=self.status,
                )
            elif event["type"] == "StepBCompleted":
                self.data["step_b_done"] = True
                self.logger.structured_log(
                    "INFO",
                    f"StepB completed",
                    status=self.status,
                )
            # Join when both are done
            if (
                self.data["step_a_done"]
                and self.data["step_b_done"]
                and not self.data["joined"]
            ):
                self.data["joined"] = True
                self.status = "joined"
                self.logger.structured_log(
                    "INFO",
                    f"Parallel steps joined",
                    status=self.status,
                )
            if event["type"] == "Finalize" and self.data["joined"]:
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
                saga_type="ParallelStepsSaga",
                error=str(e),
            )
            raise

    async def is_completed(self) -> bool:
        return self.status == "completed"
