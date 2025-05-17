#!/usr/bin/env python3
"""
Validation script to check that all DI container configurations use LoggerProtocol.

This script scans the codebase for DI container configurations and checks that they
use LoggerProtocol instead of LoggerProtocol.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Pattern

# Patterns to check for incorrect DI container usage
PATTERNS_TO_CHECK: List[Pattern] = [
    # Pattern for registering LoggerProtocol
    re.compile(r"register(?:_singleton|_scoped)?\(\s*LoggerProtocol\b"),
    # Pattern for lambda functions returning LoggerProtocol
    re.compile(r"lambda.*?:\s*LoggerProtocol\("),
    # Pattern for factory methods returning LoggerProtocol
    re.compile(r"def\s+.*?->\s*LoggerProtocol:"),
]


def check_di_configuration(file_path: Path) -> List[Tuple[int, str]]:
    """
    Check a file for incorrect DI container usage.

    Args:
        file_path: Path to the file to check

    Returns:
        List of tuples with (line_number, line_content) for each issue found
    """
    issues = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            for pattern in PATTERNS_TO_CHECK:
                if pattern.search(line):
                    issues.append((i, line.strip()))
    except UnicodeDecodeError:
        # Skip binary files
        pass

    return issues


def check_directory(directory: Path) -> List[Tuple[Path, int, str]]:
    """
    Check all Python files in a directory for incorrect DI container usage.

    Args:
        directory: Directory to check

    Returns:
        List of tuples with (file_path, line_number, line_content)
    """
    all_issues = []

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                issues = check_di_configuration(file_path)

                if issues:
                    all_issues.extend(
                        [(file_path, line_num, content) for line_num, content in issues]
                    )

    return all_issues


def main() -> int:
    """
    Main entry point for the validation script.

    Returns:
        Exit code (0 if no issues found, 1 otherwise)
    """
    # Get base directory (uno project root)
    base_dir = Path(__file__).parent.parent

    # Define directories to check
    directories_to_check = [
        base_dir / "src" / "uno",
        base_dir / "examples",
        base_dir / "tests",
    ]

    all_issues = []

    # Check each directory
    for directory in directories_to_check:
        if directory.exists():
            issues = check_directory(directory)
            all_issues.extend(issues)

    # Print results
    if all_issues:
        print(f"Found {len(all_issues)} DI container issues:")
        for file_path, line_number, line_content in all_issues:
            relative_path = file_path.relative_to(base_dir)
            print(f"{relative_path}:{line_number}: {line_content}")
        return 1
    else:
        print(
            "No DI container issues found. All configurations are using LoggerProtocol!"
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
