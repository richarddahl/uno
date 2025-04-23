# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
"""
Configuration module for Uno framework.

This module provides centralized configuration management for the application.
"""

from typing import Any

from uno.core.di.container import ServiceCollection
from uno.core.di.provider import get_service_provider

# Import config modules
from .api import APIConfig, api_config
from .application import ApplicationConfig, application_config
from .database import DatabaseConfig, database_config
from .general import GeneralConfig, general_config
from .jwt import JWTConfig, jwt_config
from .security import SecurityConfig, security_config
from .vector_search import VectorSearchConfig, vector_search_config

# Create a service collection for configuration services
services = ServiceCollection()

# Register all config instances
services.add_singleton(APIConfig, api_config)
# Example: register a named config variant
services.add_singleton(APIConfig, api_config, name="readonly")
services.add_singleton(ApplicationConfig, application_config)
services.add_singleton(DatabaseConfig, database_config)
# Example: register a named config variant
services.add_singleton(DatabaseConfig, database_config, name="readonly")
services.add_singleton(GeneralConfig, general_config)
services.add_singleton(JWTConfig, jwt_config)
services.add_singleton(SecurityConfig, security_config)
services.add_singleton(VectorSearchConfig, vector_search_config)


def get_config_provider():
    """
    Get the service provider for configuration.
    
    This ensures the configuration services are properly registered with
    the global service provider.
    
    Returns:
        The global service provider with configs registered
    """
    provider = get_service_provider()
    
    # Only configure if not already initialized
    if not provider.is_initialized():
        provider.configure_services(services)
    
    return provider


def get_config(config_type: type[Any]) -> Any:
    """
    Get a configuration instance by type.
    
    This is a convenience function for getting configuration values without
    going through the full DI system.
    
    Args:
        config_type: The configuration class to get
        
    Returns:
        An instance of the requested configuration class
    """
    # Simple lookup for common configs to avoid DI overhead for simple cases
    if config_type is GeneralConfig:
        return general_config
    elif config_type is APIConfig:
        return api_config
    elif config_type is ApplicationConfig:
        return application_config
    elif config_type is DatabaseConfig:
        return database_config
    elif config_type is JWTConfig:
        return jwt_config
    elif config_type is SecurityConfig:
        return security_config
    elif config_type is VectorSearchConfig:
        return vector_search_config
    
    # Fall back to DI system for other configs
    try:
        provider = get_config_provider()
        if provider.is_initialized():
            return provider.get_service(config_type)
        else:
            raise RuntimeError("Service provider not initialized")
    except Exception as e:
        raise ValueError(f"Configuration {config_type.__name__} not found: {e!s}")
