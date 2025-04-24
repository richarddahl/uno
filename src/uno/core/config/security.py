# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import os

from pydantic_settings import BaseSettings

from uno.core.config.base import (
    DevSettingsConfigDict,
    ProdSettingsConfigDict,
    TestSettingsConfigDict,
)


class SecurityConfig(BaseSettings):
    LOGIN_URL: str
    FORCE_RLS: bool = True


class Prod(SecurityConfig):
    model_config = ProdSettingsConfigDict


class Dev(SecurityConfig):
    model_config = DevSettingsConfigDict


class Test(SecurityConfig):
    model_config = TestSettingsConfigDict


# Create a dictionary of environment settings
env_settings: dict[str, type[SecurityConfig]] = {"dev": Dev, "test": Test, "prod": Prod}
# Select the environment settings based on the ENV variable
security_config: Dev | Test | Prod = env_settings[
    os.environ.get("ENV", "dev").lower()
]()
