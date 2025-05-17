# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
CLI utilities for documentation generation.

This module provides command-line tools for generating documentation.
"""

import asyncio
import argparse
import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

# Import just what we need, not from uno.docs
from uno.docs.discovery import discover_documentable_items
from uno.docs.providers import (
    MarkdownProvider,
    HTMLProvider,
    MkDocsProvider,
    JsonProvider,
)
from uno.docs.testing import validate_documentation
from uno.docs.example_sync import sync_examples_for_module


async def generate_documentation(
    module_name: str,
    output_path: str | None = None,
    format: str = "markdown",
    title: str | None = None,
    **options: Any,
) -> str:
    """
    Generate documentation for a module.

    Args:
        module_name: Name of the module to document
        output_path: Path to write documentation to
        format: Documentation format (markdown, html, json, mkdocs)
        title: Documentation title
        **options: Additional options for the documentation provider

    Returns:
        Generated documentation
    """
    # Discover documentable items in the module
    items = await discover_documentable_items(module_name)

    if not items:
        print(f"No documentable items found in module: {module_name}")
        return ""

    # Create appropriate provider based on format
    provider = None
    if format in ("markdown", "md"):
        provider = MarkdownProvider()
    elif format in ("html", "htm"):
        provider = HTMLProvider()
    elif format == "json":
        provider = JsonProvider()
    elif format == "mkdocs":
        provider = MkDocsProvider()
    else:
        raise ValueError(f"Unsupported format: {format}")

    # Generate documentation
    doc_title = title or f"{module_name} Documentation"
    doc = await provider.generate(
        items,
        output_path=output_path,
        title=doc_title,
        **options,
    )

    return doc


async def sync_examples(
    module_name: str,
    source_dirs: list[str | Path] | None = None,
    output_path: str | None = None,
    overwrite_existing: bool = False,
) -> dict[str, Any]:
    """
    Synchronize examples from source code to documentation.

    Args:
        module_name: Name of the module to document
        source_dirs: List of directories to scan for examples
        output_path: Path to write synchronization report to
        overwrite_existing: Whether to overwrite existing examples

    Returns:
        Synchronization result summary
    """
    # Import here to avoid circular import
    from uno.docs.example_sync import sync_examples_for_module

    # Synchronize examples
    result = await sync_examples_for_module(
        module_name,
        source_dirs=source_dirs,
        overwrite_existing=overwrite_existing,
    )

    # Write report to file if requested
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)

    return result


async def main_async(args: Sequence[str] | None = None) -> int:
    """Command-line entry point implementation."""
    parser = argparse.ArgumentParser(
        prog="uno-docs",
        description="Generate documentation for Uno components",
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Generate documentation command
    generate_parser = subparsers.add_parser("generate", help="Generate documentation")
    generate_parser.add_argument(
        "--module",
        "-m",
        type=str,
        required=True,
        help="Module to document (e.g., 'uno.config')",
    )
    generate_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path for documentation",
    )
    generate_parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["markdown", "md", "html", "htm", "json", "mkdocs"],
        default="markdown",
        help="Documentation format (default: markdown)",
    )
    generate_parser.add_argument(
        "--title",
        "-t",
        type=str,
        help="Documentation title",
    )

    # Validate documentation command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate documentation quality"
    )
    validate_parser.add_argument(
        "--module",
        "-m",
        type=str,
        required=True,
        help="Module to validate (e.g., 'uno.config')",
    )
    validate_parser.add_argument(
        "--coverage",
        "-c",
        type=float,
        default=0.8,
        help="Minimum documentation coverage (0.0-1.0)",
    )
    validate_parser.add_argument(
        "--require-examples",
        action="store_true",
        help="Require examples for all items",
    )
    validate_parser.add_argument(
        "--test-examples",
        action="store_true",
        help="Test code examples for syntax and runtime errors",
    )
    validate_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path for validation results",
    )

    # Sync examples command
    sync_parser = subparsers.add_parser(
        "sync-examples", help="Synchronize examples from source code to documentation"
    )
    sync_parser.add_argument(
        "--module",
        "-m",
        type=str,
        required=True,
        help="Module to synchronize examples for (e.g., 'uno.config')",
    )
    sync_parser.add_argument(
        "--source-dir",
        "-s",
        type=str,
        action="append",
        help="Directory to scan for examples (can be specified multiple times)",
    )
    sync_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path for synchronization report",
    )
    sync_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing examples instead of adding new ones",
    )

    # For backwards compatibility, handle no subcommand as "generate"
    parsed_args = parser.parse_args(args)
    if not parsed_args.command:
        # Check if we have at least --module which indicates generate command
        if hasattr(parsed_args, "module") and parsed_args.module:
            parsed_args.command = "generate"
        else:
            parser.print_help()
            return 1

    try:
        # Handle the appropriate command
        if parsed_args.command == "generate":
            await generate_documentation(
                module_name=parsed_args.module,
                output_path=parsed_args.output,
                format=parsed_args.format,
                title=parsed_args.title,
            )
            return 0
        elif parsed_args.command == "validate":
            passed, results = await validate_documentation(
                module_name=parsed_args.module,
                min_doc_coverage=parsed_args.coverage,
                require_examples=parsed_args.require_examples,
                test_examples=parsed_args.test_examples,
            )

            # Print validation results
            print(f"Documentation validation for {parsed_args.module}:")
            print(f"Total items: {results['total_items']}")
            print(f"Documented items: {results['documented_items']}")
            print(f"Coverage: {results['coverage']*100:.1f}%")
            print(
                f"Items with examples: {results['items_with_examples']}/{results['total_items']}"
            )

            # Print errors if any
            if results["validation_errors"]:
                print("\nValidation errors:")
                for error in results["validation_errors"]:
                    print(f"- {error}")

            # Write results to file if requested
            if parsed_args.output:
                output_file = Path(parsed_args.output)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, "w") as f:
                    json.dump({"passed": passed, "results": results}, f, indent=2)
                    print(f"\nResults written to {parsed_args.output}")

            return 0 if passed else 1
        elif parsed_args.command == "sync-examples":
            # Convert source_dir arguments to a list of Paths
            source_dirs = None
            if parsed_args.source_dir:
                source_dirs = [Path(d) for d in parsed_args.source_dir]

            # Run synchronization
            result = await sync_examples(
                module_name=parsed_args.module,
                source_dirs=source_dirs,
                output_path=parsed_args.output,
                overwrite_existing=parsed_args.overwrite,
            )

            # Print results
            print(f"Example synchronization for {parsed_args.module}:")
            print(f"Items updated: {result['items_updated']}")
            print(f"Total examples added: {result['total_examples_added']}")

            if result["items"]:
                print("\nUpdated items:")
                for item in result["items"]:
                    print(f"- {item['name']}: {item['examples_added']} examples added")

            return 0
        else:
            print(f"Unknown command: {parsed_args.command}")
            return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def main(args: Sequence[str] | None = None) -> int:
    """Main entry point for the CLI."""
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
