"""
Example ParallelStepsSaga: demonstrates fork/join (parallel step) orchestration in Uno sagas.
"""

from typing import Any

from uno.event_bus.saga_store import SagaState
from uno.event_bus.sagas import Saga
from uno.logging import LoggerProtocol


class ParallelStepsSaga(Saga):
    """
    Orchestrates a process where multiple independent steps must complete before proceeding.
    """

    def __init__(self, logger: LoggerProtocol) -> None:
        """
        Args:
            logger: Logger instance (must be injected via DI).
        """
        super().__init__()
        self.data = {
            "step_a_done": False,
            "step_b_done": False,
            "joined": False,
        }
        self.status = "waiting_parallel"
        self.logger = logger

    async def handle_event(self, event: Any) -> None:

        try:
            await self.logger.structured_log(
                LogLevel.INFO,
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
                    await self.logger.structured_log(
                        LogLevel.INFO,
                        "Steps joined successfully",
                        status=self.status,
                    )
                else:
                    await self.logger.structured_log(
                        LogLevel.ERROR,
                        f"Cannot join: step_a_done={self.data['step_a_done']}, step_b_done={self.data['step_b_done']}",
                        status=self.status,
                    )
            elif event["type"] == "Finalize" and self.data["joined"]:
                self.status = "completed"
                await self.logger.structured_log(
                    LogLevel.INFO,
                    "Saga completed",
                    status=self.status,
                )
        except Exception as e:
            await self.logger.structured_log(
                LogLevel.ERROR,
                f"Error handling event: {e!s}",
                status=self.status,
            )

    async def _handle_step_a_completed(self) -> None:
        self.data["step_a_done"] = True
        await self.logger.structured_log(
            LogLevel.INFO,
            "StepA completed",
            status=self.status,
        )

    async def _handle_step_b_completed(self) -> None:
        self.data["step_b_done"] = True
        await self.logger.structured_log(
            LogLevel.INFO,
            "StepB completed",
            status=self.status,
        )

    async def _handle_step_a_failed(self) -> None:
        self.data["step_a_done"] = False
        await self.logger.structured_log(
            LogLevel.ERROR,
            "StepA failed",
            status=self.status,
        )

    async def _handle_step_b_failed(self) -> None:
        self.data["step_b_done"] = False
        await self.logger.structured_log(
            LogLevel.ERROR,
            "StepB failed",
            status=self.status,
        )

    async def is_completed(self) -> bool:
        return self.status == "completed" and self.data["joined"]

    def set_state(self, state: SagaState) -> None:
        self.status = state.status
        self.data = state.data.copy()
