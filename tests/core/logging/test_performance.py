import pytest
import time
from uno.core.logging.logger import LoggerService, LoggingConfig
from uno.core.logging.config_service import LoggingConfigService

@pytest.fixture
def logger_service():
    config = LoggingConfig()
    logger_service = LoggerService(config)
    import asyncio
    asyncio.run(logger_service.initialize())
    yield logger_service
    asyncio.run(logger_service.dispose())

def test_logger_creation_benchmark(benchmark):
    config = LoggingConfig()
    def create_logger():
        logger_service = LoggerService(config)
        import asyncio
        asyncio.run(logger_service.initialize())
        logger = logger_service.get_logger("bench.test")
        asyncio.run(logger_service.dispose())
        return logger
    benchmark(create_logger)

def test_log_message_throughput(benchmark, logger_service):
    logger = logger_service.get_logger("bench.throughput")
    def log_messages():
        for _ in range(1000):
            logger.info("Performance log message")
    benchmark(log_messages)

def test_config_reload_benchmark(benchmark, logger_service):
    config_service = LoggingConfigService(logger_service)
    def reload_config():
        config_service.update_config(LEVEL="DEBUG")
        config_service.update_config(LEVEL="INFO")
    benchmark(reload_config)
