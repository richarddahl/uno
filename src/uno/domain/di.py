"""
Dependency injection registration extensions for the domain module.

This module provides extension methods to register domain services
with the DI container.
"""

from uno.di.container import Container
from uno.domain.config import DomainConfig
from uno.domain.repository import Repository
from uno.domain.event_sourced_repository import EventSourcedRepository
from uno.logging.protocols import LoggerProtocol


async def register_domain_services(container: Container) -> None:
    """
    Register all domain module services with the DI container.

    Args:
        container: The DI container to register services with
    """
    # Register configuration
    config = DomainConfig.from_env()
    await container.register_singleton(DomainConfig, lambda _: config)

    # Register repositories based on configuration
    # In the future, this could be made more dynamic based on config values
    await container.register_scoped(Repository, EventSourcedRepository)

    # Additional domain service registrations would go here
