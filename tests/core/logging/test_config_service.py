"""
Tests for LoggingConfigService (runtime updatable logging config).
"""
import pytest

from uno.core.logging.config_service import (
    LoggingConfigService,
    LoggingConfigUpdateError,
)
from uno.core.logging.logger import LoggerService, LoggingConfig
from uno.core.errors.result import Result, Success, Failure


class FakeLoggerService(LoggerService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.structured_logs = []
    def structured_log(self, level, msg, **kwargs):
        self.structured_logs.append((level, msg, kwargs))

@pytest.fixture
def logger_service():
    svc = FakeLoggerService(LoggingConfig())
    import asyncio
    asyncio.run(svc.initialize())
    yield svc
    asyncio.run(svc.dispose())

@pytest.fixture
def config_service(logger_service):
    return LoggingConfigService(logger_service)

def test_get_config(config_service):
    cfg = config_service.get_config()
    assert isinstance(cfg, LoggingConfig)

def test_update_level(config_service):
    result = config_service.set_level("DEBUG")
    assert isinstance(result, Success)
    assert config_service.get_config().LEVEL == "DEBUG"

def test_toggle_json_format(config_service):
    result_true = config_service.set_json_format(True)
    assert isinstance(result_true, Success)
    assert config_service.get_config().JSON_FORMAT is True
    result_false = config_service.set_json_format(False)
    assert isinstance(result_false, Success)
    assert config_service.get_config().JSON_FORMAT is False

def test_file_output_update(tmp_path, config_service):
    file_path = str(tmp_path / "log.txt")
    result_on = config_service.set_file_output(True, file_path=file_path)
    assert isinstance(result_on, Success)
    cfg = config_service.get_config()
    assert cfg.FILE_OUTPUT is True
    assert file_path == cfg.FILE_PATH
    result_off = config_service.set_file_output(False)
    assert isinstance(result_off, Success)
    assert config_service.get_config().FILE_OUTPUT is False

def test_invalid_update_returns_failure_and_logs(config_service, logger_service):
    result = config_service.update_config(NOT_A_FIELD=123)
    assert isinstance(result, Failure)
    # Error context should be attached
    assert hasattr(result.error, "context")
    assert "invalid_fields" in result.error.context
    assert "update" in result.error.context
    # Logger should have captured an error log
    logs = logger_service.structured_logs
    assert logs, "No error log was captured for invalid update"
    level, msg, context = logs[-1]
    assert level == "ERROR"
    assert "Invalid logging config field" in msg
    assert "NOT_A_FIELD" in str(context.get("invalid_fields", ""))
