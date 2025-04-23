"""
Tests for Uno DI: type safety and error handling
"""

# Standard library
from typing import Annotated, Protocol, runtime_checkable

from uno.core.di import Inject

# Local application
from uno.core.di.container import _ServiceResolver
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

import sys
sys.modules[__name__].__dict__["A"] = A
sys.modules[__name__].__dict__["B"] = B

# --- DEBUG: Print resolved type hints for A, B, NeedsNamed ---
from typing import get_type_hints
print("[TEST DEBUG] get_type_hints(A.__init__):", get_type_hints(A.__init__, globalns=globals(), localns=locals()))
print("[TEST DEBUG] get_type_hints(B.__init__):", get_type_hints(B.__init__, globalns=globals(), localns=locals()))
try:
    print("[TEST DEBUG] get_type_hints(NeedsNamed.__init__):", get_type_hints(NeedsNamed.__init__, globalns=globals(), localns=locals()))
except Exception as e:
    print(f"[TEST DEBUG] get_type_hints(NeedsNamed.__init__) failed: {e}")


class ServiceInterface:
    pass


class ServiceImplementation(ServiceInterface):
    pass


class NamedService(ServiceInterface):
    pass


class NeedsNamed:
    def __init__(self, service: Annotated[ServiceInterface, "my_name"]):
        self.service = service


class NeedsMissingNamed:
    def __init__(self, service: Annotated[ServiceInterface, "missing_name"]):
        self.service = service


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
    resolver = _ServiceResolver()
    reg_result = resolver.register(IFoo, Foo)

    if isinstance(reg_result, Failure):
        raise AssertionError(f"Registration failed: {reg_result.error}")
    result = resolver.resolve(IFoo)
    assert isinstance(result, Success)
    assert isinstance(result.value, Foo)


def test_register_wrong_type_raises():
    resolver = _ServiceResolver()
    result = resolver.register(IFoo, Bar)

    assert isinstance(result, Failure)
    assert isinstance(result.error, ServiceRegistrationError)


def test_register_factory_wrong_return_type_raises():
    resolver = _ServiceResolver()

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
    _ServiceResolver().register(Proto, Implementation)


def test_register_factory_correct_return_type():
    class IFoo2:
        pass

    class Foo2(IFoo2):
        pass

    def factory() -> IFoo2:
        return Foo2()

    resolver = _ServiceResolver()
    result = resolver.register(IFoo2, factory)
    assert isinstance(result, Success)


def test_circular_dependency_raises():
    """Test that resolving a circular dependency raises CircularDependencyError."""
    resolver = _ServiceResolver()

    resolver.register(A, A)
    resolver.register(B, B)
    # Simulate circular dependency resolution
    result = resolver.resolve(A)

    assert isinstance(result, Failure)
    assert isinstance(result.error, CircularDependencyError)


# --- Named Injection Tests ---


@runtime_checkable
class IService(Protocol):
    def get_id(self) -> str: ...


class DefaultService(IService):
    def __init__(self, *args, **kwargs):
        pass
    def get_id(self) -> str:
        return "default"


class NamedServiceA(IService):
    def __init__(self, *args, **kwargs):
        pass
    def get_id(self) -> str:
        return "service_a"


class NamedServiceB(IService):
    def __init__(self, *args, **kwargs):
        pass
    def get_id(self) -> str:
        return "service_b"


class Consumer:
    def __init__(
        self,
        default: IService,
        service_a: Annotated[IService, Inject(name="a")],
        service_b: Annotated[IService, Inject(name="b")],
    ):
        self.default_id = default.get_id()
        self.a_id = service_a.get_id()
        self.b_id = service_b.get_id()


def test_register_and_resolve_named():
    resolver = _ServiceResolver()
    resolver.register(IService, DefaultService)
    resolver.register(IService, NamedServiceA, name="a")
    resolver.register(IService, NamedServiceB, name="b")

    # Resolve default
    res_def = resolver.resolve(IService)
    assert isinstance(res_def, Success)
    assert isinstance(res_def.value, DefaultService)
    assert res_def.value.get_id() == "default"

    # Resolve named 'a'
    res_a = resolver.resolve(IService, name="a")
    assert isinstance(res_a, Success)
    assert isinstance(res_a.value, NamedServiceA)
    assert res_a.value.get_id() == "service_a"

    # Resolve named 'b'
    res_b = resolver.resolve(IService, name="b")
    assert isinstance(res_b, Success)
    assert isinstance(res_b.value, NamedServiceB)
    assert res_b.value.get_id() == "service_b"

    # Resolve non-existent name
    res_c = resolver.resolve(IService, name="c")
    assert isinstance(res_c, Failure)
    assert isinstance(res_c.error, ServiceNotFoundError)


def test_inject_named_via_annotated():
    """Test injecting a named service using Annotated."""
    resolver = _ServiceResolver()
    resolver.register(ServiceInterface, ServiceImplementation)
    resolver.register(
        (ServiceInterface, "my_name"), NamedService
    )  # Register named service
    resolver.register(NeedsNamed, NeedsNamed)  # Register dependent class

    result = resolver.resolve(NeedsNamed)
    assert isinstance(result, Success)
    assert isinstance(result.value.service, NamedService)


def test_inject_missing_named_via_annotated_fails():
    """Test injecting a non-existent named service using Annotated fails."""
    resolver = _ServiceResolver()
    resolver.register(ServiceInterface, ServiceImplementation)
    # Named service "missing_name" is NOT registered
    resolver.register(NeedsMissingNamed, NeedsMissingNamed)  # Register dependent class

    result = resolver.resolve(NeedsMissingNamed)
    assert isinstance(result, Failure)
    assert isinstance(result.error, ServiceNotFoundError | MissingParameterError)
