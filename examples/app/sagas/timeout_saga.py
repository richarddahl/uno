"""
Example TimeoutSaga: demonstrates how to implement timeouts and retries in a Uno saga.
"""

from typing import Any
from uno.events.sagas import Saga
from uno.errors import Result, Success, Failure
from examples.app.sagas.saga_logging import get_saga_logger
from uno.logging import LoggerProtocol


class TimeoutSaga(Saga):
    """
    Orchestrates a process with a timeout and retry pattern.
    """

    def __init__(self, logger: LoggerProtocol | None = None) -> None:
        """
        Args:
            logger: Optional DI-injected logger. If not provided, uses get_saga_logger().
        """
        super().__init__()
        self.data = {
            "step_completed": False,
            "retries": 0,
            "max_retries": 2,
            "timeout_triggered": False,
        }
        self.status = "waiting_step"
        self.logger = logger or get_saga_logger("timeout")

    async def handle_event(self, event: Any) -> Result[None, str]:
        try:
            self.logger.structured_log(
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
                self.logger.structured_log(
                    "INFO",
                    f"Step completed",
                    status=self.status,
                )
                return Ok(None)
            elif event["type"] == "Timeout":
                self.data["timeout_triggered"] = True
                if self.data["retries"] < self.data["max_retries"]:
                    self.data["retries"] += 1
                    self.status = "waiting_step"
                    self.logger.structured_log(
                        "INFO",
                        f"Timeout triggered - retrying (attempt {self.data['retries']})",
                        status=self.status,
                    )
                    return Success(None)
                    # Would dispatch a retry command here
                else:
                    self.status = "failed"
                    self.logger.structured_log(
                        "ERROR",
                        f"Timeout triggered - max retries ({self.data['max_retries']}) exceeded",
                        status=self.status,
                    )
                    # Delete the saga state when max retries are exceeded
                    return Failure("Max retries exceeded")
            # Add more event types as needed
        except Exception as e:
            self.logger.structured_log(
                "ERROR",
                f"Saga event handling failed",
                error=str(e),
                status=self.status,
            )
            return Failure(f"Event handling failed: {str(e)}")
            raise

    async def is_completed(self) -> bool:
        return self.status in ("completed", "failed")
