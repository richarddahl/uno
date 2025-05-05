"""
DefaultHashService implements HashServiceProtocol using hashlib and a configurable algorithm (default: sha256).
"""

import hashlib
from uno.core.services.hash_service_protocol import HashServiceProtocol


class DefaultHashService(HashServiceProtocol):
    def __init__(self, algorithm: str = "sha256"):
        if not hasattr(hashlib, algorithm):
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        self._algorithm = algorithm
        self._hash_func = getattr(hashlib, algorithm)

    def compute_hash(self, payload: str) -> str:
        return str(self._hash_func(payload.encode("utf-8")).hexdigest())
