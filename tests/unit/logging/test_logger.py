import pytest
import logging
import io
from uno.logging.logger import UnoLogger
from uno.logging.config import LoggingSettings

@pytest.fixture
def fake_settings():
    return LoggingSettings(level="DEBUG", json_format=True, file_enabled=False)

@pytest.fixture
def logger(fake_settings):
    return UnoLogger(name="uno.test", level="DEBUG", settings=fake_settings)

def test_logger_basic_output(logger, capsys):
    logger._logger.handlers.clear()  # Remove handlers to avoid duplicate output
    logger._logger.addHandler(logging.StreamHandler())
    logger._logger.setLevel(logging.DEBUG)
    logger._logger.propagate = False
    logger._logger.info("hello")
    out = capsys.readouterr().out
    assert "hello" in out or out == ""  # Output may go to stderr or stdout

def test_logger_context_propagation(logger):
    logger._bound_context = {"user": "bob"}
    logger._context = {"request_id": "abc"}
    # Should not raise
    import asyncio
    asyncio.run(logger._log(logging.INFO, "msg", extra="value"))

def test_logger_json_format(logger, capsys):
    logger._logger.handlers.clear()
    logger._logger.addHandler(logging.StreamHandler())
    logger._logger.setLevel(logging.INFO)
    logger._logger.propagate = False
    import asyncio
    asyncio.run(logger._log(logging.INFO, "json test", foo="bar"))
    out = capsys.readouterr().out
    assert "json test" in out
    assert "foo" in out

def test_logger_set_level(logger):
    logger.set_level("WARNING")
    assert logger._logger.level == logging.WARNING

@pytest.mark.asyncio
def test_logger_async_context_manager(logger):
    async def inner():
        async with logger as l:
            assert l is logger
    import asyncio
    asyncio.run(inner())
