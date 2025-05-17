# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Migration guide for Pydantic v2 usage in Uno Framework.

This file provides examples for migrating from deprecated Pydantic v1 patterns
to the recommended Pydantic v2 patterns.
"""

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


###########################################
# DEPRECATED: Class-based config approach #
###########################################


# BAD - Don't use this pattern:
class DeprecatedModel(BaseModel):
    name: str
    value: int

    class Config:  # This syntax is deprecated
        extra = "ignore"
        validate_default = True


###########################################
# CORRECT: Attribute-based config approach #
###########################################


# GOOD - Use this pattern instead:
class RecommendedModel(BaseModel):
    name: str
    value: int

    model_config = ConfigDict(  # This is the recommended syntax
        extra="ignore",
        validate_default=True,
    )


#################################################
# CORRECT: Attribute-based config for settings #
#################################################


# For settings models:
class RecommendedSettings(BaseSettings):
    api_key: str
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        validate_default=True,
    )


# Use these patterns in all test models and application code to avoid
# the PydanticDeprecatedSince20 warning
