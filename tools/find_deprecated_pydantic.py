#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Script to find Pydantic models using deprecated class-based Config.

Usage:
    python find_deprecated_pydantic.py [directory]

If directory is not specified, it will search in the current directory.
"""

import os
import re
import sys
import ast
from pathlib import Path
from typing import List, Tuple


class PydanticModelVisitor(ast.NodeVisitor):
    """AST visitor to find Pydantic models with class-based Config."""

    def __init__(self):
        self.models_with_class_config = []

    def visit_ClassDef(self, node):
        # Check if class inherits from a Pydantic model
        is_pydantic_model = False
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in ("BaseModel", "BaseSettings"):
                is_pydantic_model = True
            elif isinstance(base, ast.Attribute) and base.attr in (
                "BaseModel",
                "BaseSettings",
            ):
                is_pydantic_model = True

        if is_pydantic_model:
            # Look for nested Config class
            for item in node.body:
                if isinstance(item, ast.ClassDef) and item.name == "Config":
                    self.models_with_class_config.append((node.name, item))

        # Continue visiting child nodes
        self.generic_visit(node)


def find_deprecated_models(directory: Path) -> List[Tuple[Path, str, ast.ClassDef]]:
    """Find Pydantic models using deprecated Config class style."""
    results = []

    for path in directory.glob("**/*.py"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse the file
            try:
                tree = ast.parse(content)
                visitor = PydanticModelVisitor()
                visitor.visit(tree)

                # Add results
                for model_name, config_node in visitor.models_with_class_config:
                    results.append((path, model_name, config_node))

            except SyntaxError:
                print(f"Syntax error in {path}")

        except Exception as e:
            print(f"Error processing {path}: {e}")

    return results


def print_results(results: List[Tuple[Path, str, ast.ClassDef]]):
    """Print models using deprecated Config class and suggest how to fix."""
    if not results:
        print("No deprecated Pydantic Config classes found!")
        return

    print(f"Found {len(results)} Pydantic models using deprecated class-based Config:")
    print("\nFix these by replacing:\n")
    print("    class Config:")
    print("        extra = 'ignore'")
    print("\nWith:\n")
    print("    model_config = ConfigDict(")
    print("        extra='ignore',")
    print("    )")
    print("\nOr for settings classes:\n")
    print("    model_config = SettingsConfigDict(")
    print("        extra='ignore',")
    print("    )")
    print("\nDetailed findings:")
    print("=" * 80)

    for path, model_name, config_node in results:
        print(f"{path}:{config_node.lineno} - Class {model_name}")

    print("\nSee the Pydantic v2 migration guide for more details:")
    print("https://docs.pydantic.dev/latest/migration/")


if __name__ == "__main__":
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    results = find_deprecated_models(directory)
    print_results(results)
