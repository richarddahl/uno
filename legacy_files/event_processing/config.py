"""
Events module configuration.

This module provides configuration settings for the events module.
"""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import SettingsConfigDict

from uno.config.base import Config


class EventsConfig(Config):
    """Configuration settings for the events module."""

    # Event bus config
    event_bus_type: Literal["memory", "postgres", "redis"] = Field(
        default="memory",
        description="Type of event bus to use",
        validation_alias="UNO_EVENTS_BUS_TYPE",
    )

    # Event store config
    event_store_type: Literal["memory", "postgres", "json"] = Field(
        default="memory",
        description="Type of event store to use",
        validation_alias="UNO_EVENTS_STORE_TYPE",
    )

    # Performance config
    batch_size: int = Field(
        100,
        description="Maximum number of events to process in a batch",
        validation_alias="UNO_EVENTS_BATCH_SIZE",
    )

    # Publication config
    retry_attempts: int = Field(
        3,
        description="Number of retry attempts for event publication",
        validation_alias="UNO_EVENTS_RETRY_ATTEMPTS",
    )

    retry_delay_ms: int = Field(
        default=500,
        description="Delay in milliseconds between retry attempts",
        validation_alias="UNO_EVENTS_RETRY_DELAY_MS",
    )

    # Database config
    db_connection_string: SecretStr | None = Field(
        default=None,
        description="Connection string for the event store database",
        validation_alias="UNO_EVENTS_DB_CONNECTION",
    )

    # Handler config
    parallel_handlers: bool = Field(
        default=False,
        description="Whether to run event handlers in parallel",
        validation_alias="UNO_EVENTS_PARALLEL_HANDLERS",
    )  # No change needed, already correct

    model_config = SettingsConfigDict(env_prefix="UNO_EVENTS_")
