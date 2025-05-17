# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
HTML documentation provider for the Uno framework.

This module generates HTML documentation for Uno components.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from uno.docs.schema import DocumentableItem, DocumentationType


class HTMLProvider:
    """Provider that generates HTML documentation."""

    async def generate(
        self,
        items: list[DocumentableItem],
        output_path: str | None = None,
        **options: Any,
    ) -> str:
        """
        Generate HTML documentation for the given items.

        Args:
            items: List of items to document
            output_path: Optional path to write documentation to
            **options: Additional options:
                - title: Document title (default: "Documentation")
                - group_by_type: Group items by type (default: True)

        Returns:
            Generated HTML documentation
        """
        # Extract options
        title = options.get("title", "Documentation")
        group_by_type = options.get("group_by_type", True)

        # Prepare the HTML document
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"  <title>{title}</title>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            "  <style>",
            "    body { font-family: system-ui, sans-serif; line-height: 1.5; margin: 0; padding: 20px; }",
            "    h1, h2, h3 { margin-top: 1em; }",
            "    .content { max-width: 800px; margin: 0 auto; }",
            "    table { border-collapse: collapse; width: 100%; }",
            "    th, td { border: 1px solid #ddd; padding: 8px; }",
            "    th { background-color: #f2f2f2; }",
            "    code { background-color: #f5f5f5; padding: 2px 4px; border-radius: 4px; }",
            "    pre { background-color: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; }",
            "  </style>",
            "</head>",
            "<body>",
            '  <div class="content">',
            f"    <h1>{title}</h1>",
            f"    <p>Generated on: {now}</p>",
            '    <div class="toc">',
            "      <h2>Contents</h2>",
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
                html.append(f"      <h3>{doc_type.value.title()}</h3>")
                html.append("      <ul>")
                for item in type_items:
                    html.append(
                        f'        <li><a href="#{item.schema.name.lower()}">{item.schema.name}</a></li>'
                    )
                html.append("      </ul>")
        else:
            # Generate flat table of contents
            html.append("      <ul>")
            for item in items:
                html.append(
                    f'        <li><a href="#{item.schema.name.lower()}">{item.schema.name}</a></li>'
                )
            html.append("      </ul>")

        html.append("    </div>")
        html.append("    <hr>")

        # Generate documentation for each item
        for item in items:
            item_html = await self.generate_for_item(item)
            html.append(item_html)

        # Close the HTML document
        html.extend(
            [
                "  </div>",
                "</body>",
                "</html>",
            ]
        )

        # Generate the final HTML document
        html_content = "\n".join(html)

        # Write to output path if specified
        if output_path:
            output_path = Path(output_path)
            os.makedirs(output_path.parent, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

        return html_content

    async def generate_for_item(self, item: DocumentableItem, **options: Any) -> str:
        """
        Generate HTML documentation for a single item.

        Args:
            item: The item to document
            **options: Additional options

        Returns:
            Generated HTML documentation for the item
        """
        schema = item.schema
        html = [
            f'    <div id="{schema.name.lower()}" class="item">',
            f"      <h2>{schema.name}</h2>",
        ]

        # Add description
        if schema.description:
            html.append(f"      <p>{schema.description}</p>")

        # Add module info
        html.append(
            f"      <p><strong>Module:</strong> <code>{schema.module}</code></p>"
        )

        # Add type info
        html.append(f"      <p><strong>Type:</strong> {schema.type.value.title()}</p>")

        # Add base classes if any
        if schema.base_classes:
            html.append(
                "      <p><strong>Inherits from:</strong> "
                + ", ".join(f"<code>{base}</code>" for base in schema.base_classes)
                + "</p>"
            )

        # Add fields table
        if schema.fields:
            html.append("      <h3>Fields</h3>")
            html.append("      <table>")

            # Determine columns based on field properties
            has_secure = any(field.is_secure for field in schema.fields)

            # Create header row
            header = ["Field", "Type", "Default", "Required", "Description"]
            if has_secure:
                header.append("Security")

            html.append("        <tr>")
            for col in header:
                html.append(f"          <th>{col}</th>")
            html.append("        </tr>")

            # Add field rows
            for field in schema.fields:
                # Format field info
                field_type = field.type_name
                required = "✓" if field.is_required else ""

                default = field.default_value or ""
                if not default and field.is_required:
                    default = "<strong>Required</strong>"

                security = ""
                if has_secure and field.is_secure:
                    security = f"{field.secure_handling or 'secure'}"

                # Build row
                html.append("        <tr>")
                html.append(f"          <td>{field.name}</td>")
                html.append(f"          <td>{field_type}</td>")
                html.append(f"          <td>{default}</td>")
                html.append(f"          <td>{required}</td>")
                html.append(f"          <td>{field.description}</td>")
                if has_secure:
                    html.append(f"          <td>{security}</td>")
                html.append("        </tr>")

            html.append("      </table>")

        # Add examples section if any
        if schema.examples:
            html.append("      <h3>Examples</h3>")

            for i, example in enumerate(schema.examples, 1):
                html.append(f"      <h4>{example.title or f'Example {i}'}</h4>")
                if example.description:
                    html.append(f"      <p>{example.description}</p>")
                html.append("      <pre>")
                html.append(
                    f'<code class="language-{example.language}">{example.code}</code>'
                )
                html.append("      </pre>")

        html.append("    </div>")

        return "\n".join(html)
