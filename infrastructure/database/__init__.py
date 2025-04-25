# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
Database package for the Uno framework.

This package provides database connectivity, ORM integration, and session management.
"""

# Import the enhanced connection pool components
# Import database configuration
from uno.core.infrastructure.database.config import ConnectionConfig

# Import DB manager
from uno.core.infrastructure.database.db_manager import DBManager
from uno.core.infrastructure.database.enhanced_connection_pool import (
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
from uno.core.infrastructure.database.enhanced_pool_session import (
    EnhancedPooledSessionContext,
    EnhancedPooledSessionFactory,
    EnhancedPooledSessionOperationGroup,
    SessionPoolConfig,
    enhanced_pool_session,
)

# Import enhanced session utilities
from uno.core.infrastructure.database.enhanced_session import (
    EnhancedAsyncSessionContext,
    EnhancedAsyncSessionFactory,
    SessionOperationGroup,
    enhanced_async_session,
)

# Import error types
from uno.core.infrastructure.database.errors import (
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
from uno.core.infrastructure.database.optimizer_metrics import (
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
from uno.core.infrastructure.database.pg_optimizer_strategies import (
    PgIndexRecommendation,
    PgOptimizationStrategies,
    PgQueryOptimizer,
    add_pg_strategies,
    create_pg_optimizer,
)

# Import pooled session utilities
from uno.core.infrastructure.database.pooled_session import (
    PooledAsyncSessionContext,
    PooledAsyncSessionFactory,
    PooledSessionOperationGroup,
    pooled_async_session,
)

# Import query cache components
from uno.core.infrastructure.database.query_cache import (
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
from uno.core.infrastructure.database.query_optimizer import (
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
from uno.core.infrastructure.database.session import (
    AsyncSessionContext,
    AsyncSessionFactory,
    async_session,
)

# Register database errors
register_database_errors()

__all__ = [
    "AsyncSessionContext",
    # Base session
    "AsyncSessionFactory",
    # Query cache
    "CacheBackend",
    "CacheStrategy",
    "CachedResult",
    # Configuration
    "ConnectionConfig",
    # Enhanced connection pool
    "ConnectionPoolConfig",
    "ConnectionPoolStrategy",
    # DB Manager
    "DBManager",
    "DatabaseColumnNotFoundError",
    "DatabaseConfigError",
    "DatabaseConnectionError",
    "DatabaseConnectionPoolExhaustedError",
    "DatabaseConnectionTimeoutError",
    # Error types
    "DatabaseErrorCode",
    "DatabaseForeignKeyViolationError",
    "DatabaseIntegrityError",
    "DatabaseNotSupportedError",
    "DatabaseOperationalError",
    "DatabaseQueryError",
    "DatabaseQuerySyntaxError",
    "DatabaseQueryTimeoutError",
    "DatabaseResourceAlreadyExistsError",
    "DatabaseResourceNotFoundError",
    "DatabaseSessionError",
    "DatabaseSessionExpiredError",
    "DatabaseTableNotFoundError",
    "DatabaseTransactionConflictError",
    "DatabaseTransactionError",
    "DatabaseTransactionRollbackError",
    "DatabaseUniqueViolationError",
    "EnhancedAsyncConnectionManager",
    "EnhancedAsyncEnginePool",
    "EnhancedAsyncSessionContext",
    # Enhanced session
    "EnhancedAsyncSessionFactory",
    "EnhancedConnectionPool",
    "EnhancedPooledSessionContext",
    "EnhancedPooledSessionFactory",
    "EnhancedPooledSessionOperationGroup",
    "IndexRecommendation",
    "IndexType",
    "OptimizationConfig",
    "OptimizationLevel",
    "OptimizerMetricsCollector",
    "OptimizerMetricsMiddleware",
    # Optimizer metrics
    "OptimizerMetricsSnapshot",
    # PostgreSQL specific optimizer
    "PgIndexRecommendation",
    "PgOptimizationStrategies",
    "PgQueryOptimizer",
    "PooledAsyncSessionContext",
    # Pooled session
    "PooledAsyncSessionFactory",
    "PooledSessionOperationGroup",
    "QueryCache",
    "QueryCacheConfig",
    "QueryCacheKey",
    "QueryCacheStats",
    # Query optimizer
    "QueryComplexity",
    "QueryOptimizer",
    "QueryPlan",
    "QueryRewrite",
    "QueryStatistics",
    "SessionOperationGroup",
    # Enhanced pool session
    "SessionPoolConfig",
    "add_pg_strategies",
    "async_session",
    "cached",
    "cached_query",
    "clear_all_caches",
    "collect_optimizer_metrics",
    "create_pg_optimizer",
    "enhanced_async_connection",
    "enhanced_async_engine",
    "enhanced_async_session",
    "enhanced_pool_session",
    "get_connection_manager",
    "get_metrics_collector",
    "get_named_cache",
    "optimize_query",
    "optimized_query",
    "pooled_async_session",
    "set_default_cache",
    "set_metrics_collector",
    "track_query_performance",
    "with_query_metrics",
]
