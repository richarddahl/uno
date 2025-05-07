# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import os
from os.path import abspath, dirname
from typing import Any, List

from pydantic_settings import BaseSettings

from uno.infrastructure.config.base import (
    DevSettingsConfigDict,
    ProdSettingsConfigDict,
    TestSettingsConfigDict,
)


from uno.infrastructure.sql.interfaces import ConfigProtocol

from typing import Literal
from pydantic import Field

class GeneralConfig(BaseSettings):
    UNO_ROOT: str = Field(default=dirname(dirname(abspath(__file__))), min_length=1)
    SITE_NAME: str = Field(default="uno", min_length=1)
    DEBUG: bool = False
    LOCALE: str = Field(default="en_US", min_length=2, max_length=10)
    ENV: Literal["dev", "test", "prod"] = "prod"
    API_VERSION: Literal["v1.0"] = "v1.0"

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value with optional default."""
        return getattr(self, key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean configuration value with optional default."""
        return bool(getattr(self, key, default))

    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer configuration value with optional default."""
        return int(getattr(self, key, default))

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a float configuration value with optional default."""
        return float(getattr(self, key, default))

    def get_list(self, key: str, default: list[Any] | None = None) -> list[Any]:
        """Get a list configuration value with optional default."""
        return list(getattr(self, key, default or []))


class Prod(GeneralConfig):
    model_config = ProdSettingsConfigDict


class Dev(GeneralConfig):
    model_config = DevSettingsConfigDict


class Test(GeneralConfig):
    SITE_NAME: str = "Uno Test Site"  # Default for tests
    model_config = TestSettingsConfigDict
    __test__ = False


# Create a dictionary of environment settings
env_settings: dict[str, type[GeneralConfig]] = {"dev": Dev, "test": Test, "prod": Prod}
# Select the environment settings based on the ENV variable
general_config: Dev | Test | Prod = env_settings[os.environ.get("ENV", "dev").lower()]()

# Public alias for DI/config API
ConfigService = GeneralConfig
