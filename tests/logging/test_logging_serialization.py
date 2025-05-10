"""
Unit tests for logger serialization of tricky types (datetime, date, UUID, etc).
"""
import datetime
import uuid
import pytest
from uno.logging.logger import get_logger

pytestmark = pytest.mark.usefixtures('allow_logging')

@pytest.mark.parametrize("value,expected_fragment", [
    (datetime.datetime(2023, 5, 10, 12, 34, 56), "2023-05-10T12:34:56"),
    (datetime.date(2023, 5, 10), "2023-05-10"),
    (uuid.UUID("12345678-1234-5678-1234-567812345678"), "12345678-1234-5678-1234-567812345678"),
    ("plain string", "plain string"),
    ("string with spaces", '"string with spaces"'),
    ({"a": 1, "b": 2}, '"a"'),  # Should be JSON
    ([1, 2, 3], '[1, 2, 3]'),
])
def test_logger_handles_serialization_types(value, expected_fragment, capsys):
    logger = get_logger("test_logger_serialization")
    logger.info("Test log", tricky=value)
    captured = capsys.readouterr()
    assert expected_fragment in captured.out or expected_fragment in captured.err


def test_logger_does_not_raise_on_unserializable(capsys):
    class Unserializable:
        pass
    logger = get_logger("test_logger_serialization")
    logger.info("Test log", tricky=Unserializable())
    captured = capsys.readouterr()
    # Should fallback to str and not raise
    assert "Unserializable" in captured.out or "Unserializable" in captured.err
