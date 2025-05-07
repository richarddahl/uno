from typing import Protocol, runtime_checkable


@runtime_checkable
class HashServiceProtocol(Protocol):
    def compute_hash(self, payload: str) -> str: ...
