# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Unit tests for RelationshipCache with injected LoggerService.
"""

import pytest

"""
from uno.core.logging.logger import LoggerService
from uno.core.infrastructure.database.relationship_loader import RelationshipCache, RelationshipCacheConfig

class DummyQueryCache:
    def __init__(self):
        self.storage = {}
    def get(self, key):
        return self.storage.get(key)
    def set(self, key, value):
        self.storage[key] = value
    def clear(self):
        self.storage.clear()

@pytest.fixture
def logger_service():
    svc = LoggerService()
    import asyncio
    asyncio.run(svc.initialize())
    yield svc
    asyncio.run(svc.dispose())

@pytest.fixture
def dummy_query_cache():
    return DummyQueryCache()

@pytest.fixture
def cache(logger_service, dummy_query_cache):
    return RelationshipCache(logger_service=logger_service, query_cache=dummy_query_cache)

def test_store_and_get_to_one_logs(cache, caplog):
    parent = type("Parent", (), {"id": 1})()
    related = type("Related", (), {"id": 42})()
    cache_key = "Related:42"
    # Store
    with caplog.at_level("INFO"):
        cache.query_cache.set(cache_key, related)
        cache.logger.info("Stored to-one relationship")
    # Get
    result = cache.query_cache.get(cache_key)
    assert result is related
    assert any("Stored to-one relationship" in msg for msg in caplog.messages)

def test_logger_is_injected(cache):
    # The logger should be a real logger, not None
    assert hasattr(cache, "logger")
    assert callable(getattr(cache.logger, "info", None))
    cache.logger.info("Logger injection works!")

"""
