import pytest
from typer.testing import CliRunner

from uno.cli.log_admin import app as log_admin_app

runner = CliRunner()

def test_show_command():
    result = runner.invoke(log_admin_app, ["show"])
    assert result.exit_code == 0
    assert "LEVEL" in result.output

@pytest.mark.parametrize("field", ["LEVEL", "FORMAT", "JSON_FORMAT"])
def test_get_field_command(field):
    result = runner.invoke(log_admin_app, ["get-field", field])
    assert result.exit_code == 0
    assert field.lower() in result.output.lower()

def test_get_field_invalid():
    result = runner.invoke(log_admin_app, ["get-field", "not_a_field"])
    assert result.exit_code != 0
    assert "not found" in result.output

def test_schema_command():
    result = runner.invoke(log_admin_app, ["schema"])
    assert result.exit_code == 0
    assert "properties" in result.output

def test_restore_defaults_command():
    result = runner.invoke(log_admin_app, ["restore-defaults"])
    assert result.exit_code == 0
    assert "Restored logging config" in result.output

def test_validate_command():
    result = runner.invoke(log_admin_app, ["validate"])
    assert result.exit_code == 0
    assert "valid" in result.output.lower()

def test_set_command():
    result = runner.invoke(log_admin_app, ["set", "--level", "DEBUG", "--json-format"])
    assert result.exit_code == 0
    assert "DEBUG" in result.output
    assert "json_format" in result.output.lower()
