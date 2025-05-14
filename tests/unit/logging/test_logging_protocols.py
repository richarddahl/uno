import pytest
from uno.logging.protocols import LoggerProtocol, LoggerFactoryProtocol
from uno.logging.logger import UnoLogger
from uno.logging.factory import LoggerFactory

from tests.conftest_protocols import assert_implements_protocol


def test_logger_protocol_structural():
    logger = UnoLogger(name="uno.test")
    assert_implements_protocol(LoggerProtocol, logger)
    assert LoggerProtocol not in type(logger).__bases__


def test_logger_factory_protocol_structural():
    import inspect

    factory = LoggerFactory(container=None, settings=None)
    assert_implements_protocol(LoggerFactoryProtocol, factory)
    assert LoggerFactoryProtocol not in type(factory).__bases__
