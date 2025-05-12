"""
Test module for validating the migration from LoggerProtocol to LoggerProtocol.

This test ensures that the new logging system with LoggerProtocol and get_logger
works correctly and maintains compatibility with the legacy interfaces.
"""

import asyncio
import sys
from typing import Any

# Add the src directory to the path
sys.path.append("/Users/richarddahl/Code/uno/src")

import pytest
from uno.logging import LoggerProtocol, LogLevel, get_logger


class TestLoggingMigration:
    """Test suite for logging system migration."""

    @pytest.mark.asyncio
    async def test_get_logger_basic_functionality(self) -> None:
        """Test that get_logger provides a functional logger."""
        # Create a logger using the new get_logger function
        logger = get_logger("test_migration")

        # Verify it implements LoggerProtocol
        assert isinstance(logger, LoggerProtocol)

        # Test basic logging methods (these should not raise exceptions)
        await logger.debug("Debug message")
        await logger.info("Info message")
        await logger.warning("Warning message")
        await logger.error("Error message")
        await logger.critical("Critical message")

    @pytest.mark.asyncio
    async def test_logger_level_setting(self) -> None:
        """Test setting log levels on the logger."""
        logger = get_logger("test_levels")

        # Test setting different levels
        logger.set_level(LogLevel.DEBUG)
        await logger.debug("Should be visible at DEBUG level")

        logger.set_level(LogLevel.ERROR)
        await logger.debug("Should not be visible at ERROR level")
        await logger.error("Should be visible at ERROR level")

    @pytest.mark.asyncio
    async def test_logger_context_binding(self) -> None:
        """Test the context binding functionality."""
        logger = get_logger("test_context")

        # Test context manager
        with logger.context(request_id="123", user="test_user"):
            await logger.info("Log with context")

        # Test creating bound logger
        bound_logger = logger.bind(component="auth", subsystem="login")
        await bound_logger.info("Log from bound logger")

        # Test correlation ID
        traced_logger = logger.with_correlation_id("correlation-123")
        await traced_logger.info("Log with correlation ID")

    @pytest.mark.asyncio
    async def test_async_context(self) -> None:
        """Test logger in async context."""
        logger = get_logger("test_async")

        async def async_function() -> None:
            await logger.info("Log from async function")
            await asyncio.sleep(0.01)
            await logger.info("Log after await")

        # This should not raise any exceptions
        await async_function()


if __name__ == "__main__":
    # Run the tests directly if needed
    pytest.main(["-vvs", __file__])
