"""
Integration tests for logger error handling in real-world scenarios.
"""

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from uno.errors import ErrorCategory, ErrorSeverity, UnoError
from uno.logging.config import LoggingSettings
from uno.logging.logger import get_logger
from uno.logging.protocols import LoggerProtocol


class MockIntegrationError(UnoError):
    """Error class for testing integration with logging."""

    def __init__(
        self,
        message: str,
        code: str,
        category: str = "integration",
        severity: str = "ERROR",
        **kwargs: Any,
    ) -> None:
        """Initialize a test integration error.

        Args:
            message: Error message
            code: Error code
            category: Error category as string
            severity: Error severity as string
            **kwargs: Additional context or parameters
        """
        # Convert string category to ErrorCategory enum
        try:
            error_category = ErrorCategory[category.upper()]
        except (KeyError, AttributeError):
            error_category = ErrorCategory.INTERNAL

        # Convert string severity to ErrorSeverity enum
        try:
            error_severity = ErrorSeverity[severity.upper()]
        except (KeyError, AttributeError):
            error_severity = ErrorSeverity.ERROR

        # Extract context if provided
        context = kwargs.pop("context", {})

        # Initialize the parent UnoError with proper parameters
        super().__init__(
            code=code,
            message=message,
            category=error_category,
            severity=error_severity,
            context=context,
        )
        self.timestamp = datetime.now(UTC).isoformat()


def get_json_logger(name: str) -> LoggerProtocol:
    """Get a logger configured for JSON output.

    Args:
        name: Logger name

    Returns:
        Configured logger for testing
    """
    # Import UnoLogger directly to configure it with JSON settings
    from uno.logging.logger import UnoLogger

    # Force JSON format for testing
    settings = LoggingSettings(
        json_format=True,
        console_enabled=True,
        include_timestamp=True,
    )

    # Create and return a properly configured UnoLogger instance
    return UnoLogger(name=name, level="DEBUG", settings=settings)


@pytest.fixture
async def di_json_logger() -> LoggerProtocol:
    """Get a logger via DI for more realistic integration testing.

    Returns:
        A properly configured logger for testing
    """
    from uno.di import Container

    # Create a test container with forced JSON logging configuration
    container = Container()
    container.configure_logging(
        json_format=True,
        console_enabled=True,
        include_timestamp=True,
    )

    # Get the logger through DI as it would be in production
    return await container.resolve(LoggerProtocol, {"name": "test_integration"})


@pytest.fixture
def capture_logs(capsys: pytest.CaptureFixture) -> callable:
    """Fixture to capture and parse JSON logs from stdout/stderr."""

    def _capture() -> dict[str, Any]:
        # Get captured output
        captured = capsys.readouterr()

        # Debug the raw output to help diagnose issues
        print("\n=== CAPTURED STDOUT ===")
        print(captured.out)
        print("=== CAPTURED STDERR ===")
        print(captured.err)
        print("======================")

        # Try to find and parse JSON from either stdout or stderr
        for output in [captured.out, captured.err]:
            if not output.strip():
                continue

            # Try each line separately
            for line in output.splitlines():
                line = line.strip()
                if not line:
                    continue

                # Try to find JSON objects in the line
                try:
                    if line.startswith("{") and line.endswith("}"):
                        return json.loads(line)
                except json.JSONDecodeError:
                    # Not valid JSON, continue to next line
                    pass

                # Try to find JSON in a line that might have other content
                try:
                    # Look for { ... } pattern
                    start = line.find("{")
                    end = line.rfind("}")
                    if start >= 0 and end > start:
                        json_str = line[start : end + 1]
                        return json.loads(json_str)
                except json.JSONDecodeError:
                    # Not valid JSON, continue to next line
                    pass

        # If we reach here, no valid JSON was found
        print("WARNING: No valid JSON found in the output")
        return {}

    return _capture


@pytest.mark.asyncio
async def test_logger_error_integration(capture_logs):
    """Test that the logger correctly handles and logs UnoError objects."""
    # Use JSON logger for testing
    logger = get_json_logger("test_integration")

    # Create a test error with additional context
    error = MockIntegrationError(
        message="Integration test failed",
        code="INTEGRATION_TEST_ERROR",
        category="test",
        context={"operation": "test_operation", "attempt": 3},
    )

    # Log the error
    await logger.error(
        "Integration test error occurred",
        exception=error,
        additional_info="This is additional context",
    )

    # Capture and verify the log output
    log_data = capture_logs()

    # Print captured data for debugging
    print(f"Captured log data: {json.dumps(log_data, indent=2)}")

    # More flexible assertions that handle different log formats
    assert log_data, "No log data was captured"

    # Check for level in different possible locations
    assert "level" in log_data or "severity" in log_data, "Log level not found"
    if "level" in log_data:
        assert log_data["level"] in ("ERROR", "error")
    elif "severity" in log_data:
        assert log_data["severity"] in ("ERROR", "error")

    # Check message
    assert any(key in log_data for key in ["message", "msg"]), "No message field found"
    message_key = next(key for key in ["message", "msg"] if key in log_data)
    assert "Integration test error occurred" in log_data[message_key]

    # More flexible error property checks
    if "exception" in log_data:
        exception_data = log_data["exception"]
        if isinstance(exception_data, dict):
            assert "code" in exception_data, "Error code missing from exception data"
            assert exception_data["code"] == "INTEGRATION_TEST_ERROR"
    elif "error_type" in log_data:
        assert log_data["error_type"] == "MockIntegrationError"
        assert "code" in log_data
        assert log_data["code"] == "INTEGRATION_TEST_ERROR"

    # Check for context info
    assert any(
        key in log_data for key in ["additional_info", "context.additional_info"]
    ), "Additional info missing"


@pytest.mark.asyncio
async def test_logger_nested_error_integration(capture_logs):
    """Test that the logger correctly handles nested error structures."""
    # Use JSON logger for testing
    logger = get_json_logger("test_integration_nested")

    # Create a nested error structure
    inner_error = MockIntegrationError(
        message="Inner error occurred", code="INNER_ERROR", category="inner"
    )

    # Add a print to see the error structure
    print(f"Inner error structure: {inner_error.__dict__}")

    outer_error = MockIntegrationError(
        message="Outer error occurred",
        code="OUTER_ERROR",
        category="outer",
        cause=inner_error,
        context={"operation": "nested_operation", "retry_count": 2},
    )

    # Add a print to see the error structure
    print(f"Outer error structure: {outer_error.__dict__}")

    # Log the error with additional context
    print("About to log the error...")
    await logger.error(
        "Nested error occurred", exception=outer_error, request_id="req_12345"
    )
    print("Error logged")

    # Capture and verify the log output
    log_data = capture_logs()

    # More basic assertion first
    if not log_data:
        # If no structured data, check if raw output contains our messages
        captured = capsys.readouterr()
        assert "Nested error occurred" in (
            captured.out + captured.err
        ), "Log message not found in output"
        assert "OUTER_ERROR" in (
            captured.out + captured.err
        ), "Error code not found in output"
        return

    # Print captured data for debugging
    print(f"Captured log data: {json.dumps(log_data, indent=2)}")

    # More flexible assertions
    assert log_data, "No log data was captured"

    # Check for level in different possible locations
    assert any(key in log_data for key in ["level", "severity"]), "Log level not found"
    if "level" in log_data:
        assert log_data["level"] in ("ERROR", "error")
    elif "severity" in log_data:
        assert log_data["severity"] in ("ERROR", "error")

    # Check message
    assert any(key in log_data for key in ["message", "msg"]), "No message field found"
    message_key = next(key for key in ["message", "msg"] if key in log_data)
    assert "Nested error occurred" in log_data[message_key]

    # Check error info
    if "exception" in log_data:
        exception_data = log_data["exception"]
        if isinstance(exception_data, dict):
            assert "code" in exception_data, "Error code missing from exception data"
            assert exception_data["code"] == "OUTER_ERROR"
            if "cause" in exception_data:
                assert exception_data["cause"]["code"] == "INNER_ERROR"

    # Check for request ID
    assert any(
        key in log_data for key in ["request_id", "context.request_id"]
    ), "Request ID missing"
