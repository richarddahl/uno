"""
Tests for ErrorLoggingService (structured error event logging).
"""
import pytest
from uno.core.logging.logger import LoggerService
from uno.core.logging.error_logging_service import ErrorLoggingService
from uno.core.errors.base import FrameworkError

class DummyFrameworkError(FrameworkError):
    def __init__(self, message: str, error_code: str = "DUMMY", **context):
        super().__init__(message, error_code, **context)

@pytest.fixture
def logger_service():
    svc = LoggerService()
    import asyncio
    asyncio.run(svc.initialize())
    # Enable JSON log format for structured log assertions
    svc._config = svc._config.model_copy(update={"JSON_FORMAT": True})
    svc._configure_root_logger()
    # Force root logger to only use our handler
    import logging
    root_logger = logging.getLogger()
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
    json_handler = logging.StreamHandler()
    json_handler.setFormatter(svc._get_formatter())
    root_logger.addHandler(json_handler)
    root_logger.setLevel(logging.ERROR)
    yield svc
    asyncio.run(svc.dispose())

@pytest.fixture
def error_logging_service(logger_service):
    return ErrorLoggingService(logger_service)

import json

def test_log_framework_error(caplog, error_logging_service):
    err = DummyFrameworkError("fail", error_code="X123", foo="bar")
    with caplog.at_level("ERROR"):
        error_logging_service.log_error(err, context={"user_id": 42}, trace_context={"correlation_id": "abc"})
    found = None
    for rec in caplog.records:
        ctx = getattr(rec, "context", None)
        if ctx and ctx.get("error_code") == "X123":
            found = ctx
            break
    assert found is not None, f"No log record with error_code='X123' found in: {[getattr(r, 'context', None) for r in caplog.records]}"
    assert found["user_id"] == 42
    assert found["correlation_id"] == "abc"
    assert found["foo"] == "bar"

def test_log_standard_exception(caplog, error_logging_service):
    err = ValueError("bad value!")
    with caplog.at_level("ERROR"):
        error_logging_service.log_error(err, context={"user_id": 99})
    found = None
    for rec in caplog.records:
        ctx = getattr(rec, "context", None)
        if ctx and ctx.get("error_type") == "ValueError":
            found = ctx
            break
    assert found is not None, f"No log record with error_type='ValueError' found in: {[getattr(r, 'context', None) for r in caplog.records]}"
    assert found["user_id"] == 99
