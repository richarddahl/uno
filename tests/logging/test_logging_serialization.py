"""
Unit tests for logger serialization of tricky types (datetime, date, UUID, etc).
"""

import datetime
from unittest.mock import MagicMock, patch
import uuid

import pytest

from uno.logging.logger import LoggerProtocol, get_logger

pytestmark = pytest.mark.usefixtures("allow_logging")


@pytest.fixture
def logger() -> LoggerProtocol:
    """Create a test logger with mock handler.

    Returns:
        LoggerProtocol: Configured logger instance with mock handler
    """
    with patch("uno.logging.config.LoggingSettings") as mock_settings_cls:
        mock_settings_cls.return_value = MagicMock(
            log_level="INFO", log_format="json", log_file=None
        )
        test_logger = get_logger("test_logger_serialization")
        test_logger._handler = MagicMock()  # type: ignore[attr-defined]
        return test_logger


@pytest.mark.parametrize(
    "value,expected_fragment",
    [
        (datetime.datetime(2023, 5, 10, 12, 34, 56), "2023-05-10T12:34:56"),
        (datetime.date(2023, 5, 10), "2023-05-10"),
        (
            uuid.UUID("12345678-1234-5678-1234-567812345678"),
            "12345678-1234-5678-1234-567812345678",
        ),
        ("plain string", "plain string"),
        ("string with spaces", '"string with spaces"'),
        ({"a": 1, "b": 2}, '"a"'),  # Should be JSON
        ([1, 2, 3], "[1, 2, 3]"),
    ],
)
@pytest.mark.asyncio
async def test_logger_handles_serialization_types(
    value, expected_fragment, capsys
) -> None:
    logger = get_logger("test_logger_serialization")
    await logger.info("Test log", tricky=value)
    captured = capsys.readouterr()
    assert expected_fragment in captured.out or expected_fragment in captured.err


@pytest.mark.asyncio
async def test_logger_does_not_raise_on_unserializable(capsys) -> None:
    class Unserializable:
        def __str__(self) -> str:
            return "<Unserializable>"

    # Create a logger with a custom encoder
    with patch("uno.logging.config.LoggingSettings") as mock_settings_cls:
        mock_settings_cls.return_value = MagicMock(
            log_level="INFO", log_format="json", log_file=None
        )
        # Remove any cached logger to force UnoLogger construction with handler
        from uno.logging.logger import UnoLogger
        captured_output = []
        async def mock_handler(*args, **kwargs):
            captured_output.append(kwargs)
        # Patch settings so no file logging is attempted
        mock_settings = mock_settings_cls.return_value
        mock_settings.log_file = None
        mock_settings.file_path = None
        mock_settings.json_format = True
        logger = UnoLogger(
            "test_logger_serialization",
            settings=mock_settings,
            _handler=mock_handler
        )
        await logger.info("Test log", tricky=Unserializable())
        assert len(captured_output) == 1
        log_record = captured_output[0]
        assert "tricky=<Unserializable>" in log_record.get("message", "")
