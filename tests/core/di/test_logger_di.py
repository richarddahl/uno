import asyncio

import pytest

from uno.infrastructure.di.container import ServiceCollection
from uno.infrastructure.logging.config_service import LoggingConfigService
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig


def test_logger_service_di_integration() -> None:
    sc = ServiceCollection()
    config = LoggingConfig()
    sc.add_singleton(LoggingConfig, implementation=config)
    sc.add_singleton(
        LoggerService,
        implementation=lambda: LoggerService(LoggingConfig(CONSOLE_OUTPUT=False)),
    )
    resolver = sc.build()
    result = resolver.resolve(LoggerService)
    if hasattr(result, "value"):
        logger_service: LoggerService = result.value  # type: ignore
    else:
        raise AssertionError(f"DI resolution failed: {result}")
    asyncio.run(logger_service.initialize())
    assert isinstance(logger_service, LoggerService)
    logger = logger_service.get_logger("uno.test")
    logger.info("DI logger integration works!")
    # Should be able to update config via LoggingConfigService
    config_service = LoggingConfigService(logger_service)
    update_result = config_service.update_config(LEVEL="DEBUG")
    from uno.core.errors.result import Success

    assert isinstance(update_result, Success)
    new_config: LoggingConfig = update_result.value
    assert new_config.LEVEL == "DEBUG"
    # LoggerService should reflect the new config
    assert logger_service._config == new_config


@pytest.mark.asyncio
async def test_logger_service_lifecycle() -> None:
    sc = ServiceCollection()
    config = LoggingConfig()
    sc.add_singleton(LoggingConfig, implementation=config)
    sc.add_singleton(
        LoggerService,
        implementation=lambda: LoggerService(LoggingConfig(CONSOLE_OUTPUT=False)),
    )
    resolver = sc.build()
    result = resolver.resolve(LoggerService)
    if hasattr(result, "value"):
        logger_service = result.value
    else:
        raise AssertionError(f"DI resolution failed: {result}")
    await logger_service.initialize()
    logger = logger_service.get_logger("uno.lifecycle")
    logger.info("LoggerService initialized!")
    await logger_service.dispose()
    # After dispose, logger cache should be cleared
    assert not logger_service._loggers
