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


class JWTConfig(BaseSettings):
    TOKEN_EXPIRE_MINUTES: int = 15
    TOKEN_REFRESH_MINUTES: int = 30
    TOKEN_ALGORITHM: str = "HS256"
    TOKEN_SECRET: str


class Prod(JWTConfig):
    model_config = ProdSettingsConfigDict


class Dev(JWTConfig):
    model_config = DevSettingsConfigDict


class Test(JWTConfig):
    model_config = TestSettingsConfigDict


# Create a dictionary of environment settings
env_settings: dict[str, type[JWTConfig]] = {"dev": Dev, "test": Test, "prod": Prod}

def get_jwt_config() -> Dev | Test | Prod:
    """Safely instantiate JWTConfig for the current environment only when needed."""
    env = os.environ.get("ENV", "dev").lower()
    return env_settings[env]()
