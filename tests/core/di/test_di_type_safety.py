"""
Tests for Uno DI: type safety and error handling
"""

import pytest
from uno.core.di.test_helpers import di_provider
from typing import Protocol, runtime_checkable

from uno.core.di.container import _ServiceResolver


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
    print(f"Registering IFoo: id={id(IFoo)}, repr={repr(IFoo)}")
    reg_result = resolver.register(IFoo, Foo)
    from uno.core.errors.result import Success, Failure
    if isinstance(reg_result, Failure):
        print(f"Registration failed: {reg_result.error}")
        assert False, f"Registration failed: {reg_result.error}"
    print(f"resolver._registrations keys after register: {[f'id={id(k)}, repr={repr(k)}' for k in resolver._registrations.keys()]}")
    print(f"Resolving IFoo: id={id(IFoo)}, repr={repr(IFoo)}")
    result = resolver.resolve(IFoo)
    print(f"Result from resolve: {result}")
    assert isinstance(result, Success)
    assert isinstance(result.value, Foo)


def test_register_wrong_type_raises():
    resolver = _ServiceResolver()
    result = resolver.register(IFoo, Bar)
    from uno.core.errors.definitions import ServiceRegistrationError
    from uno.core.errors.result import Failure
    assert isinstance(result, Failure)
    assert isinstance(result.error, ServiceRegistrationError)


def test_register_factory_wrong_return_type_raises():
    resolver = _ServiceResolver()

    def factory() -> Bar:
        return Bar()

    result = resolver.register(IFoo, factory)
    from uno.core.errors.definitions import ServiceRegistrationError
    from uno.core.errors.result import Failure
    assert isinstance(result, Failure)
    assert isinstance(result.error, ServiceRegistrationError)


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


def test_register_factory_correct_return_type(di_provider):
    class IFoo2:
        pass
    class Foo2(IFoo2):
        pass

    def factory() -> Foo2:
        return Foo2()

    # Should succeed
    di_provider._base_services.add_singleton(IFoo2, factory)


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
    result = resolver.resolve(A)
    from uno.core.errors.definitions import CircularDependencyError
    from uno.core.errors.result import Failure
    assert isinstance(result, Failure)
    assert isinstance(result.error, CircularDependencyError)
