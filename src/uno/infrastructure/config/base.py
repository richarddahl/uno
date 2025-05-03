# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
Base configuration for Uno framework.
"""

from pydantic_settings import SettingsConfigDict

ProdSettingsConfigDict = SettingsConfigDict(
    case_sensitive=False, extra="ignore", env_file=".env"
)
DevSettingsConfigDict = SettingsConfigDict(
    case_sensitive=False, extra="ignore", env_file=".env_dev"
)
TestSettingsConfigDict = SettingsConfigDict(
    case_sensitive=False, extra="ignore", env_file=".env_test"
)
