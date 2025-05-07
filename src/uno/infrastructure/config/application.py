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

class ApplicationConfig(BaseSettings):
    # APPLICATION SETTINGS
    # Max Groups and Users for each type of tenant
    ENFORCE_MAX_GROUPS: bool = True
    ENFORCE_MAX_USERS: bool = True
    MAX_INDIVIDUAL_GROUPS: int = Field(default=1, ge=-1, le=100000)
    MAX_INDIVIDUAL_USERS: int = Field(default=1, ge=-1, le=100000)
    MAX_BUSINESS_GROUPS: int = Field(default=5, ge=-1, le=100000)
    MAX_BUSINESS_USERS: int = Field(default=5, ge=-1, le=100000)
    MAX_CORPORATE_GROUPS: int = Field(default=25, ge=-1, le=100000)
    MAX_CORPORATE_USERS: int = Field(default=25, ge=-1, le=100000)
    MAX_ENTERPRISE_GROUPS: int = Field(default=-1, ge=-1, le=100000)
    MAX_ENTERPRISE_USERS: int = Field(default=-1, ge=-1, le=100000)

    # Superuser settings
    SUPERUSER_EMAIL: str
    SUPERUSER_HANDLE: str
    SUPERUSER_FULL_NAME: str

    # Modules to load
    LOAD_PACKAGES: list[str] = Field(default_factory=list)
    APP_PATH: str = ""


class Prod(ApplicationConfig):
    model_config = ProdSettingsConfigDict


class Dev(ApplicationConfig):
    model_config = DevSettingsConfigDict


class Test(ApplicationConfig):
    model_config = TestSettingsConfigDict
    __test__ = False


# Create a dictionary of environment settings
env_settings: dict[str, type[ApplicationConfig]] = {
    "dev": Dev,
    "test": Test,
    "prod": Prod,
}
# Select the environment settings based on the ENV variable
application_config: Dev | Test | Prod = env_settings[
    os.environ.get("ENV", "dev").lower()
]()
