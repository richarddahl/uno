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



