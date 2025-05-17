# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
MkDocs site generator for the Uno framework documentation.

This module creates a complete MkDocs site structure with navigation,
search, and themed documentation.
"""

from __future__ import annotations

import os
import yaml
import shutil
from pathlib import Path
from typing import Any, cast

from uno.docs.schema import DocumentableItem, DocumentationType
from uno.docs.providers.markdown import MarkdownProvider


class MkDocsProvider:
    """Provider that generates a complete MkDocs documentation site."""

    def __init__(self) -> None:
        """Initialize the MkDocs provider."""
        self.markdown_provider = MarkdownProvider()

    async def generate(
        self,
        items: list[DocumentableItem],
        output_path: str | None = None,
        **options: Any,
    ) -> str:
        """
        Generate a MkDocs site for the given documentable items.

        Args:
            items: List of items to document
            output_path: Path to output directory (required)
            **options: Additional options:
                - site_name: Name of the documentation site
                - theme: MkDocs theme to use (default: "material")
                - repo_url: GitHub repository URL
                - repo_name: GitHub repository name
                - plugins: List of MkDocs plugins to enable
                - build: Whether to build the site (requires mkdocs)
                - logo: Path to logo file
                - favicon: Path to favicon file

        Returns:
            Path to the generated site configuration
        """
        if not output_path:
            raise ValueError("output_path is required for MkDocs generation")

        # Set up output directory structure
        docs_dir = Path(output_path) / "docs"
        os.makedirs(docs_dir, exist_ok=True)

        # Group items by type
        items_by_type: dict[DocumentationType, list[DocumentableItem]] = {}
        for item in items:
            item_type = item.schema_info.type  # Change here
            if item_type not in items_by_type:
                items_by_type[item_type] = []
            items_by_type[item_type].append(item)

        # Create navigation structure and generate files
        nav = []
        for doc_type, type_items in items_by_type.items():
            # Create section in navigation
            type_name = doc_type.value.title()
            type_dir = docs_dir / doc_type.value
            os.makedirs(type_dir, exist_ok=True)

            section = {type_name: []}
            section_items = cast(list, section[type_name])

            # Create index file for this type
            with open(type_dir / "index.md", "w", encoding="utf-8") as f:
                f.write(f"# {type_name}\n\n")
                f.write(f"Documentation for {type_name.lower()} components.\n\n")
                f.write("## Components\n\n")
                for item in sorted(
                    type_items, key=lambda x: x.schema_info.name
                ):  # Change here
                    f.write(
                        f"- [{item.schema_info.name}]({item.schema_info.name.lower()}.md)\n"
                    )

            section_items.append({"Overview": f"{doc_type.value}/index.md"})

            # Generate individual documentation files
            for item in sorted(
                type_items, key=lambda x: x.schema_info.name
            ):  # Change here
                item_doc = await self.markdown_provider.generate_for_item(item)
                file_path = (
                    type_dir / f"{item.schema_info.name.lower()}.md"
                )  # Change here
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(item_doc)

                # Add to navigation
                relative_path = f"{doc_type.value}/{item.schema_info.name.lower()}.md"  # Change here
                section_items.append({item.schema_info.name: relative_path})

            nav.append(section)

        # Create main index file
        site_name = options.get("site_name", "Uno Documentation")
        with open(docs_dir / "index.md", "w", encoding="utf-8") as f:
            f.write(f"# {site_name}\n\n")
            f.write("Welcome to the Uno framework documentation.\n\n")

            # Add framework description if provided
            if "description" in options:
                f.write(f"{options['description']}\n\n")

            f.write("## Documentation Sections\n\n")
            for doc_type in items_by_type:
                type_name = doc_type.value.title()
                type_count = len(items_by_type[doc_type])
                f.write(
                    f"- [{type_name}]({doc_type.value}/index.md) ({type_count} components)\n"
                )

        # Set up MkDocs configuration
        config = {
            "site_name": site_name,
            "theme": options.get("theme", "material"),
            "docs_dir": "docs",
            "nav": [{"Home": "index.md"}] + nav,
            "markdown_extensions": [
                "pymdownx.highlight",
                "pymdownx.superfences",
                "pymdownx.tabbed",
                "pymdownx.details",
                "admonition",
                "toc",
            ],
        }

        # Add theme customization
        if options.get("theme", "material") == "material":
            config["theme"] = {
                "name": "material",
                "palette": {
                    "primary": options.get("primary_color", "indigo"),
                    "accent": options.get("accent_color", "indigo"),
                },
                "features": [
                    "navigation.instant",
                    "navigation.tracking",
                    "navigation.expand",
                    "navigation.indexes",
                    "search.highlight",
                    "search.share",
                ],
            }

            # Add logo if provided
            if "logo" in options:
                logo_path = options["logo"]
                if os.path.exists(logo_path):
                    target_path = Path(output_path) / "docs" / "assets" / "logo.png"
                    os.makedirs(target_path.parent, exist_ok=True)
                    shutil.copy(logo_path, target_path)
                    config["theme"]["logo"] = "assets/logo.png"

            # Add favicon if provided
            if "favicon" in options:
                favicon_path = options["favicon"]
                if os.path.exists(favicon_path):
                    target_path = Path(output_path) / "docs" / "assets" / "favicon.ico"
                    os.makedirs(target_path.parent, exist_ok=True)
                    shutil.copy(favicon_path, target_path)
                    config["theme"]["favicon"] = "assets/favicon.ico"

        # Add repository information
        if "repo_url" in options:
            config["repo_url"] = options["repo_url"]
        if "repo_name" in options:
            config["repo_name"] = options["repo_name"]

        # Add plugins if specified
        plugins = options.get("plugins")
        if plugins:
            config["plugins"] = plugins

        # Write configuration
        config_path = Path(output_path) / "mkdocs.yml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False)

        # Build the site if requested
        if options.get("build", False):
            try:
                import subprocess

                subprocess.run(["mkdocs", "build", "-f", str(config_path)], check=True)
            except Exception as e:
                print(f"Warning: Could not build MkDocs site: {e}")

        return str(config_path)

    async def generate_for_item(self, item: DocumentableItem, **options: Any) -> str:
        """
        Generate MkDocs documentation for a single item.

        This delegates to the Markdown provider since MkDocs uses Markdown.

        Args:
            item: The item to document
            **options: Additional options

        Returns:
            Generated Markdown documentation for the item
        """
        return await self.markdown_provider.generate_for_item(item, **options)
