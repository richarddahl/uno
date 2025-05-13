"""Edge and corner cases for Uno config system."""

import os

from pydantic_settings import SettingsConfigDict
import pytest
import asyncio
from pathlib import Path
from typing import Any

from uno.config import (
    SecureField,
    SecureValue,
    SecureValueHandling,
    UnoSettings,
    load_settings,
)

# 1. Explicit override_values always win
def test_explicit_override_priority(monkeypatch, tmp_path):
    class MySettings(UnoSettings):
        foo: str = "default"
        bar: int = 1
    monkeypatch.setenv("FOO", "env_foo")
    monkeypatch.setenv("BAR", "2")
    overrides = {"foo": "override_foo", "bar": 42}
    settings = asyncio.run(load_settings(MySettings, override_values=overrides))
    assert settings.foo == "override_foo"
    assert settings.bar == 42

# 2. config_path loads from custom dir
def test_config_path_loading(tmp_path):
    config_dir = tmp_path / "conf"
    config_dir.mkdir()
    env_file = config_dir / ".env"
    env_file.write_text("FOO=from_file\n")
    class MySettings(UnoSettings):
        foo: str = "default"
    settings = asyncio.run(load_settings(MySettings, config_path=str(config_dir)))
    assert settings.foo == "from_file"

# 3. SecureValue edge cases
def test_securevalue_empty_and_none():
    val = SecureValue("", handling=SecureValueHandling.MASK)
    assert val.get_value() == ""
    val2 = SecureValue(None, handling=SecureValueHandling.MASK)
    assert val2.get_value() is None or val2.get_value() == "None"
    with pytest.raises(TypeError):
        SecureValue(object(), handling=SecureValueHandling.MASK)

def test_securevalue_equality():
    a = SecureValue("x", handling=SecureValueHandling.MASK)
    b = SecureValue("x", handling=SecureValueHandling.MASK)
    assert a == b
    assert a == "x"
    assert not (a != "x")

# 4. UnoSettings field alias/env prefix
def test_field_alias_and_env_prefix(monkeypatch):
    class MySettings(UnoSettings):
        fooBar: str = "abc"
        model_config = SettingsConfigDict(
            alias_generator = lambda f: f.upper()
        )
    monkeypatch.setenv("FOOBAR", "from_env")
    settings = asyncio.run(load_settings(MySettings))
    assert settings.fooBar == "from_env"

# 5. Misconfigured SecureField raises
def test_invalid_securefield():
    with pytest.raises(Exception):
        SecureField("bad", handling="not_a_handling") 

# 6. Thread safety under concurrent load_settings with overrides
@pytest.mark.asyncio
async def test_concurrent_load_settings_overrides(monkeypatch):
    class MySettings(UnoSettings):
        foo: str = "default"
    monkeypatch.setenv("FOO", "env_value")
    async def load():
        return await load_settings(MySettings, override_values={"foo": "override"})
    results = await asyncio.gather(*(load() for _ in range(10)))
    assert all(s.foo == "override" for s in results)

# 7. Env var pollution: unrelated vars don't override
def test_env_var_pollution(monkeypatch):
    class MySettings(UnoSettings):
        foo: str = "default"
    monkeypatch.setenv("UNRELATED_VAR", "should_not_affect")
    settings = asyncio.run(load_settings(MySettings))
    assert settings.foo == "default"

# 8. Sealed SecureValue in settings
def test_sealed_securevalue_in_settings():
    class MySettings(UnoSettings):
        secret: str = SecureField("top", handling=SecureValueHandling.SEALED)
    s = MySettings()
    with pytest.raises(Exception):
        _ = s.secret.get_value()

# 9. Nested UnoSettings secure masking
def test_nested_unosettings_masking():
    class Inner(UnoSettings):
        password: str = SecureField("pw", handling=SecureValueHandling.MASK)
    class Outer(UnoSettings):
        inner: Inner = Inner()
    o = Outer()
    masked = o._mask_secure_fields()
    assert masked["inner"]["password"] == "********"
