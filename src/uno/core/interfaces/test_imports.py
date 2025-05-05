"""
Test that all public symbols in uno.core.interfaces.__all__ can be imported directly.
"""
import importlib
import pytest

MODULE = "uno.core.interfaces"

@pytest.mark.parametrize("symbol", [
    "ConfigProtocol",
    "DBManagerProtocol",
    "DTOManagerProtocol",
    "DatabaseProviderProtocol",
    "DomainRepositoryProtocol",
    "DomainServiceProtocol",
    "EventBusProtocol",
    "EventPublisherProtocol",
    "EventStoreProtocol",
    "HashServiceProtocol",
    "LoggerProtocol",
    "RepositoryProtocol",
    "SQLEmitterFactoryProtocol",
    "SQLExecutionProtocol",
    "ServiceProtocol",
    "UnitOfWorkProtocol",
])
def test_symbol_importable(symbol):
    mod = importlib.import_module(MODULE)
    assert hasattr(mod, symbol), f"{symbol} not found in {MODULE}"
    getattr(mod, symbol)  # Should not raise
