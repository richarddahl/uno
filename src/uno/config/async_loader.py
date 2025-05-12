"""
AsyncConfigLoader: Async configuration loader for Uno framework integration.
Supports loading config from remote/async sources (e.g. HTTP, secrets manager).
"""
from uno.config.base import UnoSettings, Environment
from typing import TypeVar

T = TypeVar("T", bound=UnoSettings)

class AsyncConfigLoader:
    """
    Loads configuration asynchronously from remote or async sources.
    """
    async def load(self, settings_class: type[T], env: Environment | None = None) -> T:
        """
        Asynchronously load settings for the given class and environment.
        Override this method to implement custom remote/async loading logic.
        """
        # Default: fallback to sync loading for now
        return settings_class.from_env(env or Environment.get_current())
