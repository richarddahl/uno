"""
Domain module configuration.

This module provides configuration settings for the domain module.
"""

from pydantic import Field

from uno.config.base import Config


class DomainConfig(Config):
    """Configuration settings for the domain module."""

    # General domain settings
    snapshot_frequency: int = Field(
        default=100,
        description="Number of events after which to create a snapshot",
        validation_alias="UNO_DOMAIN_SNAPSHOT_FREQUENCY",
    )

    max_events_per_aggregate: int = Field(
        default=1000,
        description="Maximum number of events per aggregate",
        validation_alias="UNO_DOMAIN_MAX_EVENTS",
    )

    # Business rule settings
    strict_validation: bool = Field(
        default=True,
        description="Whether to enforce strict validation rules",
        validation_alias="UNO_DOMAIN_STRICT_VALIDATION",
    )

    # Concurrency settings
    optimistic_concurrency: bool = Field(
        default=True,
        description="Whether to use optimistic concurrency control",
        validation_alias="UNO_DOMAIN_OPTIMISTIC_CONCURRENCY",
    )

    model_config = {"env_prefix": "UNO_DOMAIN_"}
