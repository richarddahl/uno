import pytest
from uno.logging.scope import LoggerScope
from uno.logging.factory import LoggerFactory
from uno.logging.scope import LoggerScopeProtocol
from uno.logging.factory import LoggerFactoryProtocol


def test_logger_scope_compliance():
    assert issubclass(LoggerScope, LoggerScopeProtocol)
    assert isinstance(LoggerScope(None), LoggerScopeProtocol)


def test_logger_factory_compliance():
    assert issubclass(LoggerFactory, LoggerFactoryProtocol)
    assert isinstance(LoggerFactory(None, None), LoggerFactoryProtocol)
