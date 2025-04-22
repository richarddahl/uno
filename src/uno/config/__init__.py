# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
from uno.core.di.container import ServiceCollection

from .api import APIConfig, api_config
from .application import ApplicationConfig, application_config
from .database import DatabaseConfig, database_config
from .general import GeneralConfig, general_config
from .jwt import JWTConfig, jwt_config
from .logging import LoggingConfig, logging_config
from .security import SecurityConfig, security_config
from .vector_search import VectorSearchConfig, vector_search_config

services = ServiceCollection()
services.add_singleton(APIConfig, api_config)
services.add_singleton(ApplicationConfig, application_config)
services.add_singleton(DatabaseConfig, database_config)
services.add_singleton(GeneralConfig, general_config)
services.add_singleton(JWTConfig, jwt_config)
services.add_singleton(LoggingConfig, logging_config)
services.add_singleton(SecurityConfig, security_config)
services.add_singleton(VectorSearchConfig, vector_search_config)


def get_config_provider():
    from uno.core.di.provider import get_service_provider

    return get_service_provider()
