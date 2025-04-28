from collections.abc import Callable
from typing import Any, Generic, TypeVar
from uno.core.di.service_scope import ServiceScope

T = TypeVar("T")

class ServiceRegistration(Generic[T]):
    """
    ADVANCED/INTERNAL: Service registration information.

    This class is not intended for typical end-user code, but is exposed for advanced/extensibility scenarios.
    Most users should use ServiceCollection for registrations.

    Holds the configuration for how a service should be resolved, including
    its implementation type or factory, scope, and initialization parameters.
    """

    def __init__(
        self,
        implementation: type[T] | Any,
        scope: ServiceScope = ServiceScope.SINGLETON,
        params: dict[str, Any] | None = None,
        condition: Callable[[], bool] | None = None,
    ):
        self.implementation = implementation
        self.scope = scope
        self.params = params or {}
        self.condition = condition

    def __repr__(self) -> str:
        return (
            f"ServiceRegistration(implementation={self.implementation}, "
            f"scope={self.scope}, params={self.params}, "
            f"condition={self.condition})"
        )
