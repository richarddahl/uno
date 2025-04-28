# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
import decimal
from datetime import date, datetime, timedelta

import pytest

from uno.core import utils
from uno.core.config.general import GeneralConfig
from uno.core.logging.logger import LoggerService


@pytest.fixture
def general_config():
    """
    Provide a GeneralConfig instance for testing.
    """
    # Create and return an instance directly instead of using DI
    return GeneralConfig()


class FakeLoggerService(LoggerService):
    def __init__(self):
        self.logs = []
    def structured_log(self, level: str, msg: str, **kwargs):
        self.logs.append((level, msg, kwargs))

class DummyModel:
    def __str__(self):
        return "DummyModelString"

def test_import_from_path_success(tmp_path):
    # Create a dummy module file
    mod_path = tmp_path / "modsuccess.py"
    mod_path.write_text("x = 42\n")
    logger = FakeLoggerService()
    mod = utils.import_from_path("modsuccess", str(mod_path), logger=logger)
    assert hasattr(mod, "x")
    assert logger.logs == []  # No error logs

def test_import_from_path_failure(tmp_path):
    logger = FakeLoggerService()
    missing_path = tmp_path / "missing.py"
    with pytest.raises(Exception):
        utils.import_from_path("missingmod", str(missing_path), logger=logger)
    assert logger.logs
    log = logger.logs[0]
    assert log[0] == "ERROR"
    assert "Failed to import module" in log[1]
    assert log[2]["module_name"] == "missingmod"
    assert log[2]["file_path"] == str(missing_path)

def test_boolean_to_string():
    assert utils.boolean_to_string(True) == "Yes"
    assert utils.boolean_to_string(False) == "No"


def test_date_to_string():
    d = date(2023, 4, 22)
    assert utils.date_to_string(d) == "Apr 22, 2023"
    assert utils.date_to_string(None) is None


def test_datetime_to_string(general_config):
    dt = datetime(2023, 4, 22, 15, 30)
    result = utils.datetime_to_string(dt, general_config)
    assert "2023" in result
    assert utils.datetime_to_string(None, general_config) is None


def test_decimal_to_string():
    dec = decimal.Decimal("1234.56")
    assert utils.decimal_to_string(dec) == "1,234.56"
    assert utils.decimal_to_string(None) is None


def test_obj_to_string():
    model = DummyModel()
    assert utils.obj_to_string(model) == "DummyModelString"
    assert utils.obj_to_string(None) is None


def test_timedelta_to_string():
    td = timedelta(days=2, hours=3)
    assert "2 days" in utils.timedelta_to_string(td)
    assert utils.timedelta_to_string(None) is None


def test_snake_to_camel():
    assert utils.snake_to_camel("my_snake_case") == "MySnakeCase"


def test_snake_to_caps_snake():
    assert utils.snake_to_caps_snake("my_snake_case") == "MY_SNAKE_CASE"
