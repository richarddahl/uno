#!/usr/bin/env python3
"""
Script to update the DI container configuration to use LoggerProtocol instead of LoggerProtocol.

This script scans for DI container configurations and updates them to use
LoggerProtocol and get_logger instead of LoggerProtocol.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Pattern, Match

# Patterns for DI container registration with LoggerProtocol
REGISTRATION_PATTERNS: List[Pattern] = [
    # Pattern for register/register_singleton/register_scoped with LoggerProtocol
    re.compile(r"(register(?:_singleton|_scoped)?\()LoggerProtocol(,|\))"),
    # Pattern for lambda functions that return LoggerProtocol
    re.compile(r"(lambda.*?:)(\s*)LoggerProtocol\((.*?)\)"),
    # Pattern for factory functions that return LoggerProtocol
    re.compile(r"(def\s+.*?->)\s*LoggerProtocol:"),
]


def update_di_registration(file_path: Path) -> None:
    """
    Update DI container registrations in a file.

    Args:
        file_path: Path to the file to update
    """
    if not file_path.exists() or file_path.suffix != ".py":
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "LoggerProtocol" not in content and "container.register" not in content:
        return

    print(f"Processing {file_path}...")

    # Update registrations
    modified = False

    # Replace direct registrations
    new_content = re.sub(REGISTRATION_PATTERNS[0], r"\1LoggerProtocol\2", content)
    if new_content != content:
        modified = True
        content = new_content

    # Replace lambda factory functions
    new_content = re.sub(REGISTRATION_PATTERNS[1], r"\1\2get_logger(\3)", content)
    if new_content != content:
        modified = True
        content = new_content

    # Replace factory method return types
    new_content = re.sub(REGISTRATION_PATTERNS[2], r"\1 LoggerProtocol:", content)
    if new_content != content:
        modified = True
        content = new_content

    if modified:
        # Add import for LoggerProtocol and get_logger if needed
        if "from uno.logging import " in content:
            if (
                "from uno.logging import LoggerProtocol" not in content
                and "from uno.logging import get_logger" not in content
            ):
                content = re.sub(
                    r"from uno\.logging import (.*)",
                    r"from uno.logging import \1, LoggerProtocol, get_logger",
                    content,
                )
        elif "import uno.logging" in content:
            pass  # Using direct imports, no change needed
        else:
            # Add import if not present
            content = "from uno.logging import LoggerProtocol, get_logger\n" + content

        # Write updated content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ Updated DI container configuration in {file_path}")


def process_directory(directory: Path) -> None:
    """
    Process all Python files in a directory recursively.

    Args:
        directory: Directory to process
    """
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                update_di_registration(Path(root) / file)


def main() -> int:
    """
    Main entry point for the update script.

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

    print("Updating DI container configurations...")

    # Process each directory
    for directory in directories_to_process:
        if directory.exists():
            print(f"\nProcessing directory: {directory}")
            process_directory(directory)

    print("\nDI container configuration update completed successfully!")
    print("\nNext steps:")
    print("1. Run your tests to verify the changes")
    print("2. Check any custom DI configurations manually to ensure they're correct")

    return 0


if __name__ == "__main__":
    sys.exit(main())
