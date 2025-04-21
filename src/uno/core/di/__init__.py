"""
Dependencies module for Uno framework.

This module provides a modern dependency injection system
to improve testability, maintainability, and decoupling of components.

The module offers a decorator-based approach to dependency management
with proper scope handling and automatic discovery of injectable services.
"""

# Interfaces
# Modern FastAPI integration is imported separately
# Database integration
from uno.core.di.database import (
    get_db_manager,
    get_db_session,
    get_domain_registry,
    get_domain_repository,
    get_domain_service,
    get_event_bus,
    get_event_publisher,
    get_raw_connection,
    get_repository,
    get_schema_manager,
    get_sql_emitter_factory,
    get_sql_execution_service,
)
from uno.core.di.interfaces import (
    DomainRepositoryProtocol,
    DomainServiceProtocol,
    EventBusProtocol,
    SchemaManagerProtocol,
    SQLEmitterFactoryProtocol,
    SQLExecutionProtocol,
    UnoConfigProtocol,
    UnoDatabaseProviderProtocol,
    UnoDBManagerProtocol,
    UnoRepositoryProtocol,
    UnoServiceProtocol,
)

# Implementations
from uno.core.di.repository import UnoRepository
from uno.core.di.service import CrudService, UnoService

# Vector search interfaces
from uno.core.di.vector_interfaces import (
    BatchVectorUpdateServiceProtocol,
    RAGServiceProtocol,
    VectorConfigServiceProtocol,
    VectorSearchServiceProtocol,
    VectorUpdateServiceProtocol,
)

# Vector search implementations
try:
    from uno.core.di.vector_provider import get_rag_service, get_vector_search_service
except ImportError:
    # Vector search components not available
    get_vector_search_service = None
    get_rag_service = None

# New modern DI system
from uno.core.di.modern_provider import (
    ServiceLifecycle,
    UnoServiceProvider,
    shutdown_services,
    get_service_provider as get_modern_provider,
    initialize_services as initialize_modern_services,
)
from uno.core.di.scoped_container import (
    ServiceCollection,
    ServiceResolver,
    ServiceScope,
    create_async_scope,
    create_scope,
    get_service,
)

# Testing utilities
import os

if os.environ.get("ENV") == "test":
    from uno.core.di.testing import (
        MockConfig,
        MockRepository,
        MockService,
        TestingContainer,
        TestSession,
        TestSessionProvider,
        configure_test_container,
    )


__all__ = [
    # Modern DI functionality uses decorator-based approach
    # Interfaces
    "UnoRepositoryProtocol",
    "UnoServiceProtocol",
    "UnoConfigProtocol",
    "UnoDatabaseProviderProtocol",
    "UnoDBManagerProtocol",
    "SQLEmitterFactoryProtocol",
    "SQLExecutionProtocol",
    "SchemaManagerProtocol",
    "DomainRepositoryProtocol",
    "DomainServiceProtocol",
    "EventBusProtocol",
    # Vector Search Interfaces
    "VectorSearchServiceProtocol",
    "RAGServiceProtocol",
    "VectorUpdateServiceProtocol",
    "BatchVectorUpdateServiceProtocol",
    "VectorConfigServiceProtocol",
    # Implementations
    "UnoRepository",
    "UnoService",
    "CrudService",
    # Modern FastAPI integration is in fastapi_integration module
    # Database integration
    "get_db_session",
    "get_raw_connection",
    "get_repository",
    "get_db_manager",
    "get_sql_emitter_factory",
    "get_sql_execution_service",
    "get_schema_manager",
    # Domain integration
    "get_event_bus",
    "get_event_publisher",
    "get_domain_registry",
    "get_domain_repository",
    "get_domain_service",
    # Modern service provider functionality is in UnoServiceProvider
    # Vector search implementations
    "get_vector_search_service",
    "get_rag_service",
]

# Add testing utilities if in test environment
if os.environ.get("ENV") == "test":
    __all__ += [
        "TestingContainer",
        "MockRepository",
        "MockConfig",
        "MockService",
        "TestSession",
        "TestSessionProvider",
        "configure_test_container",
    ]

# Add modern DI system if available
__all__ += [
    # New DI core
    "ServiceScope",
    "ServiceCollection",
    "ServiceResolver",
    "get_service",
    "create_scope",
    "create_async_scope",
    # Modern provider
    "UnoServiceProvider",
    "ServiceLifecycle",
    "get_modern_provider",
    "initialize_modern_services",
    "shutdown_services",
]
