"""Top-level pytest configuration for the uno framework."""

import asyncio
import os

import pytest
import pytest_asyncio

# First import modules for their side effects to ensure registries are populated
import uno.errors.base
import uno.config.errors
import uno.event_store.errors
import uno.event_bus.errors
import uno.injection.errors
import uno.logging.errors

# Then import and initialize registry
from uno.errors.registry import registry

# Then import specific symbols
from uno.errors.base import (
    INTERNAL_ERROR,
    ErrorCode,
    ErrorCategory,
    ErrorSeverity,
    UnoError,
)

# Configure asyncio to be less verbose
os.environ["PYTHONASYNCIODEBUG"] = "0"

pytest_plugins = [
    "pytest_asyncio",
]


# Fixture for event loop policy
@pytest.fixture(scope="session")
def event_loop_policy():
    """Return the event loop policy to use."""
    # You can customize this if needed, for example:
    # return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


# Skip integration tests by default unless explicitly requested
# Run with: pytest -m integration
def pytest_configure(config):
    """Configure pytest to recognize our custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (deselect with '-m "
        "not integration')",
    )


# Add a command line option to skip integration tests
def pytest_addoption(parser):
    """Add command line options for pytest."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests that require external services",
    )


# Skip integration tests by default
def pytest_collection_modifyitems(config, items):
    """Skip integration tests by default."""
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(
            reason="need --run-integration option to run"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
