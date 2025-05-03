from enum import Enum, auto


class ServiceScope(Enum):
    """
    Service lifetime scopes for dependency injection.

    Defines the lifetime of a service instance, including singleton (application),
    scoped, and transient.
    """
    SINGLETON = auto()  # One instance per container
    SCOPED = auto()     # One instance per scope (e.g., request)
    TRANSIENT = auto()  # New instance each time
