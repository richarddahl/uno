"""
Tests for Uno DI: type safety and error handling
"""

from typing import Protocol, runtime_checkable

import pytest

from uno.core.di._internal import CircularDependencyError, ServiceRegistrationError
from uno.core.di.container import _ServiceResolver
from uno.core.errors.base import FrameworkError


@runtime_checkable
class IFoo(Protocol):
    def foo(self) -> str: ...


class Foo(IFoo):
    def foo(self) -> str:
        return "foo"


class Bar:
    pass


def test_register_and_resolve_type_safe():
    resolver = _ServiceResolver()
    resolver.register(IFoo, Foo)
    # Should raise FrameworkError due to missing required parameters
    with pytest.raises(FrameworkError):
        resolver.resolve(IFoo)


def test_register_wrong_type_raises():
    resolver = _ServiceResolver()
    with pytest.raises(ServiceRegistrationError):
        resolver.register(IFoo, Bar)


def test_register_factory_wrong_return_type_raises():
    resolver = _ServiceResolver()

    def factory() -> Bar:
        return Bar()

    with pytest.raises(ServiceRegistrationError):
        resolver.register(IFoo, factory)


def test_register_protocol_structural_check():
    from typing import Protocol, runtime_checkable

    @runtime_checkable
    class Proto(Protocol):
        def foo(self) -> int: ...

    class Impl:
        def foo(self) -> int:
            return 42

    class WrongImpl:
        def bar(self) -> int:
            return 0

    resolver = _ServiceResolver()
    # Should succeed
    resolver.register(Proto, Impl)
    # Should fail
    with pytest.raises(ServiceRegistrationError):
        resolver.register(Proto, WrongImpl)


def test_register_factory_correct_return_type():
    resolver = _ServiceResolver()

    class IFoo2:
        pass

    class Foo2(IFoo2):
        pass

    def factory() -> Foo2:
        return Foo2()

    # Should succeed
    resolver.register(IFoo2, factory)


def test_circular_dependency_raises():
    resolver = _ServiceResolver()

    class A:
        def __init__(self, b: "B"):
            pass

    class B:
        def __init__(self, a: "A"):
            pass

    resolver.register(A, A)
    resolver.register(B, B)
    # Simulate circular dependency resolution
    with pytest.raises(CircularDependencyError):
        resolver.resolve(A)
