"""
Tests for LoggingConfigService (runtime updatable logging config).
"""
import pytest

from uno.core.logging.config_service import (
    LoggingConfigService,
    LoggingConfigUpdateError,
)
from uno.core.logging.logger import LoggerService, LoggingConfig


@pytest.fixture
def logger_service():
    svc = LoggerService(LoggingConfig())
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
    config_service.set_level("DEBUG")
    assert config_service.get_config().LEVEL == "DEBUG"

def test_toggle_json_format(config_service):
    config_service.set_json_format(True)
    assert config_service.get_config().JSON_FORMAT is True
    config_service.set_json_format(False)
    assert config_service.get_config().JSON_FORMAT is False

def test_file_output_update(tmp_path, config_service):
    file_path = str(tmp_path / "log.txt")
    config_service.set_file_output(True, file_path=file_path)
    cfg = config_service.get_config()
    assert cfg.FILE_OUTPUT is True
    assert file_path == cfg.FILE_PATH
    config_service.set_file_output(False)
    assert config_service.get_config().FILE_OUTPUT is False

def test_invalid_update_raises(config_service):
    with pytest.raises(LoggingConfigUpdateError):
        config_service.update_config(NOT_A_FIELD=123)
