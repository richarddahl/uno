# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework# core_library/logging/interfaces.py
import pytest
from uno.di.errors import (
    DIServiceCreationError,
    DIDIServiceCreationError,
    DuplicateRegistrationError,
    ScopeError,
    ContainerDisposedError,
    DIScopeDisposedError,
)


class DummyError(Exception):
    pass


def test_service_creation_error_context():
    err = DIServiceCreationError(interface=str, error=DummyError("fail"), foo="bar")
    assert "interface" in err.context
    assert "error_type" in err.context
    assert err.context["foo"] == "bar"


import pytest


@pytest.mark.asyncio
async def test_di_service_creation_error_context():
    err = await DIDIServiceCreationError.async_init(
        service_type=str,
        original_error=DummyError("fail"),
        container=None,
        service_key="str",
        dependency_chain=["A", "B"],
        foo="bar",
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


@pytest.mark.asyncio
async def test_scope_disposed_error():
    # Use the async_init factory method instead of the constructor
    err = await DIScopeDisposedError.async_init(
        message="Operation attempted on disposed scope",
        operation="resolve",
        scope_id="xyz",
        code="SCOPE_DISPOSED",
    )

    # Verify the error properties
    assert "Operation" in err.message
    assert "disposed scope" in err.message
    assert err.context.get("scope_id") == "xyz"
    assert err.context.get("operation") == "resolve"
    assert err.code == "DI_SCOPE_DISPOSED"
