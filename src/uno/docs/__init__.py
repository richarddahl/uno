# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Documentation generation for the Uno framework.

This module provides utilities for generating documentation from various
components of the Uno framework, making them more discoverable and understandable.
"""

from uno.docs.protocols import DocumentationProviderProtocol, SchemaExtractorProtocol
from uno.docs.providers import (
    MarkdownProvider,
    HTMLProvider,
    MkDocsProvider,
    JsonProvider,
)
from uno.docs.schema import DocumentableItem, SchemaInfo, FieldInfo, ExampleInfo
from uno.docs.discovery import discover_documentable_items
from uno.docs.testing import validate_documentation, validate_documentation_examples
from uno.docs.search import create_search_index, search_items
from uno.docs.example_sync import sync_examples_for_module
from uno.docs.api_playground import (
    generate_api_playground_html,
    execute_api_call,
    ApiEndpointInfo,
    ApiExecutionRequest,
    ApiExecutionResponse,
)
from uno.docs.landing_page import (
    LandingPageConfig,
    LandingPageSection,
    generate_landing_page,
    generate_default_landing_page,
)

# Import the cli module, not the specific functions (to avoid circular imports)
from uno.docs import cli

# Use the generate_documentation function from cli module
generate_documentation = cli.generate_documentation
test_documentation_examples = cli.test_documentation_examples
sync_examples = cli.sync_examples

__all__ = [
    # Core protocols
    "DocumentationProviderProtocol",
    "SchemaExtractorProtocol",
    # Schema information classes
    "DocumentableItem",
    "SchemaInfo",
    "FieldInfo",
    "ExampleInfo",
    # Providers
    "MarkdownProvider",
    "HTMLProvider",
    "MkDocsProvider",
    "JsonProvider",
    # Discovery utilities
    "discover_documentable_items",
    # Testing utilities
    "validate_documentation",
    "validate_documentation_examples",
    # Search utilities
    "create_search_index",
    "search_items",
    # Example sync utilities
    "sync_examples_for_module",
    "sync_examples",
    # API playground utilities
    "generate_api_playground_html",
    "execute_api_call",
    "ApiEndpointInfo",
    "ApiExecutionRequest",
    "ApiExecutionResponse",
    # Landing page utilities
    "LandingPageConfig",
    "LandingPageSection",
    "generate_landing_page",
    "generate_default_landing_page",
    # CLI utilities
    "generate_documentation",
    "test_documentation_examples",
]
