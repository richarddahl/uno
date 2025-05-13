"""
Example TimeoutSaga: demonstrates how to implement timeouts and retries in a Uno saga.
"""

from typing import Any

from uno.events.saga_store import SagaState
from uno.events.sagas import Saga

from uno.logging import LoggerProtocol


class TimeoutSaga(Saga):
    """
    Orchestrates a process with a timeout and retry pattern.
    """

    def __init__(self, logger: LoggerProtocol) -> None:
        """
        Args:
            logger: Logger instance (must be injected via DI).
        """
        super().__init__()
        self.data = {
            "step_completed": False,
            "retries": 0,
            "max_retries": 2,
            "timeout_triggered": False,
        }
        self.status = "waiting_step"
        self.logger = logger

    async def handle_event(self, event: Any) -> None:
        try:
            await self.logger.structured_log(
                "INFO",
                f"Saga event received",
                saga_type="TimeoutSaga",
                event_type=event.get("type"),
                status=self.status,
                data=self.data.copy(),
            )
            if event["type"] == "StepCompleted":
                self.data["step_completed"] = True
                self.status = "completed"
                await self.logger.structured_log(
                    "INFO",
                    f"Step completed",
                    status=self.status,
                )
                return
            elif event["type"] == "Timeout":
                self.data["timeout_triggered"] = True
                if self.data["retries"] < self.data["max_retries"]:
                    self.data["retries"] += 1
                    self.status = "waiting_step"
                    await self.logger.structured_log(
                        "INFO",
                        f"Timeout triggered - retrying (attempt {self.data['retries']})",
                        status=self.status,
                    )
                    return
                    # Would dispatch a retry command here
                else:
                    self.status = "failed"
                    await self.logger.structured_log(
                        "ERROR",
                        f"Timeout triggered - max retries ({self.data['max_retries']}) exceeded",
                        status=self.status,
                    )
                    # Delete the saga state when max retries are exceeded
                    raise RuntimeError("Max retries exceeded")
            # Add more event types as needed
        except Exception as e:
            await self.logger.structured_log(
                "ERROR",
                f"Saga event handling failed",
                error=str(e),
                status=self.status,
            )
            raise

    async def is_completed(self) -> bool:
        return self.status in ("completed", "failed")

    def set_state(self, state: SagaState) -> None:
        self.status = state.status
        self.data = state.data.copy()
