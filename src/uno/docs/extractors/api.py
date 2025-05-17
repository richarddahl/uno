# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
API endpoint extractor for documentation.

This module extracts documentation information from API endpoint classes.
"""

from __future__ import annotations

import inspect
import re
from typing import Any, get_type_hints, cast

from uno.docs.schema import DocumentationType, ExampleInfo, FieldInfo, SchemaInfo


class ApiExtractor:
    """Extractor for API endpoint classes."""

    async def can_extract(self, item: Any) -> bool:
        """Determine if this extractor can handle an API endpoint class."""
        # Check if it's a class
        if not inspect.isclass(item):
            return False

        # Look for API endpoint indicators
        try:
            # Check if it has route attributes or other API markers
            return (
                hasattr(item, "route")
                or hasattr(item, "__endpoints__")
                or hasattr(item, "path")
                or getattr(item, "__api__", False)
            )
        except (ImportError, TypeError):
            return False

    async def extract_schema(self, item: Any) -> SchemaInfo:
        """Extract documentation schema from an API endpoint class."""
        # Extract basic information
        schema = SchemaInfo(
            name=item.__name__,
            module=item.__module__,
            description=self._extract_docstring(item),
            type=DocumentationType.API,
        )

        # Extract API-specific information like routes, methods, etc.
        # ... implementation for API endpoint extraction ...

        return schema

    def _extract_docstring(self, obj: Any) -> str:
        """Extract a clean description from an object's docstring."""
        # ... similar to the ConfigExtractor implementation ...
