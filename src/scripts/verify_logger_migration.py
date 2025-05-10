#!/usr/bin/env python3
"""
Test script to verify the LoggerProtocol to LoggerProtocol migration.

This script checks if any LoggerProtocol references remain in the codebase
after the migration script has been run.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


def find_logger_service_references(directory: Path) -> List[Tuple[Path, int, str]]:
    """
    Find any remaining references to LoggerProtocol in the codebase.

    Args:
        directory: Base directory to search in

    Returns:
        List of tuples containing (file_path, line_number, line_content)
    """
    references = []

    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = Path(root) / file

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        if "LoggerProtocol" in line:
                            references.append((file_path, i, line.strip()))
            except UnicodeDecodeError:
                # Skip binary files
                pass

    return references


def main() -> int:
    """
    Main entry point for the verification script.

    Returns:
        Exit code (0 if no references found, 1 otherwise)
    """
    # Get base directory (uno project root)
    base_dir = Path(__file__).parent.parent

    # Define directories to check
    directories_to_check = [
        base_dir / "src" / "uno",
        base_dir / "examples",
        base_dir / "tests",
    ]

    all_references = []

    # Find references in each directory
    for directory in directories_to_check:
        if directory.exists():
            references = find_logger_service_references(directory)
            all_references.extend(references)

    # Print results
    if all_references:
        print(f"Found {len(all_references)} references to LoggerProtocol:")
        for file_path, line_number, line_content in all_references:
            relative_path = file_path.relative_to(base_dir)
            print(f"{relative_path}:{line_number}: {line_content}")
        return 1
    else:
        print("No references to LoggerProtocol found. Migration successful!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
