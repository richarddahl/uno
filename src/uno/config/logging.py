# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

# Logging configuration
import os

from pydantic_settings import BaseSettings

from uno.config.base import (
    DevSettingsConfigDict,
    ProdSettingsConfigDict,
    TestSettingsConfigDict,
)


class LoggingConfig(BaseSettings):
    LEVEL: str = "INFO"
    FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    JSON_FORMAT: bool = False
    CONSOLE_OUTPUT: bool = True
    FILE_OUTPUT: bool = False
    FILE_PATH: str | None = None
    BACKUP_COUNT: int = 5
    MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB
    PROPAGATE: bool = False
    INCLUDE_LOGGER_CONTEXT: bool = True
    INCLUDE_EXCEPTION_TRACEBACK: bool = True


class Prod(LoggingConfig):
    model_config = ProdSettingsConfigDict


class Dev(LoggingConfig):
    model_config = DevSettingsConfigDict


class Test(LoggingConfig):
    model_config = TestSettingsConfigDict


# Create a dictionary of environment settings
env_settings: dict[str, type[LoggingConfig]] = {"dev": Dev, "test": Test, "prod": Prod}
# Select the environment settings based on the ENV variable
logging_config: Dev | Test | Prod = env_settings[os.environ.get("ENV", "dev").lower()]()
