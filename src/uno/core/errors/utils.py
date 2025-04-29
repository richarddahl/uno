"""
Utility functions for Uno error handling and serialization.
"""
from enum import Enum
from typing import Any

def serialize_enums(obj: Any) -> Any:
    """
    Recursively convert any Enum instances in a structure (dict, list, tuple, set)
    to their string representation (using .name), for JSON serializability.
    """
    if isinstance(obj, Enum):
        return obj.name
    elif isinstance(obj, dict):
        return {serialize_enums(k): serialize_enums(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_enums(i) for i in obj]
    elif isinstance(obj, tuple):
        return tuple(serialize_enums(i) for i in obj)
    elif isinstance(obj, set):
        return {serialize_enums(i) for i in obj}
    return obj
