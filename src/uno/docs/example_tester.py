# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Example testing framework for documentation examples.

This module provides utilities to extract, verify, and test code examples
from documentation to ensure they remain accurate and functional.
"""

from __future__ import annotations

import ast
import asyncio
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from uno.docs.schema import DocumentableItem, ExampleInfo


async def extract_examples(item: DocumentableItem) -> list[ExampleInfo]:
    """
    Extract code examples from a documentable item.

    Args:
        item: The documentable item to extract examples from

    Returns:
        List of extracted code examples
    """
    # Examples are already available in the schema
    return item.schema_info.examples


async def validate_example_syntax(example: ExampleInfo) -> list[str]:
    """
    Validate the syntax of a code example.

    Args:
        example: The code example to validate

    Returns:
        List of syntax error messages (empty if valid)
    """
    if not example.code:
        return ["Example code is empty"]

    if example.language.lower() != "python":
        # Skip syntax validation for non-Python examples
        return []

    try:
        # Try to parse the code using ast
        ast.parse(example.code)
        return []
    except SyntaxError as e:
        line_num = getattr(e, "lineno", "unknown")
        return [f"Syntax error at line {line_num}: {e}"]
    except Exception as e:
        return [f"Validation error: {e}"]


async def check_examples_compatibility(
    examples: list[ExampleInfo], python_version: tuple[int, int] = (3, 13)
) -> list[str]:
    """
    Check if examples are compatible with the specified Python version.

    Args:
        examples: List of code examples to check
        python_version: Tuple of (major, minor) Python version

    Returns:
        List of compatibility issues
    """
    issues = []

    for example in examples:
        if example.language.lower() != "python":
            continue

        try:
            # Use ast with feature_version to check compatibility
            ast.parse(example.code, feature_version=python_version)
        except SyntaxError as e:
            issues.append(
                f"Example '{example.title}' is not compatible with Python {python_version[0]}.{python_version[1]}: {e}"
            )
        except Exception as e:
            issues.append(
                f"Error checking compatibility for example '{example.title}': {e}"
            )

    return issues


@contextmanager
def isolated_environment() -> Generator[dict[str, Any], None, None]:
    """
    Create an isolated environment for running code examples.

    This context manager creates a temporary directory and sets up an
    isolated environment with limited access to avoid potentially harmful operations.

    Yields:
        Dictionary of global variables for the environment
    """
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set up environment variables
        old_cwd = os.getcwd()
        os.chdir(temp_dir)

        # Create a safe globals dictionary with limited functionality
        safe_globals = {
            "__builtins__": {
                # Allow only safe builtins
                name: getattr(__builtins__, name)
                for name in [
                    "print",
                    "len",
                    "range",
                    "int",
                    "float",
                    "str",
                    "bool",
                    "list",
                    "dict",
                    "set",
                    "tuple",
                    "sum",
                    "min",
                    "max",
                    "all",
                    "any",
                    "enumerate",
                    "zip",
                    "TypeError",
                    "ValueError",
                    "Exception",
                    "True",
                    "False",
                    "None",
                ]
            },
            # Add safe modules
            "math": __import__("math"),
            "random": __import__("random"),
            "json": __import__("json"),
            "re": __import__("re"),
            "Path": Path,
            "tempfile": tempfile,
            # Provide temp directory
            "TEMP_DIR": temp_dir,
        }

        try:
            yield safe_globals
        finally:
            # Restore the original working directory
            os.chdir(old_cwd)


async def run_example(example: ExampleInfo) -> tuple[bool, str]:
    """
    Run a code example in an isolated environment.

    Args:
        example: The code example to run

    Returns:
        Tuple of (success, output/error message)
    """
    if example.language.lower() != "python":
        return False, f"Cannot run non-Python example: {example.language}"

    # Process example code to make it runnable
    runnable_code = preprocess_example_code(example.code)

    # Create an isolated environment
    with isolated_environment() as env:
        # Capture stdout and stderr
        stdout_original = sys.stdout
        stderr_original = sys.stderr
        stdout_capture = tempfile.StringIO()
        stderr_capture = tempfile.StringIO()

        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            # Execute the code
            exec(runnable_code, env)

            # Get output
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()

            # Check if there was any error output
            if stderr_output:
                return False, f"Example produced errors:\n{stderr_output}"

            return True, stdout_output
        except Exception as e:
            return False, f"Example failed to run: {e}"
        finally:
            # Restore stdout and stderr
            sys.stdout = stdout_original
            sys.stderr = stderr_original


def preprocess_example_code(code: str) -> str:
    """
    Preprocess example code to make it runnable in isolation.

    This function handles common patterns in documentation examples
    that would prevent them from running in isolation, such as:
    - Imports of the framework itself
    - References to external resources or APIs
    - Interactive example components

    Args:
        code: The code example to preprocess

    Returns:
        Preprocessed code ready for execution
    """
    lines = code.split("\n")
    processed_lines = []

    # Check for imports and add mock objects if needed
    imports = {}
    for line in lines:
        if line.strip().startswith("import ") or line.strip().startswith("from "):
            # Extract the imported module
            if "import" in line and "from" not in line:
                module = line.split("import")[1].strip().split(" as ")[0].strip()
                imports[module] = f"# Mock import: {module}"
            elif "from" in line and "import" in line:
                module = line.split("from")[1].split("import")[0].strip()
                imports[module] = f"# Mock import: {module}"

    # Add mock objects for imports
    for module, comment in imports.items():
        if module.startswith("uno."):
            # For Uno framework imports, add a mock class
            class_name = module.split(".")[-1].capitalize()
            processed_lines.append(comment)
            processed_lines.append(f"class {class_name}: pass")
            processed_lines.append(f"{module.split('.')[-1]} = {class_name}()")

    # Add the original code with any problematic lines commented out
    for line in lines:
        # Handle certain patterns that would cause issues
        if (
            line.strip().startswith("import ")
            or line.strip().startswith("from ")
            or "await " in line
            or "async " in line
        ):
            # Comment out async/await lines and imports that might fail
            processed_lines.append(f"# {line}")
        else:
            processed_lines.append(line)

    return "\n".join(processed_lines)


async def test_all_examples(item: DocumentableItem) -> list[str]:
    """
    Test all examples in a documentable item.

    Args:
        item: The documentable item containing examples

    Returns:
        List of error messages for failed examples (empty if all passed)
    """
    errors = []

    # Extract examples from the item
    examples = await extract_examples(item)

    # Test each example
    for example in examples:
        # First, validate syntax
        syntax_errors = await validate_example_syntax(example)
        if syntax_errors:
            for error in syntax_errors:
                errors.append(f"Syntax error in example '{example.title}': {error}")
            continue  # Skip running the example if it has syntax errors

        # If Python example, try to run it
        if example.language.lower() == "python":
            success, output = await run_example(example)
            if not success:
                errors.append(f"Example '{example.title}' failed: {output}")

    return errors


async def validate_examples(
    items: list[DocumentableItem],
) -> tuple[bool, dict[str, Any]]:
    """
    Validate examples in a list of documentable items.

    Args:
        items: List of documentable items to validate

    Returns:
        Tuple of (passed, details) where details contains validation metrics
    """
    results = {
        "total_items": len(items),
        "items_with_examples": 0,
        "total_examples": 0,
        "valid_examples": 0,
        "syntax_errors": 0,
        "runtime_errors": 0,
        "items_with_errors": 0,
        "error_details": [],
    }

    for item in items:
        schema = item.schema_info
        examples = schema.examples

        # Count items with examples
        if examples:
            results["items_with_examples"] += 1
            results["total_examples"] += len(examples)

            # Validate syntax for all examples
            syntax_issues = []
            for example in examples:
                syntax_errors = await validate_example_syntax(example)
                if syntax_errors:
                    results["syntax_errors"] += 1
                    syntax_issues.extend(syntax_errors)

            # Run Python examples
            python_examples = [ex for ex in examples if ex.language.lower() == "python"]
            if python_examples:
                for example in python_examples:
                    # Skip examples with syntax errors
                    if await validate_example_syntax(example):
                        continue

                    success, output = await run_example(example)
                    if not success:
                        results["runtime_errors"] += 1
                        syntax_issues.append(
                            f"Runtime error in '{example.title}': {output}"
                        )

            # Record any issues
            if syntax_issues:
                results["items_with_errors"] += 1
                results["error_details"].append(
                    {"item": schema.name, "errors": syntax_issues}
                )
            else:
                # All examples in this item are valid
                results["valid_examples"] += len(examples)

    # Calculate valid examples percentage
    if results["total_examples"] > 0:
        results["example_success_rate"] = (
            results["valid_examples"] / results["total_examples"]
        )
    else:
        results["example_success_rate"] = 1.0

    # Determine if validation passed (all items with examples have valid examples)
    passed = results["items_with_errors"] == 0 and (
        results["items_with_examples"] > 0 or results["total_items"] == 0
    )

    return passed, results


def example_validator(item: DocumentableItem) -> list[str]:
    """
    Validator function for documentation examples that can be used with validate_documentation.

    Args:
        item: Documentable item to validate

    Returns:
        List of validation error messages
    """
    # Run the example tests synchronously since validators in validate_documentation are sync
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(test_all_examples(item))
