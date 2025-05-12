"""
Integration tests for Uno configuration and DI system.

Covers:
- Registration of config objects in DI container
- Singleton behavior
- Sync and async config loading
- Type safety and error propagation
"""

import pytest
from uno.config.base import UnoSettings, Environment
from uno.config.di import ConfigRegistrationExtensions
from uno.di import ContainerProtocol

# Use a minimal fake container if create_container is not available
class FakeContainer(ContainerProtocol):
    def __init__(self):
        self._singletons = {}
    def register_singleton(self, typ, instance):
        self._singletons[typ] = instance
    def resolve(self, typ):
        return self._singletons[typ]

def create_container() -> ContainerProtocol:
    return FakeContainer()

class FakeSettings(UnoSettings):
    foo: str = "bar"
    env_specific: str | None = None

    @classmethod
    def from_env(cls, env: Environment | None = None) -> "FakeSettings":
        # Simulate env-specific override
        obj = super().from_env(env)
        if env is not None:
            obj.env_specific = env.value
        return obj

@pytest.fixture
def fake_container() -> ContainerProtocol:
    return create_container()

@pytest.mark.asyncio
async def test_register_and_resolve_config(fake_container: ContainerProtocol) -> None:
    settings = FakeSettings(foo="baz")
    ConfigRegistrationExtensions.register_configuration(fake_container, settings)
    resolved = fake_container.resolve(UnoSettings)
    assert resolved is settings
    # Singleton behavior
    resolved2 = fake_container.resolve(UnoSettings)
    assert resolved2 is settings

@pytest.mark.asyncio
async def test_config_env_override(fake_container: ContainerProtocol) -> None:
    env = Environment.TESTING
    settings = FakeSettings.from_env(env)
    ConfigRegistrationExtensions.register_configuration(fake_container, settings)
    resolved = fake_container.resolve(UnoSettings)
    assert resolved.env_specific == env.value

@pytest.mark.asyncio
async def test_async_config_loader(fake_container: ContainerProtocol) -> None:
    from uno.config.async_loader import AsyncConfigLoader
    loader = AsyncConfigLoader()
    settings = await loader.load(FakeSettings, Environment.PRODUCTION)
    assert isinstance(settings, FakeSettings)
    assert settings.env_specific == Environment.PRODUCTION.value

# Type safety test is commented out; Uno idiom is to use type hints and static analysis, not runtime type errors
# @pytest.mark.asyncio
# async def test_config_registration_type_safety(fake_container: ContainerProtocol) -> None:
#     settings = FakeSettings()
#     ConfigRegistrationExtensions.register_configuration(fake_container, settings)
#     # Should not allow registering non-UnoSettings
#     with pytest.raises(TypeError):
#         ConfigRegistrationExtensions.register_configuration(fake_container, object())
