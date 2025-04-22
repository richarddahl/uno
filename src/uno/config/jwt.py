# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class JWTConfig(BaseSettings):
    TOKEN_EXPIRE_MINUTES: int = 15
    TOKEN_REFRESH_MINUTES: int = 30
    TOKEN_ALGORITHM: str = "HS256"
    TOKEN_SECRET: str


class Prod(JWTConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env")


class Dev(JWTConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env_dev")


class Test(JWTConfig):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env_test")


# Create a dictionary of environment settings
env_settings: dict[str, type[JWTConfig]] = {"dev": Dev, "test": Test, "prod": Prod}
# Select the environment settings based on the ENV variable
jwt_config: Dev | Test | Prod = env_settings[os.environ.get("ENV", "dev").lower()]()
