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

class APIConfig(BaseSettings):
    API_VERSION: Literal["v1.0"] = "v1.0"
    # QUERY SETTINGS
    DEFAULT_LIMIT: int = Field(default=100, ge=1, le=1000)
    DEFAULT_OFFSET: int = Field(default=0, ge=0)
    DEFAULT_PAGE_SIZE: int = Field(default=25, ge=1, le=1000)


class Prod(APIConfig):
    model_config = ProdSettingsConfigDict


class Dev(APIConfig):
    model_config = DevSettingsConfigDict


class Test(APIConfig):
    model_config = TestSettingsConfigDict
    __test__ = False


# Create a dictionary of environment settings
env_settings: dict[str, type[APIConfig]] = {"dev": Dev, "test": Test, "prod": Prod}
# Select the environment settings based on the ENV variable
api_config: Dev | Test | Prod = env_settings[os.environ.get("ENV", "dev").lower()]()
