"""
Domain module configuration.

This module provides configuration settings for the domain module.
"""

from pydantic import Field

from uno.config.base import UnoSettings


class DomainConfig(UnoSettings):
    """Configuration settings for the domain module."""

    # General domain settings
    snapshot_frequency: int = Field(
        100,
        description="Number of events after which to create a snapshot",
        env="UNO_DOMAIN_SNAPSHOT_FREQUENCY",
    )

    max_events_per_aggregate: int = Field(
        1000,
        description="Maximum number of events per aggregate",
        env="UNO_DOMAIN_MAX_EVENTS",
    )

    # Business rule settings
    strict_validation: bool = Field(
        True,
        description="Whether to enforce strict validation rules",
        env="UNO_DOMAIN_STRICT_VALIDATION",
    )

    # Concurrency settings
    optimistic_concurrency: bool = Field(
        True,
        description="Whether to use optimistic concurrency control",
        env="UNO_DOMAIN_OPTIMISTIC_CONCURRENCY",
    )

    model_config = {"env_prefix": "UNO_DOMAIN_"}
