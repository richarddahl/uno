# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT

import logging
from unittest.mock import patch

import pytest

from uno.core.logging.logger import (
    get_logger,
    logger_service,
    LoggingConfig,
)


@pytest.fixture(autouse=True)
def clear_logger_state():
    # Reset the logger_service between tests
    import asyncio
    asyncio.run(logger_service.dispose())
    # Re-initialize to default config for isolation
    asyncio.run(logger_service.initialize())


def test_singleton_logger():
    logger1 = get_logger()
    logger2 = get_logger()
    assert logger1 is logger2


def test_named_logger_singleton():
    logger_a1 = get_logger("a")
    logger_a2 = get_logger("a")
    logger_b = get_logger("b")
    assert logger_a1 is logger_a2
    assert logger_a1 is not logger_b


def test_logger_has_correct_type():
    logger = get_logger()
    assert isinstance(logger, logging.Logger)


# The root logger is now configured by LoggerService.initialize().
# The following test is not needed with the new DI-based setup, as initialization is explicit and idempotent.
# def test_configure_root_logger_called_once():
#     with patch.object(logging, "basicConfig") as mock_basic_config:
#         get_logger()
#         get_logger()
#         mock_basic_config.assert_called_once()


def test_logging_output_to_stream_with_caplog(caplog):
    logger = get_logger("pytest.test")
    with caplog.at_level(logging.INFO, logger="pytest.test"):
        logger.info("hello world")
    assert any("hello world" in message for message in caplog.messages)


def test_logging_output_with_caplog(caplog):
    logger = get_logger("pytest.test")
    with caplog.at_level(logging.INFO, logger="pytest.test"):
        logger.info("hello world")
    assert any("hello world" in m for m in caplog.messages)


def test_logger_level_and_format():
    logger = get_logger("test2")
    assert logger.level == logging.NOTSET  # child loggers default to NOTSET
    root_logger = logging.getLogger()
    assert root_logger.level in (logging.INFO, logging.DEBUG, logging.WARNING)


def test_logger_thread_safety():
    import threading

    results = []

    def getlog():
        results.append(get_logger("thread"))

    threads = [threading.Thread(target=getlog) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(logger_instance is results[0] for logger_instance in results)


def test_logger_multiple_names():
    names = ["uno", "uno.db", "uno.api"]
    loggers = [get_logger(n) for n in names]
    for i, logger in enumerate(loggers):
        for j, logger2 in enumerate(loggers):
            if i == j:
                assert logger is logger2
            else:
                assert logger is not logger2


def test_logger_reconfiguration():
    logger = get_logger("uno")
    old_config = logger_service._config
    new_config = LoggingConfig(LEVEL="DEBUG")
    import asyncio
    # Dispose and re-initialize with new config
    asyncio.run(logger_service.dispose())
    logger_service._config = new_config
    asyncio.run(logger_service.initialize())
    logger2 = get_logger("uno")
    assert logger is logger2
    # Restore old config
    asyncio.run(logger_service.dispose())
    logger_service._config = old_config
    asyncio.run(logger_service.initialize())
