# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
"""
Configuration module for Uno framework.

This module provides centralized configuration management for the application.
"""

from typing import Any, Type

from uno.infrastructure.di.service_collection import ServiceCollection
from uno.infrastructure.di.service_provider import ServiceProvider

# Import config modules
from .api import APIConfig, api_config
from .application import ApplicationConfig, application_config
from .database import DatabaseConfig, database_config
from .general import GeneralConfig, general_config
from .jwt import JWTConfig, get_jwt_config
from .security import SecurityConfig, security_config
from .vector_search import VectorSearchConfig, vector_search_config
from uno.infrastructure.sql.config import SQLConfig, sql_config

# Create a service collection for configuration services
services = ServiceCollection()

__all__ = [
    "APIConfig",
    "api_config",
    "ApplicationConfig",
    "application_config",
    "DatabaseConfig",
    "database_config",
    "GeneralConfig",
    "general_config",
    "JWTConfig",
    "get_jwt_config",
    "SecurityConfig",
    "security_config",
    "VectorSearchConfig",
    "vector_search_config",
    "SQLConfig",
    "sql_config",
    "services",
]


# Register all config instances
services.add_instance(APIConfig, api_config)
# Example: register a named config variant
services.add_instance(APIConfig, api_config, name="api.readonly")
services.add_instance(ApplicationConfig, application_config)
services.add_instance(DatabaseConfig, database_config)
# Example: register a named config variant
services.add_instance(DatabaseConfig, database_config, name="database.readonly")
services.add_instance(GeneralConfig, general_config)
services.add_instance(SecurityConfig, security_config)
services.add_instance(VectorSearchConfig, vector_search_config)
services.add_instance(SQLConfig, sql_config)

# NOTE: Strict DI mode: All configuration dependencies must be passed explicitly from the composition root.

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
        return get_jwt_config()
    elif config_type is SecurityConfig:
        return security_config
    elif config_type is VectorSearchConfig:
        return vector_search_config
    elif config_type is SQLConfig:
        return sql_config

    # Strict DI mode: Only statically registered configs are available here.
    raise ValueError(f"Configuration {config_type.__name__} not found. All configs must be injected explicitly.")
