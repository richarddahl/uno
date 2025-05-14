import os
import pytest
from uno.logging.config import LoggingSettings


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    # Clear relevant env vars before each test
    keys = [
        "UNO_LOGGING_LEVEL",
        "UNO_LOGGING_JSON_FORMAT",
        "UNO_LOGGING_INCLUDE_TIMESTAMP",
        "UNO_LOGGING_INCLUDE_LEVEL",
        "UNO_LOGGING_CONSOLE_ENABLED",
        "UNO_LOGGING_FILE_ENABLED",
        "UNO_LOGGING_FILE_PATH",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)


class FakeEnv:
    def __init__(self, **kwargs):
        self.vars = kwargs

    def set(self, monkeypatch):
        for k, v in self.vars.items():
            monkeypatch.setenv(f"UNO_LOGGING_{k.upper()}", v)


@pytest.mark.parametrize(
    "env,expected",
    [
        ({}, LoggingSettings()),
        ({"LEVEL": "DEBUG"}, LoggingSettings(level="DEBUG")),
        ({"JSON_FORMAT": "true"}, LoggingSettings(json_format=True)),
        ({"INCLUDE_TIMESTAMP": "false"}, LoggingSettings(include_timestamp=False)),
        ({"INCLUDE_LEVEL": "false"}, LoggingSettings(include_level=False)),
        ({"CONSOLE_ENABLED": "false"}, LoggingSettings(console_enabled=False)),
        (
            {"FILE_ENABLED": "true", "FILE_PATH": "/tmp/log.txt"},
            LoggingSettings(file_enabled=True, file_path="/tmp/log.txt"),
        ),
    ],
)
def test_logging_settings_env(monkeypatch, env, expected):
    for k, v in env.items():
        monkeypatch.setenv(f"UNO_LOGGING_{k}", v)
    settings = LoggingSettings.load()
    # Fix: Access model_fields from the class, not the instance
    for field in LoggingSettings.model_fields:
        assert getattr(settings, field) == getattr(expected, field)


def test_logging_settings_type_validation():
    # Invalid bool
    with pytest.raises(ValueError):
        LoggingSettings.model_validate({"json_format": "notabool"})
    # Invalid level type
    with pytest.raises(ValueError):
        LoggingSettings.model_validate({"level": 123})


def test_logging_settings_defaults():
    settings = LoggingSettings()
    assert settings.level == "INFO"
    assert settings.json_format is False
    assert settings.include_timestamp is True
    assert settings.include_level is True
    assert settings.console_enabled is True
    assert settings.file_enabled is False
    assert settings.file_path is None
