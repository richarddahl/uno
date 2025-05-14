import pytest
from uno.logging.protocols import LoggerProtocol, LoggerFactoryProtocol
from uno.logging.logger import UnoLogger
from uno.logging.factory import LoggerFactory

def test_logger_protocol_structural():
    logger = UnoLogger(name="uno.test")
    assert isinstance(logger, LoggerProtocol)
    # Should not inherit directly from Protocol
    assert LoggerProtocol not in type(logger).__bases__

def test_logger_factory_protocol_structural():
    import inspect
    factory = LoggerFactory(container=None, settings=None)
    assert isinstance(factory, LoggerFactoryProtocol)
    # Should not inherit directly from Protocol
    assert LoggerFactoryProtocol not in type(factory).__bases__
