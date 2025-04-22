# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import os
from os.path import abspath, dirname

from pydantic_settings import BaseSettings, SettingsConfigDict


class GeneralConfig(BaseSettings):
    UNO_ROOT: str = dirname(dirname(abspath(__file__)))
    SITE_NAME: str
    DEBUG: bool = False
    LOCALE: str = "en_US"
    ENV: str = "prod"
    API_VERSION: str = "v1.0"


class Prod(GeneralConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env")


class Dev(GeneralConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env_dev")


class Test(GeneralConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env_test")


# Create a dictionary of environment settings
env_settings: dict[str, type[GeneralConfig]] = {"dev": Dev, "test": Test, "prod": Prod}
# Select the environment settings based on the ENV variable
general_config: Dev | Test | Prod = env_settings[os.environ.get("ENV", "dev").lower()]()
