# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationConfig(BaseSettings):
    # APPLICATION SETTINGS
    # Max Groups and Users for each type of tenant
    ENFORCE_MAX_GROUPS: bool = True
    ENFORCE_MAX_USERS: bool = True
    MAX_INDIVIDUAL_GROUPS: int = 1
    MAX_INDIVIDUAL_USERS: int = 1
    MAX_BUSINESS_GROUPS: int = 5
    MAX_BUSINESS_USERS: int = 5
    MAX_CORPORATE_GROUPS: int = 25
    MAX_CORPORATE_USERS: int = 25
    MAX_ENTERPRISE_GROUPS: int = -1
    MAX_ENTERPRISE_USERS: int = -1

    # Superuser settings
    SUPERUSER_EMAIL: str
    SUPERUSER_HANDLE: str
    SUPERUSER_FULL_NAME: str

    # Modules to load
    LOAD_PACKAGES: list[str] = []
    APP_PATH: str = ""


class Prod(ApplicationConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env")


class Dev(ApplicationConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env_dev")


class Test(ApplicationConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env_test")


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
