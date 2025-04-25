"""
Pytest configuration for DI/provider tests: globally suppress all log output except for tests that explicitly capture/assert on logs.
This ensures silent test output and avoids interfering with caplog/capture-based tests.
"""
import logging
import pytest

@pytest.fixture(autouse=True, scope="session")
def suppress_all_logs():
    """Suppress all log output for DI/provider tests by default (root and noisy libraries)."""
    original_root_level = logging.getLogger().level
    original_asyncio_level = logging.getLogger("asyncio").level
    logging.getLogger().setLevel(logging.CRITICAL)
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)
    yield
    logging.getLogger().setLevel(original_root_level)
    logging.getLogger("asyncio").setLevel(original_asyncio_level)
