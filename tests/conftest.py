"""Pytest configuration and fixtures for event store tests."""

import asyncio
import os
from typing import AsyncIterator, Any, Dict, TypeVar, Generic, Optional, Generator

import pytest
import pytest_asyncio
from pydantic import BaseModel

# Configure asyncio to be less verbose
os.environ["PYTHONASYNCIODEBUG"] = "0"


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
