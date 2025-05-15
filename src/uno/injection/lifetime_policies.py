from uno.injection.config import ServiceLifetime
from typing import Any, Callable


class SingletonPolicy:
    def __init__(self):
        self._instances = {}

    async def get_instance(self, scope, factory, key):
        if key not in self._instances:
            self._instances[key] = await factory()
        return self._instances[key]

    async def store_instance(self, scope, instance, key):
        self._instances[key] = instance

    async def should_dispose(self):
        return False


class ScopedPolicy:
    async def get_instance(self, scope, factory, key):
        if key not in scope._services:
            scope._services[key] = await factory()
        return scope._services[key]

    async def store_instance(self, scope, instance, key):
        scope._services[key] = instance

    async def should_dispose(self):
        return True


class TransientPolicy:
    async def get_instance(self, scope, factory, key):
        return await factory()

    async def store_instance(self, scope, instance, key):
        pass

    async def should_dispose(self):
        return True


LIFETIME_POLICY_MAP = {
    ServiceLifetime.SINGLETON: SingletonPolicy(),
    ServiceLifetime.SCOPED: ScopedPolicy(),
    ServiceLifetime.TRANSIENT: TransientPolicy(),
}
