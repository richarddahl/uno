# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class APIConfig(BaseSettings):
    API_VERSION: str = "v1.0"
    # QUERY SETTINGS
    DEFAULT_LIMIT: int = 100
    DEFAULT_OFFSET: int = 0
    DEFAULT_PAGE_SIZE: int = 25


class Prod(APIConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env")


class Dev(APIConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env_dev")


class Test(APIConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env_test")


# Create a dictionary of environment settings
env_settings: dict[str, type[APIConfig]] = {"dev": Dev, "test": Test, "prod": Prod}
# Select the environment settings based on the ENV variable
api_config: Dev | Test | Prod = env_settings[os.environ.get("ENV", "dev").lower()]()
