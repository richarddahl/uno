import pytest
import logging
from uno.logging.errors import ErrorLogger

class FakeLoggingError(Exception):
    def __init__(self, context):
        self.context = context
        super().__init__("fake error")

class FakeErrorContext:
    def __init__(self):
        self.code = "E123"
        self.context = {"foo": "bar"}
        self.severity = "ERROR"

def test_error_logger_logs(monkeypatch):
    logs = []
    class FakeLogger:
        async def log(self, level, msg, extra=None, **kwargs):
            logs.append((level, msg, extra))
        async def debug(self, msg, exc_info=None):
            logs.append(("DEBUG", msg, exc_info))
    err_logger = ErrorLogger(FakeLogger())
    fake_error = FakeLoggingError(FakeErrorContext())
    import asyncio
    asyncio.run(err_logger.log_error(fake_error))
    assert logs
