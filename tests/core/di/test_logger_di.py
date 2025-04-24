import pytest
import asyncio
from uno.core.di.container import ServiceCollection
from uno.core.logging.logger import LoggerService, LoggingConfig
from uno.core.logging.config_service import LoggingConfigService

def test_logger_service_di_integration():
    sc = ServiceCollection()
    sc.add_singleton(LoggingConfig, implementation=LoggingConfig)
    resolver = sc.build()
    config_result = resolver.resolve(LoggingConfig)
    if hasattr(config_result, "value"):
        config = config_result.value
    else:
        raise AssertionError(f"DI resolution failed for LoggingConfig: {config_result}")
    def logger_service_factory():
        return LoggerService(config)
    sc.add_singleton(LoggerService, implementation=logger_service_factory)
    resolver = sc.build()
    result = resolver.resolve(LoggerService)
    if hasattr(result, "value"):
        logger_service = result.value
    else:
        raise AssertionError(f"DI resolution failed: {result}")
    asyncio.run(logger_service.initialize())
    assert isinstance(logger_service, LoggerService)
    logger = logger_service.get_logger("uno.test")
    logger.info("DI logger integration works!")
    # Should be able to update config via LoggingConfigService
    config_service = LoggingConfigService(logger_service)
    new_config = config_service.update_config(LEVEL="DEBUG")
    assert new_config.LEVEL == "DEBUG"
    # LoggerService should reflect the new config
    assert logger_service._config.LEVEL == "DEBUG"

@pytest.mark.asyncio
async def test_logger_service_lifecycle():
    sc = ServiceCollection()
    sc.add_singleton(LoggingConfig, implementation=LoggingConfig)
    resolver = sc.build()
    config_result = resolver.resolve(LoggingConfig)
    if hasattr(config_result, "value"):
        config = config_result.value
    else:
        raise AssertionError(f"DI resolution failed for LoggingConfig: {config_result}")
    def logger_service_factory():
        return LoggerService(config)
    sc.add_singleton(LoggerService, implementation=logger_service_factory)
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
