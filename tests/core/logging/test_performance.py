import pytest

from tests.core.logging.suppress_output import suppress_stdout_stderr
from uno.core.logging.config_service import LoggingConfigService
from uno.core.logging.logger import LoggerService, LoggingConfig


@pytest.fixture
def logger_service():
    # Force CONSOLE_OUTPUT=False to prevent all stdout logging
    config = LoggingConfig(CONSOLE_OUTPUT=False)
    logger_service = LoggerService(config)
    import asyncio

    asyncio.run(logger_service.initialize())
    yield logger_service
    asyncio.run(logger_service.dispose())


def test_logger_creation_benchmark(benchmark):
    def create_logger():
        # Always disable console output for test loggers
        logger_service = LoggerService(LoggingConfig(CONSOLE_OUTPUT=False))
        import asyncio

        with suppress_stdout_stderr():
            asyncio.run(logger_service.initialize())
            logger = logger_service.get_logger("bench.test")
            asyncio.run(logger_service.dispose())
        return logger

    benchmark(create_logger)


def test_log_message_throughput(benchmark, logger_service):
    logger = logger_service.get_logger("bench.throughput")

    def log_messages():
        with suppress_stdout_stderr():
            for _ in range(1000):
                logger.info("Performance log message")

    benchmark(log_messages)


def test_config_reload_benchmark(benchmark, logger_service):
    config_service = LoggingConfigService(logger_service)

    def reload_config():
        with suppress_stdout_stderr():
            config_service.update_config(LEVEL="DEBUG")
            config_service.update_config(LEVEL="INFO")

    benchmark(reload_config)
