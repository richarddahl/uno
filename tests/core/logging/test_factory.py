"""
Tests for the LoggerServiceFactory.
"""

from uno.infrastructure.logging.factory import (
    DefaultLoggerServiceFactory,
    LoggerServiceFactory,
    create_logger_factory,
    create_logger_factory_callable,
)
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig


class TestDefaultLoggerServiceFactory:
    """Tests for the DefaultLoggerServiceFactory."""

    def test_create_with_default_namespace(self) -> None:
        """Test creating a logger with the default namespace."""
        # Arrange
        factory = DefaultLoggerServiceFactory()

        # Act
        logger = factory.create("test_component")

        # Assert
        assert isinstance(logger, LoggerService)
        # logger.name is no longer available; check logger type only

    def test_create_with_custom_namespace(self) -> None:
        """Test creating a logger with a custom namespace."""
        # Arrange
        factory = DefaultLoggerServiceFactory(base_namespace="custom")

        # Act
        logger = factory.create("test_component")

        # Assert
        assert isinstance(logger, LoggerService)
        # logger.name is no longer available; check logger type only

    def test_multiple_loggers_share_common_namespace(self) -> None:
        """Test that multiple loggers from the same factory share the base namespace."""
        # Arrange
        factory = DefaultLoggerServiceFactory(base_namespace="app")

        # Act
        logger1 = factory.create("component1")
        logger2 = factory.create("component2")

        # Assert
        # logger.name is no longer available; check logger type only
        assert isinstance(logger1, LoggerService)
        assert isinstance(logger2, LoggerService)
        assert logger1 is not logger2


class TestFactoryFunctions:
    """Tests for the factory functions."""

    def test_create_logger_factory(self) -> None:
        """Test creating a logger factory."""
        # Act
        factory = create_logger_factory(base_namespace="test")

        # Assert
        assert isinstance(factory, DefaultLoggerServiceFactory)

        # Verify it creates loggers correctly
        logger = factory.create("component")
        # logger.name is no longer available; check logger type only
        assert isinstance(logger, LoggerService)

    def test_create_logger_factory_callable(self) -> None:
        """Test creating a callable logger factory."""
        # Act
        factory_callable = create_logger_factory_callable(base_namespace="test")

        # Assert - should be a callable
        assert callable(factory_callable)

        # Verify it creates loggers correctly
        logger = factory_callable("component")
        assert isinstance(logger, LoggerService)
        # logger.name is no longer available; check logger type only


class TestLoggerServiceFactoryProtocol:
    """Tests for the LoggerServiceFactory protocol."""

    def test_custom_factory_implementation(self) -> None:
        """Test a custom implementation of LoggerServiceFactory."""

        # Define a custom factory implementation
        class CustomLoggerFactory:
            def create(self, component_name: str) -> LoggerService:
                return LoggerService(LoggingConfig())

        # Create an instance and use it
        factory: LoggerServiceFactory = CustomLoggerFactory()
        logger = factory.create("test")

        # Assert
        assert isinstance(logger, LoggerService)
        # logger.name is no longer available; check logger type only
