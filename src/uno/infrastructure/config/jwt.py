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


from typing import Literal
from pydantic import Field

class JWTConfig(BaseSettings):
    TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=1, le=1440)
    TOKEN_REFRESH_MINUTES: int = Field(default=30, ge=1, le=10080)
    TOKEN_ALGORITHM: Literal["HS256", "RS256"] = "HS256"
    TOKEN_SECRET: str = Field(..., min_length=8)


class Prod(JWTConfig):
    model_config = ProdSettingsConfigDict


class Dev(JWTConfig):
    model_config = DevSettingsConfigDict


class Test(JWTConfig):
    model_config = TestSettingsConfigDict
    __test__ = False


# Create a dictionary of environment settings
env_settings: dict[str, type[JWTConfig]] = {"dev": Dev, "test": Test, "prod": Prod}


def get_jwt_config() -> Dev | Test | Prod:
    """Safely instantiate JWTConfig for the current environment only when needed."""
    env = os.environ.get("ENV", "dev").lower()
    return env_settings[env]()
