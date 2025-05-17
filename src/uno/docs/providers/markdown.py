# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Markdown documentation provider for the Uno framework.

This module generates Markdown documentation for Uno components.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from uno.docs.schema import DocumentableItem, DocumentationType


class MarkdownProvider:
    """Provider that generates Markdown documentation."""

    async def generate(
        self,
        items: list[DocumentableItem],
        output_path: str | None = None,
        **options: Any,
    ) -> str:
        """
        Generate Markdown documentation for the given items.

        Args:
            items: List of items to document
            output_path: Optional path to write documentation to
            **options: Additional options:
                - title: Document title (default: "Documentation")
                - group_by_type: Group items by type (default: True)

        Returns:
            Generated Markdown documentation
        """
        # Extract options
        title = options.get("title", "Documentation")
        group_by_type = options.get("group_by_type", True)

        # Prepare header
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        doc = [
            f"# {title}",
            "",
            f"Generated on: {now}",
            "",
            "## Contents",
            "",
        ]

        # Group items by type if needed
        if group_by_type:
            items_by_type: dict[DocumentationType, list[DocumentableItem]] = {}
            for item in items:
                item_type = item.schema.type
                if item_type not in items_by_type:
                    items_by_type[item_type] = []
                items_by_type[item_type].append(item)

            # Generate table of contents by type
            for doc_type, type_items in items_by_type.items():
                doc.append(f"### {doc_type.value.title()}")
                doc.append("")
                for item in type_items:
                    doc.append(f"- [{item.schema.name}](#{item.schema.name.lower()})")
                doc.append("")
        else:
            # Generate flat table of contents
            for item in items:
                doc.append(f"- [{item.schema.name}](#{item.schema.name.lower()})")
            doc.append("")

        doc.append("---")
        doc.append("")

        # Generate documentation for each item
        item_docs = []
        for item in items:
            item_doc = await self.generate_for_item(item)
            item_docs.append(item_doc)

        doc.extend(item_docs)

        # Generate the final markdown document
        markdown = "\n".join(doc)

        # Write to output path if specified
        if output_path:
            output_path = Path(output_path)
            os.makedirs(output_path.parent, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown)

        return markdown

    async def generate_for_item(self, item: DocumentableItem, **options: Any) -> str:
        """
        Generate Markdown documentation for a single item.

        Args:
            item: The item to document
            **options: Additional options

        Returns:
            Generated Markdown documentation
        """
        schema = item.schema
        doc = [
            f"## {schema.name}",
            "",
        ]

        # Add description
        if schema.description:
            doc.append(schema.description)
            doc.append("")

        # Add module info
        doc.append(f"**Module:** `{schema.module}`")
        doc.append("")

        # Add type info
        doc.append(f"**Type:** {schema.type.value.title()}")
        doc.append("")

        # Add base classes if any
        if schema.base_classes:
            doc.append(
                "**Inherits from:** "
                + ", ".join(f"`{base}`" for base in schema.base_classes)
            )
            doc.append("")

        # Add fields table
        if schema.fields:
            doc.append("### Fields")
            doc.append("")

            # Determine columns based on field properties
            has_secure = any(field.is_secure for field in schema.fields)

            # Create header row
            header = ["Field", "Type", "Default", "Required", "Description"]
            if has_secure:
                header.append("Security")

            doc.append("| " + " | ".join(header) + " |")

            # Create separator row
            doc.append("| " + " | ".join("---" for _ in header) + " |")

            # Add field rows
            for field in schema.fields:
                # Format field info
                field_type = field.type_name
                required = "✓" if field.is_required else ""

                default = field.default_value or ""
                if not default and field.is_required:
                    default = "**Required**"

                security = ""
                if has_secure and field.is_secure:
                    security = f"{field.secure_handling or 'secure'}"

                # Build row
                row = [field.name, field_type, default, required, field.description]
                if has_secure:
                    row.append(security)

                doc.append("| " + " | ".join(row) + " |")

            doc.append("")

        # Add examples section if any
        if schema.examples:
            doc.append("### Examples")
            doc.append("")

            for i, example in enumerate(schema.examples, 1):
                doc.append(f"#### {example.title or f'Example {i}'}")
                if example.description:
                    doc.append("")
                    doc.append(example.description)
                doc.append("")
                doc.append(f"```{example.language}")
                doc.append(example.code)
                doc.append("```")
                doc.append("")

        return "\n".join(doc)
