# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import os

from pydantic_settings import BaseSettings

from uno.infrastructure.config.base import (
    DevSettingsConfigDict,
    ProdSettingsConfigDict,
    TestSettingsConfigDict,
)


from pydantic import Field

class DatabaseConfig(BaseSettings):
    # DATABASE SETTINGS
    DB_USER: str = Field(..., min_length=1)
    DB_USER_PW: str = Field(..., min_length=1)
    DB_HOST: str = Field(..., min_length=1)
    DB_PORT: int = Field(..., ge=1, le=65535)
    DB_SCHEMA: str = Field(..., min_length=1)
    DB_NAME: str = Field(..., min_length=1)
    DB_SYNC_DRIVER: str = Field(..., min_length=1)
    DB_ASYNC_DRIVER: str = Field(..., min_length=1)


class Prod(DatabaseConfig):
    model_config = ProdSettingsConfigDict


class Dev(DatabaseConfig):
    model_config = DevSettingsConfigDict


class Test(DatabaseConfig):
    model_config = TestSettingsConfigDict
    __test__ = False


# Create a dictionary of environment settings
env_settings: dict[str, type[DatabaseConfig]] = {"dev": Dev, "test": Test, "prod": Prod}
# Select the environment settings based on the ENV variable
database_config: Dev | Test | Prod = env_settings[
    os.environ.get("ENV", "dev").lower()
]()
