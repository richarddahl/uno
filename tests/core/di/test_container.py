# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework

import pytest

from uno.core.di.container import (
    ServiceCollection,
)


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
    with pytest.raises(ValueError):
        resolver.resolve(Foo)




