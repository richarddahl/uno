#!/usr/bin/env python3
"""
Migration script to replace LoggerProtocol with LoggerProtocol and get_logger.

This script automates the migration from the legacy LoggerProtocol to the new
LoggerProtocol and get_logger based system in the Uno framework.
"""

import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Match, Pattern

# Pattern for import statements with LoggerProtocol
IMPORT_PATTERN: Pattern = re.compile(
    r"^from uno\.logging(?:\.logger)? import (.*?LoggerProtocol.*?)$", re.MULTILINE
)

# Pattern for type annotations
TYPE_ANNOTATION_PATTERN: Pattern = re.compile(
    r"(^.*?:\s*)((?:\")?LoggerProtocol(?:\")?)(\s*(?:[,|\)].*)?$)", re.MULTILINE
)

# Pattern for LoggerProtocol constructor calls
CONSTRUCTOR_PATTERN: Pattern = re.compile(
    r"LoggerProtocol\((.*?)\)", re.MULTILINE | re.DOTALL
)


def process_file(file_path: Path) -> None:
    """
    Process a single file to replace LoggerProtocol with LoggerProtocol/get_logger.

    Args:
        file_path: Path to the file to process
    """
    if not file_path.exists() or file_path.suffix != ".py":
        return

    print(f"Processing {file_path}...")

    # Read file content
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Skip if no LoggerProtocol is found
    if "LoggerProtocol" not in content:
        return

    # 1. Replace import statements
    def import_replacer(match: Match) -> str:
        imports = match.group(1)
        if "LoggerProtocol" in imports and "LoggerProtocol" not in imports:
            # Replace LoggerProtocol with LoggerProtocol and get_logger
            imports = imports.replace("LoggerProtocol", "LoggerProtocol, get_logger")
        return f"from uno.logging import {imports}"

    content = IMPORT_PATTERN.sub(import_replacer, content)

    # 2. Replace type annotations
    def type_annotation_replacer(match: Match) -> str:
        prefix = match.group(1)
        logger_type = match.group(2)
        suffix = match.group(3) or ""

        # Replace LoggerProtocol with LoggerProtocol
        new_type = logger_type.replace("LoggerProtocol", "LoggerProtocol")
        return f"{prefix}{new_type}{suffix}"

    content = TYPE_ANNOTATION_PATTERN.sub(type_annotation_replacer, content)

    # 3. Replace constructor calls
    def constructor_replacer(match: Match) -> str:
        args = match.group(1).strip()
        # Replace LoggerProtocol(name) with get_logger(name)
        return f"get_logger({args})"

    content = CONSTRUCTOR_PATTERN.sub(constructor_replacer, content)

    # Write modified content back to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Updated {file_path}")


def process_directory(directory: Path, callback: Callable[[Path], None]) -> None:
    """
    Process all Python files in a directory recursively.

    Args:
        directory: Path to the directory to process
        callback: Function to call for each file
    """
    for item in directory.iterdir():
        if item.is_file() and item.suffix == ".py":
            callback(item)
        elif (
            item.is_dir()
            and not item.name.startswith(".")
            and not item.name == "__pycache__"
        ):
            process_directory(item, callback)


def main() -> int:
    """
    Main entry point for the migration script.

    Returns:
        Exit code (0 for success)
    """
    # Get base directory (uno project root)
    base_dir = Path(__file__).parent.parent

    # Define directories to process
    directories_to_process = [
        base_dir / "src" / "uno",
        base_dir / "examples",
        base_dir / "tests",
    ]

    print("Starting LoggerProtocol migration...")

    # Process each directory
    for directory in directories_to_process:
        if directory.exists():
            print(f"\nProcessing directory: {directory}")
            process_directory(directory, process_file)

    print("\nMigration completed successfully!")
    print("\nRecommended next steps:")
    print("1. Run your tests to verify the changes")
    print(
        "2. Check that all LoggerProtocol implementations are correctly registered in the DI container"
    )
    print("3. Update any documentation that refers to LoggerProtocol")

    return 0


if __name__ == "__main__":
    sys.exit(main())
