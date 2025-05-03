"""
DomainServiceProtocol: Abstract base class for domain service discovery and DI.
Extend this protocol for domain services that should be auto-discoverable and injectable.
"""

from typing import Protocol, runtime_checkable

@runtime_checkable
class DomainServiceProtocol(Protocol):
    """Protocol for domain service implementations to support DI and discovery."""
    # Example: required method signature for all domain services
    def service_name(self) -> str:
        ...
