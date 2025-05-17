# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Core protocols for the Uno documentation system.

This module defines the interfaces used by the documentation system.
"""

from __future__ import annotations

from typing import Any, Protocol

from uno.docs.schema import SchemaInfo


class SchemaExtractorProtocol(Protocol):
    """
    Protocol for schema extractors that can document specific types of objects.
    
    This protocol is NOT runtime_checkable and should be used
    for static type checking only.
    """
    
    async def can_extract(self, item: Any) -> bool:
        """
        Determine if this extractor can handle a given item.
        
        Args:
            item: The item to check
            
        Returns:
            True if this extractor can handle the item
        """
        ...
        
    async def extract_schema(self, item: Any) -> SchemaInfo:
        """
        Extract documentation schema from an item.
        
        Args:
            item: The item to extract schema from
            
        Returns:
            Documentation schema for the item
        """
        ...


class DocumentationProviderProtocol(Protocol):
    """
    Protocol for documentation providers that generate documentation in various formats.
    
    This protocol is NOT runtime_checkable and should be used
    for static type checking only.
    """
    
    async def generate(
        self, 
        items: list[Any],
        output_path: str | None = None,
        **options: Any,
    ) -> str:
        """
        Generate documentation for the given items.
        
        Args:
            items: List of items to document
            output_path: Optional path to write documentation to
            **options: Additional provider-specific options
            
        Returns:
            Generated documentation as a string
        """
        ...
    
    async def generate_for_item(
        self,
        item: Any,
        **options: Any,
    ) -> str:
        """
        Generate documentation for a single item.
        
        Args:
            item: The item to document
            **options: Additional provider-specific options
            
        Returns:
            Generated documentation for the item
        """
        ...
