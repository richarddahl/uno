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


class VectorSearchConfig(BaseSettings):
    VECTOR_DIMENSIONS: int = 1536
    VECTOR_INDEX_TYPE: str = "hnsw"
    VECTOR_BATCH_SIZE: int = 10
    VECTOR_UPDATE_INTERVAL: float = 1.0
    VECTOR_AUTO_START: bool = True
    VECTOR_ENTITIES: dict[str, str] = {}


class Prod(VectorSearchConfig):
    model_config = ProdSettingsConfigDict


class Dev(VectorSearchConfig):
    model_config = DevSettingsConfigDict


class Test(VectorSearchConfig):
    model_config = TestSettingsConfigDict


# Create a dictionary of environment settings
env_settings: dict[str, type[VectorSearchConfig]] = {
    "dev": Dev,
    "test": Test,
    "prod": Prod,
}
# Select the environment settings based on the ENV variable
vector_search_config: Dev | Test | Prod = env_settings[
    os.environ.get("ENV", "dev").lower()
]()
