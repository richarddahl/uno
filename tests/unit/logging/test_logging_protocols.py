import pytest
from uno.logging.protocols import LoggerProtocol, LoggerFactoryProtocol
from uno.logging.logger import UnoLogger
from uno.logging.factory import LoggerFactory

from tests.conftest_protocols import assert_implements_protocol  # updated import path


def test_logger_protocol_structural():
    logger = UnoLogger(name="uno.test")
    assert_implements_protocol(LoggerProtocol, logger)


def test_logger_factory_protocol_structural():
    factory = LoggerFactory(container=None, settings=None)
    assert_implements_protocol(LoggerFactoryProtocol, factory)
