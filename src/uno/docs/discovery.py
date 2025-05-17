# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Discovery utilities for the Uno documentation system.

This module provides functions to discover documentable items in modules.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Any, Callable, TypeVar

from uno.docs.schema import DocumentableItem

T = TypeVar("T")


async def discover_documentable_items(
    module_name: str,
    predicate: Callable[[Any], bool] | None = None,
) -> list[DocumentableItem]:
    """
    Discover documentable items in the specified module.

    Args:
        module_name: Fully qualified module name
        predicate: Optional function to filter discovered items

    Returns:
        List of discovered documentable items
    """
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return []

    # Get all extractors
    from uno.docs.extractors import get_extractors

    extractors = await get_extractors()

    # Find all documentable items in the module
    items = []
    for name, obj in inspect.getmembers(module):
        # Skip if predicate provided and object doesn't match
        if predicate and not predicate(obj):
            continue

        # Try each extractor
        for extractor in extractors:
            if await extractor.can_extract(obj):
                schema = await extractor.extract_schema(obj)
                items.append(DocumentableItem(schema_info=schema, original=obj))
                break

    # Also check submodules if it's a package
    if hasattr(module, "__path__"):
        for _, submodule_name, is_pkg in pkgutil.iter_modules(
            module.__path__, module.__name__ + "."
        ):
            subitems = await discover_documentable_items(submodule_name, predicate)
            items.extend(subitems)

    return items
