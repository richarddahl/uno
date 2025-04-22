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
    assert resolver.resolve(Bar).msg == "bar"

def test_add_conditional_false():
    services = ServiceCollection()
    services.add_conditional(lambda: False, lambda sc: sc.add_singleton(Bar))
    resolver = services.build()
    with pytest.raises(FrameworkError):
        resolver.resolve(Bar)


def test_add_validation_passes():
    services = ServiceCollection()
    services.add_singleton(Foo)
    services.add_validation(lambda sc: None)
    resolver = services.build()
    assert resolver.resolve(Foo).value == 42


class Foo:
    def __init__(self):
        self.value = 42


def test_singleton_lifetime():
    services = ServiceCollection()
    services.add_singleton(Foo)
    resolver = services.build()
    f1 = resolver.resolve(Foo)
    f2 = resolver.resolve(Foo)
    assert f1 is f2


def test_transient_lifetime():
    services = ServiceCollection()
    services.add_transient(Foo)
    resolver = services.build()
    f1 = resolver.resolve(Foo)
    f2 = resolver.resolve(Foo)
    assert f1 is not f2


def test_scoped_lifetime_outside_scope_raises():
    services = ServiceCollection()
    services.add_scoped(Foo)
    resolver = services.build()
    with pytest.raises(FrameworkError):
        resolver.resolve(Foo)
