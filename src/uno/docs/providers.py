# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Documentation generation for the Uno framework.

This module provides utilities for generating documentation from various
components of the Uno framework, making them more discoverable and understandable.
"""

from uno.docs.protocols import DocumentationProviderProtocol, SchemaExtractorProtocol
from uno.docs.providers import (
    MarkdownProvider,
    HTMLProvider,
    MkDocsProvider,
    JsonProvider,
)
from uno.docs.schema import DocumentableItem, SchemaInfo, FieldInfo, ExampleInfo
from uno.docs.discovery import discover_documentable_items

# Import the cli module, not the specific functions (to avoid circular imports)
from uno.docs import cli

# Use the generate_documentation function from cli module
generate_documentation = cli.generate_documentation

__all__ = [
    # Core protocols
    "DocumentationProviderProtocol",
    "SchemaExtractorProtocol",
    # Schema information classes
    "DocumentableItem",
    "SchemaInfo",
    "FieldInfo",
    "ExampleInfo",
    # Providers
    "MarkdownProvider",
    "HTMLProvider",
    "MkDocsProvider",
    "JsonProvider",
    # Discovery utilities
    "discover_documentable_items",
    # CLI utilities
    "generate_documentation",
]


class MkDocsProvider:
    """Provider for MkDocs documentation."""

    async def generate(
        self,
        items: list[DocumentableItem],
        output_path: str | None = None,
        site_name: str = "Documentation",
        theme: str = "material",
        build: bool = False,
        enable_search: bool = True,
        syntax_highlighting: bool = True,
        highlight_theme: str = "github-dark",
        enable_relationship_graphs: bool = True,
        enable_enhanced_search: bool = True,
        **options: Any,
    ) -> str:
        """
        Generate MkDocs documentation.

        Args:
            items: List of documentable items
            output_path: Path to write documentation to
            site_name: Name of the site
            theme: MkDocs theme to use
            build: Whether to build the site
            enable_search: Whether to enable search
            syntax_highlighting: Whether to enable syntax highlighting
            highlight_theme: Theme to use for syntax highlighting
            enable_relationship_graphs: Whether to include relationship graph links
            enable_enhanced_search: Whether to include enhanced search links
            **options: Additional options

        Returns:
            Generated documentation
        """
        # ...existing code...

        # Add navigation
        nav = [{"Home": "index.md"}]

        # Add enhanced search link if enabled
        if enable_enhanced_search:
            nav.append({"Search": "/search"})

        # Add relationship graph link if enabled
        if enable_relationship_graphs:
            nav.append({"Component Relationships": "/relationships"})

        for category in sorted(items_by_type.keys()):
            category_nav = {category.capitalize(): []}
            category_items = items_by_type[category]
            for item in sorted(category_items, key=lambda x: x.schema_info.name):
                category_nav[category.capitalize()].append(
                    {item.schema_info.name: f"{category}/{item.schema_info.name}.md"}
                )
            nav.append(category_nav)
        config["nav"] = nav

        # ...existing code...


class MarkdownProvider:
    """Provider for Markdown documentation."""

    # ...existing code...

    async def generate_for_item(
        self,
        item: DocumentableItem,
        enable_api_playground: bool = True,
        **options: Any,
    ) -> str:
        """
        Generate Markdown documentation for a single item.

        Args:
            item: Item to document
            enable_api_playground: Whether to include API playground links
            **options: Additional options

        Returns:
            Generated Markdown documentation
        """
        schema = item.schema_info
        doc = f"# {schema.name}\n\n"

        # Add description
        if schema.description:
            doc += f"{schema.description}\n\n"

        # For API endpoints, add a link to the playground
        if schema.type == DocumentationType.API and enable_api_playground:
            doc += f"[Try this endpoint in the API Playground](/api-playground/{schema.name})\n\n"

        # ...existing code...
