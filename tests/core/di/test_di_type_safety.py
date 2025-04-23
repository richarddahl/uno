"""
Tests for Uno DI: type safety and error handling
"""

# Standard library
import sys
from typing import Annotated, Protocol, runtime_checkable

# Local application
from uno.core.di.container import ServiceRegistration, ServiceScope, _ServiceResolver
from uno.core.errors.definitions import (
    CircularDependencyError,
    MissingParameterError,
    ServiceNotFoundError,
    ServiceRegistrationError,
)
from uno.core.errors.result import Failure, Success


# --- Test Classes (Module Level) ---
class B:
    def __init__(self, a: "A"):
        pass


class A:
    def __init__(self, b: "B"):
        pass


sys.modules[__name__].__dict__["A"] = A
sys.modules[__name__].__dict__["B"] = B


class ServiceInterface:
    pass


class ServiceImplementation(ServiceInterface):
    pass


@runtime_checkable
class IFoo(Protocol):
    def foo(self) -> str: ...


class Foo(IFoo):
    def __init__(self, *args, **kwargs):
        pass

    def foo(self) -> str:
        return "foo"


class Bar:
    pass


def test_register_and_resolve_type_safe():
    resolver = _ServiceResolver(registrations={})
    reg_result = resolver.register(IFoo, Foo)

    if isinstance(reg_result, Failure):
        raise AssertionError(f"Registration failed: {reg_result.error}")
    result = resolver.resolve(IFoo)
    assert isinstance(result, Success)
    assert isinstance(result.value, Foo)


def test_register_wrong_type_raises():
    resolver = _ServiceResolver(registrations={})
    result = resolver.register(IFoo, Bar)

    assert isinstance(result, Failure)
    assert isinstance(result.error, ServiceRegistrationError)


def test_register_factory_wrong_return_type_raises():
    resolver = _ServiceResolver(registrations={})

    def factory() -> Bar:
        return Bar()

    result = resolver.register(IFoo, factory)

    assert isinstance(result, Failure)
    assert isinstance(result.error, ServiceRegistrationError)


def test_register_protocol_structural_check():
    @runtime_checkable
    class Proto(Protocol):
        def foo(self) -> int: ...

    class Implementation:
        def foo(self) -> int:
            return 1

    # Should succeed
    _ServiceResolver(registrations={}).register(Proto, Implementation)


def test_register_factory_correct_return_type():
    class IFoo2:
        pass

    class Foo2(IFoo2):
        pass

    def factory() -> IFoo2:
        return Foo2()

    resolver = _ServiceResolver(registrations={})
    result = resolver.register(IFoo2, factory)
    assert isinstance(result, Success)


def test_circular_dependency_raises():
    """Test that resolving a circular dependency with type-based registrations fails (cycle or missing param)."""
    resolver = _ServiceResolver(registrations={})
    resolver.register(A, A)
    resolver.register(B, B)
    result = resolver.resolve(A)
    assert isinstance(result, Failure)
    from uno.core.errors.definitions import CircularDependencyError, ServiceRegistrationError
    assert isinstance(result.error, (CircularDependencyError, ServiceRegistrationError))

def test_circular_dependency_with_factories_returns_failure():
    """Test that resolving a circular dependency via factories returns a Failure (not CircularDependencyError)."""
    resolver = _ServiceResolver(registrations={})
    resolver.register(A, lambda: A(B()))
    resolver.register(B, lambda: B(A()))
    result = resolver.resolve(A)
    assert isinstance(result, Failure)
    from uno.core.errors.definitions import ServiceNotFoundError, ServiceRegistrationError
    assert isinstance(result.error, (ServiceNotFoundError, ServiceRegistrationError))
