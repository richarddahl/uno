from uno.infrastructure.di.provider import ServiceLifecycle


class ForgottenService(ServiceLifecycle):
    async def initialize(self):
        pass

    async def dispose(self):
        pass
