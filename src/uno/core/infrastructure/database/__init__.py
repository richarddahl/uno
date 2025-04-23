# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Database package for the Uno framework.

This package provides database connectivity, ORM integration, and session management.
"""

# Import the enhanced connection pool components
# Import database configuration
from uno.infrastructure.database.config import ConnectionConfig

# Import DB manager
from uno.infrastructure.database.db_manager import DBManager
from uno.infrastructure.database.enhanced_connection_pool import (
    ConnectionPoolConfig,
    ConnectionPoolStrategy,
    EnhancedAsyncConnectionManager,
    EnhancedAsyncEnginePool,
    EnhancedConnectionPool,
    enhanced_async_connection,
    enhanced_async_engine,
    get_connection_manager,
)

# Import the enhanced pool session components
from uno.infrastructure.database.enhanced_pool_session import (
    EnhancedPooledSessionContext,
    EnhancedPooledSessionFactory,
    EnhancedPooledSessionOperationGroup,
    SessionPoolConfig,
    enhanced_pool_session,
)

# Import enhanced session utilities
from uno.infrastructure.database.enhanced_session import (
    EnhancedAsyncSessionContext,
    EnhancedAsyncSessionFactory,
    SessionOperationGroup,
    enhanced_async_session,
)

# Import error types
from uno.infrastructure.database.errors import (
    DatabaseColumnNotFoundError,
    DatabaseConfigError,
    DatabaseConnectionError,
    DatabaseConnectionPoolExhaustedError,
    DatabaseConnectionTimeoutError,
    DatabaseErrorCode,
    DatabaseForeignKeyViolationError,
    DatabaseIntegrityError,
    DatabaseNotSupportedError,
    DatabaseOperationalError,
    DatabaseQueryError,
    DatabaseQuerySyntaxError,
    DatabaseQueryTimeoutError,
    DatabaseResourceAlreadyExistsError,
    DatabaseResourceNotFoundError,
    DatabaseSessionError,
    DatabaseSessionExpiredError,
    DatabaseTableNotFoundError,
    DatabaseTransactionConflictError,
    DatabaseTransactionError,
    DatabaseTransactionRollbackError,
    DatabaseUniqueViolationError,
    register_database_errors,
)

# Import optimizer metrics components
from uno.infrastructure.database.optimizer_metrics import (
    OptimizerMetricsCollector,
    OptimizerMetricsMiddleware,
    OptimizerMetricsSnapshot,
    collect_optimizer_metrics,
    get_metrics_collector,
    set_metrics_collector,
    track_query_performance,
    with_query_metrics,
)

# Import PostgreSQL-specific optimizer components
from uno.infrastructure.database.pg_optimizer_strategies import (
    PgIndexRecommendation,
    PgOptimizationStrategies,
    PgQueryOptimizer,
    add_pg_strategies,
    create_pg_optimizer,
)

# Import pooled session utilities
from uno.infrastructure.database.pooled_session import (
    PooledAsyncSessionContext,
    PooledAsyncSessionFactory,
    PooledSessionOperationGroup,
    pooled_async_session,
)

# Import query cache components
from uno.infrastructure.database.query_cache import (
    CacheBackend,
    CachedResult,
    CacheStrategy,
    QueryCache,
    QueryCacheConfig,
    QueryCacheKey,
    QueryCacheStats,
    cached,
    cached_query,
    clear_all_caches,
    get_named_cache,
    set_default_cache,
)

# Import query optimizer components
from uno.infrastructure.database.query_optimizer import (
    IndexRecommendation,
    IndexType,
    OptimizationConfig,
    OptimizationLevel,
    QueryComplexity,
    QueryOptimizer,
    QueryPlan,
    QueryRewrite,
    QueryStatistics,
    optimize_query,
    optimized_query,
)

# Import base session utilities
from uno.infrastructure.database.session import (
    AsyncSessionContext,
    AsyncSessionFactory,
    async_session,
)

# Register database errors
register_database_errors()

__all__ = [
    # Enhanced connection pool
    'ConnectionPoolConfig',
    'ConnectionPoolStrategy',
    'EnhancedConnectionPool',
    'EnhancedAsyncEnginePool',
    'EnhancedAsyncConnectionManager',
    'get_connection_manager',
    'enhanced_async_engine',
    'enhanced_async_connection',
    
    # Enhanced pool session
    'SessionPoolConfig',
    'EnhancedPooledSessionFactory',
    'EnhancedPooledSessionContext',
    'enhanced_pool_session',
    'EnhancedPooledSessionOperationGroup',
    
    # Base session
    'AsyncSessionFactory',
    'AsyncSessionContext',
    'async_session',
    
    # Enhanced session
    'EnhancedAsyncSessionFactory',
    'EnhancedAsyncSessionContext',
    'enhanced_async_session',
    'SessionOperationGroup',
    
    # Pooled session
    'PooledAsyncSessionFactory',
    'PooledAsyncSessionContext',
    'pooled_async_session',
    'PooledSessionOperationGroup',
    
    # Query cache
    'CacheBackend',
    'CacheStrategy',
    'QueryCacheConfig',
    'QueryCacheStats',
    'QueryCacheKey',
    'CachedResult',
    'QueryCache',
    'cached',
    'cached_query',
    'get_named_cache',
    'set_default_cache',
    'clear_all_caches',
    
    # Query optimizer
    'QueryComplexity',
    'OptimizationLevel',
    'IndexType',
    'QueryPlan',
    'IndexRecommendation',
    'QueryRewrite',
    'QueryStatistics',
    'OptimizationConfig',
    'QueryOptimizer',
    'optimize_query',
    'optimized_query',
    
    # PostgreSQL specific optimizer
    'PgIndexRecommendation',
    'PgOptimizationStrategies',
    'PgQueryOptimizer',
    'add_pg_strategies',
    'create_pg_optimizer',
    
    # Optimizer metrics
    'OptimizerMetricsSnapshot',
    'OptimizerMetricsCollector',
    'OptimizerMetricsMiddleware',
    'track_query_performance',
    'with_query_metrics',
    'get_metrics_collector',
    'set_metrics_collector',
    'collect_optimizer_metrics',
    
    # Configuration
    'ConnectionConfig',
    
    # DB Manager
    'DBManager',
    
    # Error types
    'DatabaseErrorCode',
    'DatabaseConnectionError',
    'DatabaseConnectionTimeoutError',
    'DatabaseConnectionPoolExhaustedError',
    'DatabaseQueryError',
    'DatabaseQueryTimeoutError',
    'DatabaseQuerySyntaxError',
    'DatabaseTransactionError',
    'DatabaseTransactionRollbackError',
    'DatabaseTransactionConflictError',
    'DatabaseIntegrityError',
    'DatabaseUniqueViolationError',
    'DatabaseForeignKeyViolationError',
    'DatabaseResourceNotFoundError',
    'DatabaseResourceAlreadyExistsError',
    'DatabaseTableNotFoundError',
    'DatabaseColumnNotFoundError',
    'DatabaseSessionError',
    'DatabaseSessionExpiredError',
    'DatabaseConfigError',
    'DatabaseOperationalError',
    'DatabaseNotSupportedError',
]