"""
Uno API serialization utilities.

This module provides helpers for enforcing the Uno canonical serialization contract
at all API boundaries. All API responses must use the Uno contract:
    model_dump(exclude_none=True, exclude_unset=True, by_alias=True)

Usage:
    from .api_utils import as_canonical_json
    ...
    @app.get("/example", response_model=MyDTO)
    def example():
        return as_canonical_json(MyDTO(...))

All API endpoints must use this utility (or equivalent logic) to ensure compliance.
"""
from pydantic import BaseModel
from typing import Any


def as_canonical_json(obj: Any) -> Any:
    """
    Recursively serialize a Pydantic BaseModel or a list/dict of models using the Uno canonical contract.
    This ensures all API responses are compliant with Uno's serialization requirements.
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
    elif isinstance(obj, list):
        return [as_canonical_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: as_canonical_json(v) for k, v in obj.items()}
    return obj
