# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework

import pytest

from uno.core.di.container import ServiceCollection
from uno.core.errors.base import FrameworkError

class Bar:
    def __init__(self):
        self.msg = "bar"

def test_add_conditional_true():
    services = ServiceCollection()
    services.add_conditional(lambda: True, lambda sc: sc.add_singleton(Bar))
    resolver = services.build()
    result = resolver.resolve(Bar)
    from uno.core.errors.result import Success
    assert isinstance(result, Success)
    assert result.value.msg == "bar"

def test_add_conditional_false():
    services = ServiceCollection()
    services.add_conditional(lambda: False, lambda sc: sc.add_singleton(Bar))
    resolver = services.build()
    result = resolver.resolve(Bar)
    from uno.core.errors.result import Failure
    from uno.core.errors.definitions import ServiceNotFoundError
    assert isinstance(result, Failure)
    assert isinstance(result.error, ServiceNotFoundError)


def test_add_validation_passes():
    services = ServiceCollection()
    services.add_singleton(Foo)
    services.add_validation(lambda sc: None)
    resolver = services.build()
    result = resolver.resolve(Foo)
    from uno.core.errors.result import Success
    assert isinstance(result, Success)
    assert result.value.value == 42


class Foo:
    def __init__(self):
        self.value = 42


def test_singleton_lifetime():
    services = ServiceCollection()
    services.add_singleton(Foo)
    resolver = services.build()
    r1 = resolver.resolve(Foo)
    r2 = resolver.resolve(Foo)
    from uno.core.errors.result import Success
    assert isinstance(r1, Success)
    assert isinstance(r2, Success)
    assert r1.value is r2.value


def test_transient_lifetime():
    services = ServiceCollection()
    services.add_transient(Foo)
    resolver = services.build()
    r1 = resolver.resolve(Foo)
    r2 = resolver.resolve(Foo)
    from uno.core.errors.result import Success
    assert isinstance(r1, Success)
    assert isinstance(r2, Success)
    assert r1.value is not r2.value


def test_scoped_lifetime_outside_scope_raises():
    services = ServiceCollection()
    services.add_scoped(Foo)
    resolver = services.build()
    result = resolver.resolve(Foo)
    from uno.core.errors.result import Failure
    from uno.core.errors.definitions import ScopeError
    assert isinstance(result, Failure)
    assert isinstance(result.error, ScopeError)
