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


from typing import Literal, Any
from pydantic import Field

class VectorSearchConfig(BaseSettings):
    VECTOR_DIMENSIONS: int = Field(default=1536, ge=1, le=4096)
    VECTOR_INDEX_TYPE: Literal["hnsw", "flat"] = "hnsw"
    VECTOR_BATCH_SIZE: int = Field(default=50, ge=1, le=1000)
    VECTOR_UPDATE_INTERVAL: float = Field(default=1.0, ge=0.0, le=3600.0)
    VECTOR_AUTO_START: bool = True
    VECTOR_ENTITIES: dict[str, str] = Field(default_factory=dict)
    VECTOR_EF_SEARCH: int = Field(default=50, ge=1, le=100)
    VECTOR_M: int = Field(default=8, ge=1, le=32)
    VECTOR_CACHE_SIZE: int = Field(default=100, ge=1, le=1000)
    VECTOR_THREADS: int = Field(default=2, ge=1, le=4)
    VECTOR_DISTANCE_THRESHOLD: float = Field(default=0.7, ge=0.0, le=1.0)
    VECTOR_MIN_SCORE: float = Field(default=0.7, ge=0.0, le=1.0)
    VECTOR_MAX_RESULTS: int = Field(default=20, ge=1, le=100)


from pydantic import field_validator, model_validator

class Prod(VectorSearchConfig):
    model_config = ProdSettingsConfigDict
    
    VECTOR_M: int = Field(default=8, ge=32, le=32)
    VECTOR_THREADS: int = Field(default=2, ge=4, le=4)
    VECTOR_CACHE_SIZE: int = Field(default=100, ge=1000, le=1000)
    VECTOR_DISTANCE_THRESHOLD: float = Field(default=0.7, ge=0.9, le=1.0)
    VECTOR_MIN_SCORE: float = Field(default=0.7, ge=0.7, le=1.0)
    VECTOR_MAX_RESULTS: int = Field(default=20, ge=20, le=100)

class Dev(VectorSearchConfig):
    model_config = DevSettingsConfigDict
    
    VECTOR_M: int = Field(default=8, ge=16, le=32)
    VECTOR_THREADS: int = Field(default=2, ge=2, le=4)
    VECTOR_CACHE_SIZE: int = Field(default=100, ge=100, le=1000)
    VECTOR_DISTANCE_THRESHOLD: float = Field(default=0.7, ge=0.8, le=1.0)
    VECTOR_MIN_SCORE: float = Field(default=0.7, ge=0.5, le=1.0)
    VECTOR_MAX_RESULTS: int = Field(default=20, ge=10, le=100)

class TestConfig(VectorSearchConfig):
    __test__ = False
    model_config = TestSettingsConfigDict
    
    VECTOR_M: int = Field(default=8, ge=8, le=32)
    VECTOR_THREADS: int = Field(default=2, ge=1, le=4)
    VECTOR_CACHE_SIZE: int = Field(default=100, ge=10, le=1000)
    VECTOR_DISTANCE_THRESHOLD: float = Field(default=0.7, ge=0.7, le=1.0)
    VECTOR_MIN_SCORE: float = Field(default=0.7, ge=0.3, le=1.0)
    VECTOR_MAX_RESULTS: int = Field(default=20, ge=5, le=100)

# Create a dictionary of environment settings
env_settings: dict[str, type[VectorSearchConfig]] = {
    "dev": Dev,
    "test": TestConfig,
    "prod": Prod,
}
# Select the environment settings based on the ENV variable
vector_search_config: Dev | TestConfig | Prod = env_settings[
    os.environ.get("ENV", "dev").lower()
]()
