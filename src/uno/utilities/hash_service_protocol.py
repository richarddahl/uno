from typing import Protocol


class HashServiceProtocol(Protocol):
    def compute_hash(self, payload: str) -> str: ...
