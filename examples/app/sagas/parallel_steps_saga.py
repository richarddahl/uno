"""
Example ParallelStepsSaga: demonstrates fork/join (parallel step) orchestration in Uno sagas.
"""

from typing import Any

from examples.app.sagas.saga_logging import get_saga_logger
from uno.events.sagas import Saga
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
                "Saga event received",
                saga_type="ParallelStepsSaga",
                event_type=event.get("type"),
                status=self.status,
                data=self.data.copy(),
            )
            if event["type"] == "StepACompleted":
                await self._handle_step_a_completed()
            elif event["type"] == "StepBCompleted":
                await self._handle_step_b_completed()
            elif event["type"] == "StepAFailed":
                await self._handle_step_a_failed()
            elif event["type"] == "StepBFailed":
                await self._handle_step_b_failed()
            elif event["type"] == "Join":
                if self.data["step_a_done"] and self.data["step_b_done"]:
                    self.data["joined"] = True
                    self.status = "joined"
                    self.logger.structured_log(
                        "INFO",
                        "Steps joined successfully",
                        status=self.status,
                    )
                else:
                    self.logger.structured_log(
                        "ERROR",
                        f"Cannot join: step_a_done={self.data['step_a_done']}, step_b_done={self.data['step_b_done']}",
                        status=self.status,
                    )
            elif event["type"] == "Finalize" and self.data["joined"]:
                self.status = "completed"
                self.logger.structured_log(
                    "INFO",
                    "Saga completed",
                    status=self.status,
                )
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Error handling event: {e!s}",
                status=self.status,
            )

    async def _handle_step_a_completed(self) -> None:
        self.data["step_a_done"] = True
        self.logger.structured_log(
            "INFO",
            "StepA completed",
            status=self.status,
        )

    async def _handle_step_b_completed(self) -> None:
        self.data["step_b_done"] = True
        self.logger.structured_log(
            "INFO",
            "StepB completed",
            status=self.status,
        )

    async def _handle_step_a_failed(self) -> None:
        self.data["step_a_done"] = False
        self.logger.structured_log(
            "ERROR",
            "StepA failed",
            status=self.status,
        )

    async def _handle_step_b_failed(self) -> None:
        self.data["step_b_done"] = False
        self.logger.structured_log(
            "ERROR",
            "StepB failed",
            status=self.status,
        )

    async def is_completed(self) -> bool:
        return self.status == "completed" and self.data["joined"]
