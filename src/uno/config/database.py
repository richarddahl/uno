# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    # DATABASE SETTINGS
    DB_USER: str
    DB_USER_PW: str
    DB_HOST: str
    DB_PORT: int
    DB_SCHEMA: str
    DB_NAME: str
    DB_SYNC_DRIVER: str
    DB_ASYNC_DRIVER: str


class Prod(DatabaseConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env")


class Dev(DatabaseConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env_dev")


class Test(DatabaseConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env_test")


# Create a dictionary of environment settings
env_settings: dict[str, type[DatabaseConfig]] = {"dev": Dev, "test": Test, "prod": Prod}
# Select the environment settings based on the ENV variable
database_config: Dev | Test | Prod = env_settings[
    os.environ.get("ENV", "dev").lower()
]()
