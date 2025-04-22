# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
import asyncio

import pytest

from uno.core.di.container import (
    ServiceCollection,
    ServiceContainer,
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


def test_scoped_lifetime_within_scope():
    services = ServiceCollection()
    services.add_scoped(Foo)
    resolver = services.build()
    with resolver.create_scope("scope1") as scope_resolver:
        f1 = scope_resolver.resolve(Foo)
        f2 = scope_resolver.resolve(Foo)
        assert f1 is f2
    with resolver.create_scope("scope2") as scope_resolver2:
        f3 = scope_resolver2.resolve(Foo)
        assert f3 is not f1


def test_initialize_and_global_container():
    services = ServiceCollection()
    services.add_singleton(Foo)
    resolver = ServiceContainer.initialize(services)
    f_global = ServiceContainer.get().resolve(Foo)
    assert f_global is resolver.resolve(Foo)


def test_get_scoped_service_async():
    services = ServiceCollection()
    services.add_scoped(Foo)
    ServiceContainer.initialize(services)

    async def runner():
        async with ServiceContainer.create_async_scope() as scope:
            foo = scope.resolve(Foo)
            assert isinstance(foo, Foo)

    asyncio.get_event_loop().run_until_complete(runner())
