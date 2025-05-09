"""
Events module configuration.

This module provides configuration settings for the events module.
"""

from typing import Literal

from pydantic import Field, SecretStr

from uno.config.base import UnoSettings


class EventsConfig(UnoSettings):
    """Configuration settings for the events module."""

    # Event bus settings
    event_bus_type: Literal["memory", "postgres", "redis"] = Field(
        "memory", description="Type of event bus to use", env="UNO_EVENTS_BUS_TYPE"
    )

    # Event store settings
    event_store_type: Literal["memory", "postgres", "json"] = Field(
        "memory", description="Type of event store to use", env="UNO_EVENTS_STORE_TYPE"
    )

    # Performance settings
    batch_size: int = Field(
        100,
        description="Maximum number of events to process in a batch",
        env="UNO_EVENTS_BATCH_SIZE",
    )

    # Publication settings
    retry_attempts: int = Field(
        3,
        description="Number of retry attempts for event publication",
        env="UNO_EVENTS_RETRY_ATTEMPTS",
    )

    retry_delay_ms: int = Field(
        500,
        description="Delay in milliseconds between retry attempts",
        env="UNO_EVENTS_RETRY_DELAY_MS",
    )

    # Database settings
    db_connection_string: SecretStr = Field(
        None,
        description="Connection string for the event store database",
        env="UNO_EVENTS_DB_CONNECTION",
    )

    # Handler settings
    parallel_handlers: bool = Field(
        False,
        description="Whether to run event handlers in parallel",
        env="UNO_EVENTS_PARALLEL_HANDLERS",
    )

    model_config = {"env_prefix": "UNO_EVENTS_"}
