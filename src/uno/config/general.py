# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import os
from os.path import abspath, dirname

from pydantic_settings import BaseSettings

from uno.config.base import (
    DevSettingsConfigDict,
    ProdSettingsConfigDict,
    TestSettingsConfigDict,
)


class GeneralConfig(BaseSettings):
    UNO_ROOT: str = dirname(dirname(abspath(__file__)))
    SITE_NAME: str = "uno"
    DEBUG: bool = False
    LOCALE: str = "en_US"
    ENV: str = "prod"
    API_VERSION: str = "v1.0"


class Prod(GeneralConfig):
    model_config = ProdSettingsConfigDict


class Dev(GeneralConfig):
    model_config = DevSettingsConfigDict


class Test(GeneralConfig):
    SITE_NAME: str = "Uno Test Site"  # Default for tests
    model_config = TestSettingsConfigDict


# Create a dictionary of environment settings
env_settings: dict[str, type[GeneralConfig]] = {"dev": Dev, "test": Test, "prod": Prod}
# Select the environment settings based on the ENV variable
general_config: Dev | Test | Prod = env_settings[os.environ.get("ENV", "dev").lower()]()
