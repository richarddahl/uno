# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Example synchronization for documentation.

This module provides utilities to extract and synchronize code examples
from source files and tests to keep documentation examples up-to-date.
"""

from __future__ import annotations

import ast
import inspect
import os
import re
from pathlib import Path
from typing import Any, cast

from uno.docs.schema import DocumentableItem, ExampleInfo, SchemaInfo


class ExampleExtractor:
    """Extracts example code from source files and tests."""

    # Regular expression for example annotation comments
    EXAMPLE_ANNOTATION_RE = re.compile(
        r"#\s*@example(?:\[(\w+)\])?\s*:\s*(.*?)(?:\s+@end-example|\Z)",
        re.DOTALL,
    )

    # Regular expression for test function examples
    TEST_FUNCTION_RE = re.compile(
        r"test_(\w+)|(\w+)_test",
    )

    async def extract_from_file(
        self,
        file_path: Path,
        target_name: str | None = None,
    ) -> dict[str, list[ExampleInfo]]:
        """
        Extract examples from a Python file.

        Args:
            file_path: Path to the Python file
            target_name: Optional target item name to filter examples

        Returns:
            Dictionary mapping item names to lists of example info
        """
        if not file_path.exists() or file_path.suffix != ".py":
            return {}

        examples: dict[str, list[ExampleInfo]] = {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract examples from annotation comments
            annotation_examples = await self._extract_annotation_examples(
                content, target_name
            )
            for name, example_list in annotation_examples.items():
                if name not in examples:
                    examples[name] = []
                examples[name].extend(example_list)

            # Extract examples from test functions if this is a test file
            if "test_" in file_path.name or "_test" in file_path.name:
                test_examples = await self._extract_test_examples(
                    content, file_path, target_name
                )
                for name, example_list in test_examples.items():
                    if name not in examples:
                        examples[name] = []
                    examples[name].extend(example_list)

        except Exception as e:
            print(f"Error extracting examples from {file_path}: {e}")

        return examples

    async def _extract_annotation_examples(
        self,
        content: str,
        target_name: str | None = None,
    ) -> dict[str, list[ExampleInfo]]:
        """Extract examples from annotation comments in source code."""
        examples: dict[str, list[ExampleInfo]] = {}

        # Find all example annotations
        for match in self.EXAMPLE_ANNOTATION_RE.finditer(content):
            try:
                # Get the target and example text
                target = match.group(1) or ""  # The target item name (if specified)
                example_text = match.group(2).strip()

                # Skip if we're filtering by target and this doesn't match
                if target_name and target and target != target_name:
                    continue

                # Extract the example code
                example_lines = example_text.split("\n")

                # Remove common indentation
                if len(example_lines) > 1:
                    # Find minimum indentation (excluding empty lines)
                    indents = [
                        len(line) - len(line.lstrip())
                        for line in example_lines
                        if line.strip()
                    ]
                    if indents:
                        min_indent = min(indents)
                        # Remove that amount of indentation from all lines
                        example_lines = [
                            line[min_indent:] if line.strip() else line
                            for line in example_lines
                        ]

                # Determine the target item name
                example_target = target or self._infer_target_from_context(
                    content, match.start()
                )
                if not example_target:
                    continue  # Skip if no target determined

                # Create the example info
                title = f"Example for {example_target}"
                language = "python"  # Default to Python

                # Look for title in a comment above the example
                start_pos = max(0, match.start() - 200)  # Look back up to 200 chars
                context_before = content[start_pos : match.start()]
                title_match = re.search(r"#\s*Title:\s*(.*?)(?:\n|$)", context_before)
                if title_match:
                    title = title_match.group(1).strip()

                # Look for language specification
                lang_match = re.search(r"#\s*Language:\s*(.*?)(?:\n|$)", context_before)
                if lang_match:
                    language = lang_match.group(1).strip().lower()

                example = ExampleInfo(
                    title=title,
                    code="\n".join(example_lines),
                    language=language,
                    description=f"Example extracted from source code annotation",
                )

                # Add to examples dictionary
                if example_target not in examples:
                    examples[example_target] = []
                examples[example_target].append(example)

            except Exception as e:
                print(f"Error processing example annotation: {e}")

        return examples

    async def _extract_test_examples(
        self,
        content: str,
        file_path: Path,
        target_name: str | None = None,
    ) -> dict[str, list[ExampleInfo]]:
        """Extract examples from test functions."""
        examples: dict[str, list[ExampleInfo]] = {}

        try:
            # Parse the code
            tree = ast.parse(content)

            # Find test functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and (
                    node.name.startswith("test_") or node.name.endswith("_test")
                ):
                    # Extract target from test function name
                    target = None
                    match = self.TEST_FUNCTION_RE.match(node.name)
                    if match:
                        # Get the name part (without test_ or _test)
                        target = match.group(1) or match.group(2)

                        # Convert snake_case to CamelCase if needed
                        if "_" in target:
                            parts = target.split("_")
                            target = "".join(p.capitalize() for p in parts)

                    # Skip if target doesn't match requested target
                    if target_name and target and target != target_name:
                        continue

                    # Extract the function's code
                    func_lines = content.splitlines()[node.lineno - 1 : node.end_lineno]

                    # Remove function definition and common indentation
                    if len(func_lines) > 1:
                        func_lines = func_lines[1:]  # Skip the def line
                        # Find minimum indentation (excluding empty lines)
                        indents = [
                            len(line) - len(line.lstrip())
                            for line in func_lines
                            if line.strip()
                        ]
                        if indents:
                            min_indent = min(indents)
                            # Remove that amount of indentation from all lines
                            func_lines = [
                                line[min_indent:] if line.strip() else line
                                for line in func_lines
                            ]

                    # Create example
                    if target:
                        example = ExampleInfo(
                            title=f"Example from test {node.name}",
                            code="\n".join(func_lines),
                            language="python",
                            description=f"Example extracted from test function in {file_path.name}",
                        )

                        # Add to examples dictionary
                        if target not in examples:
                            examples[target] = []
                        examples[target].append(example)

        except SyntaxError:
            # Skip files with syntax errors
            pass
        except Exception as e:
            print(f"Error extracting test examples from {file_path}: {e}")

        return examples

    def _infer_target_from_context(self, content: str, pos: int) -> str | None:
        """Infer the target item name from the context around the example."""
        # Look back up to 500 characters to find a class or function definition
        start = max(0, pos - 500)
        context = content[start:pos]

        # Look for class definition
        class_match = re.search(r"class\s+(\w+)", context)
        if class_match:
            return class_match.group(1)

        # Look for function definition
        func_match = re.search(r"def\s+(\w+)", context)
        if func_match:
            return func_match.group(1)

        return None


class ExampleSynchronizer:
    """Synchronizes examples between code and documentation."""

    def __init__(self) -> None:
        """Initialize the example synchronizer."""
        self.extractor = ExampleExtractor()

    async def sync_examples(
        self,
        items: list[DocumentableItem],
        source_dirs: list[str | Path],
        overwrite_existing: bool = False,
    ) -> dict[str, list[ExampleInfo]]:
        """
        Synchronize examples from source code to documentation.

        Args:
            items: List of documentable items to update
            source_dirs: List of directories to scan for examples
            overwrite_existing: Whether to overwrite existing examples

        Returns:
            Dictionary mapping item names to lists of added examples
        """
        # Build a map of item names to items
        items_by_name: dict[str, DocumentableItem] = {}
        for item in items:
            items_by_name[item.schema_info.name] = item

        # Track added examples
        added_examples: dict[str, list[ExampleInfo]] = {}

        # Process each source directory
        for source_dir in source_dirs:
            source_path = Path(source_dir)
            if not source_path.exists() or not source_path.is_dir():
                continue

            # Find all Python files
            for path in source_path.glob("**/*.py"):
                # Extract examples from file
                file_examples = await self.extractor.extract_from_file(path)

                # Update items with examples
                for name, examples in file_examples.items():
                    if name in items_by_name:
                        item = items_by_name[name]

                        # Track examples before modification
                        if name not in added_examples:
                            added_examples[name] = []

                        # Update the schema with new examples
                        if overwrite_existing:
                            # Replace all examples
                            item.schema_info.examples = examples
                            added_examples[name].extend(examples)
                        else:
                            # Add new examples that don't duplicate existing ones
                            existing_code = {
                                ex.code.strip() for ex in item.schema_info.examples
                            }
                            for example in examples:
                                if example.code.strip() not in existing_code:
                                    item.schema_info.examples.append(example)
                                    added_examples[name].append(example)

        return added_examples


async def sync_examples_for_module(
    module_name: str,
    source_dirs: list[str | Path] | None = None,
    overwrite_existing: bool = False,
) -> dict[str, Any]:
    """
    Synchronize examples for a module.

    This is a convenience wrapper that discovers documentable items
    and synchronizes examples from source code.

    Args:
        module_name: Name of the module to synchronize examples for
        source_dirs: List of directories to scan for examples
        overwrite_existing: Whether to overwrite existing examples

    Returns:
        Dictionary with synchronization results
    """
    from uno.docs.discovery import discover_documentable_items

    # If no source dirs specified, use some defaults
    if not source_dirs:
        # Try to find source directory based on module name
        module = __import__(module_name, fromlist=[""])
        module_file = inspect.getfile(module)
        module_dir = Path(module_file).parent

        # Add module directory and tests directory
        source_dirs = [module_dir]

        # Look for tests directory
        tests_dir = module_dir / "tests"
        if tests_dir.exists() and tests_dir.is_dir():
            source_dirs.append(tests_dir)

        # Try one level up for tests
        tests_dir = module_dir.parent / "tests"
        if tests_dir.exists() and tests_dir.is_dir():
            source_dirs.append(tests_dir)

    # Discover documentable items
    items = await discover_documentable_items(module_name)

    # Synchronize examples
    synchronizer = ExampleSynchronizer()
    added = await synchronizer.sync_examples(
        items,
        source_dirs,
        overwrite_existing=overwrite_existing,
    )

    # Build result statistics
    result = {
        "module": module_name,
        "items_updated": len(added),
        "total_examples_added": sum(len(examples) for examples in added.values()),
        "items": [
            {
                "name": name,
                "examples_added": len(examples),
            }
            for name, examples in added.items()
        ],
    }

    return result
