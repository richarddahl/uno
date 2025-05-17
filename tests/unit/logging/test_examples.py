import pytest
from uno.logging.logger import UnoLogger, get_logger
from uno.logging.config import LoggingSettings

def test_example_minimal_logger():
    logger = UnoLogger(name="minimal")
    assert logger._logger.name == "minimal"
    logger._logger.info("Minimal log")

def test_example_advanced_config(monkeypatch):
    monkeypatch.setenv("UNO_LOGGING_LEVEL", "WARNING")
    settings = LoggingSettings.load()
    logger = UnoLogger(name="adv", settings=settings)
    assert logger._settings.level == "WARNING"
    logger._logger.warning("Advanced config log")
