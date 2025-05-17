# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Testing utilities for documentation completeness and accuracy.

This module provides tools to validate documentation quality and correctness.
"""

from __future__ import annotations

import inspect
import re
from typing import Any, Callable, TypeVar, cast

from uno.docs.schema import DocumentableItem, SchemaInfo
from uno.docs.discovery import discover_documentable_items
from uno.docs.example_tester import validate_examples, example_validator

T = TypeVar("T")


async def validate_documentation(
    module_name: str,
    min_doc_coverage: float = 0.8,
    require_examples: bool = True,
    validators: list[Callable[[DocumentableItem], list[str]]] | None = None,
    test_examples: bool = False,
) -> tuple[bool, dict[str, Any]]:
    """
    Validate the documentation quality for a module.

    Args:
        module_name: Module to validate
        min_doc_coverage: Minimum required documentation coverage (0.0-1.0)
        require_examples: Whether examples are required for all items
        validators: Custom validation functions
        test_examples: Whether to test code examples for syntax and runtime errors

    Returns:
        Tuple of (passed, details) where details contains validation metrics
    """
    # Discover all documentable items
    items = await discover_documentable_items(module_name)

    # Initialize validation results
    results = {
        "total_items": len(items),
        "documented_items": 0,
        "items_with_examples": 0,
        "items_with_fields": 0,
        "documented_fields": 0,
        "total_fields": 0,
        "validation_errors": [],
        "coverage": 0.0,
    }

    # Check each item
    for item in items:
        schema = item.schema_info

        # Check if item has a description
        if schema.description and len(schema.description.strip()) > 20:
            results["documented_items"] += 1

        # Check for examples
        if schema.examples:
            results["items_with_examples"] += 1

        # Check fields
        if schema.fields:
            results["items_with_fields"] += 1
            results["total_fields"] += len(schema.fields)

            # Count documented fields
            for field in schema.fields:
                if field.description and len(field.description.strip()) > 10:
                    results["documented_fields"] += 1

        # Run custom validators
        if validators:
            for validator in validators:
                errors = validator(item)
                if errors:
                    for error in errors:
                        results["validation_errors"].append(f"{schema.name}: {error}")

    # Calculate coverage
    if results["total_items"] > 0:
        results["coverage"] = results["documented_items"] / results["total_items"]

    # Run example testing if requested
    if test_examples:
        examples_passed, example_results = await validate_examples(items)
        results["example_validation"] = example_results

        # Add example validation errors to the main error list
        if "error_details" in example_results:
            for error_item in example_results.get("error_details", []):
                item_name = error_item.get("item", "Unknown")
                for error in error_item.get("errors", []):
                    results["validation_errors"].append(f"{item_name}: {error}")

    # Determine if validation passed
    passed = (
        results["coverage"] >= min_doc_coverage
        and (
            not require_examples
            or results["items_with_examples"] == results["total_items"]
        )
        and len(results["validation_errors"]) == 0
    )

    return passed, results


async def validate_documentation_examples(
    module_name: str,
) -> tuple[bool, dict[str, Any]]:
    """
    Specifically validate examples in documentation for a module.

    This is a convenience wrapper around validate_examples that first
    discovers documentable items in the module.

    Args:
        module_name: Module to validate examples for

    Returns:
        Tuple of (passed, details) where details contains validation metrics
    """
    # Discover all documentable items
    items = await discover_documentable_items(module_name)

    # Run example validation
    return await validate_examples(items)
