import pytest
from uno.di.errors import (
    ServiceCreationError,
    DIServiceCreationError,
    ServiceNotRegisteredError,
    DIServiceNotFoundError,
    DuplicateRegistrationError,
    DICircularDependencyError,
    ScopeError,
    ContainerDisposedError,
    DIScopeDisposedError,
)

class DummyError(Exception):
    pass

def test_service_creation_error_context():
    err = ServiceCreationError(interface=str, error=DummyError("fail"), foo="bar")
    assert "interface" in err.context
    assert "error_type" in err.context
    assert err.context["foo"] == "bar"

import pytest

@pytest.mark.asyncio
async def test_di_service_creation_error_context():
    err = await DIServiceCreationError.async_init(
        service_type=str,
        original_error=DummyError("fail"),
        container=None,
        service_key="str",
        dependency_chain=["A", "B"],
        foo="bar"
    )
    assert "service_type" in err.context
    assert "dependency_chain" in err.context
    assert err.context["foo"] == "bar"

def test_duplicate_registration_error():
    err = DuplicateRegistrationError(interface=int)
    assert "interface_name" in err.context

def test_scope_error_with_context():
    err = ScopeError("fail", context={"foo": 1})
    err2 = err.with_context({"bar": 2})
    assert err2.context["foo"] == 1
    assert err2.context["bar"] == 2

def test_container_disposed_error():
    err = ContainerDisposedError("resolve")
    assert "operation" in err.context

def test_scope_disposed_error():
    err = DIScopeDisposedError("resolve", scope_id="xyz")
    assert "operation" in err.context
    assert err.context["scope_id"] == "xyz"
