import logging
import pytest
from uno.logging.logger import StructuredFormatter

def test_structured_formatter_json():
    fmt = StructuredFormatter(json_format=True, include_timestamp=False, include_level=False)
    record = logging.LogRecord(
        name="uno.test", level=logging.INFO, pathname="", lineno=0, msg="msg", args=(), exc_info=None
    )
    formatted = fmt.format(record)
    assert "msg" in formatted
    assert formatted.startswith("{")

def test_structured_formatter_plain():
    fmt = StructuredFormatter(json_format=False, include_timestamp=True, include_level=True)
    record = logging.LogRecord(
        name="uno.test", level=logging.INFO, pathname="", lineno=0, msg="plain", args=(), exc_info=None
    )
    formatted = fmt.format(record)
    assert "plain" in formatted
    assert "INFO" in formatted
    assert any([ts in formatted for ts in [":", "-"]])  # timestamp present
