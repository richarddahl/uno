# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Schema extractors for the Uno documentation system.

This package provides extractors for generating documentation schema
from various types of objects.
"""

from __future__ import annotations

from typing import Sequence

from uno.docs.protocols import SchemaExtractorProtocol
from uno.docs.extractors.config_extractor import ConfigExtractor
from uno.docs.extractors.api_extractor import ApiEndpointExtractor
from uno.docs.extractors.model_extractor import ModelExtractor
from uno.docs.extractors.service_extractor import ServiceExtractor
from uno.docs.extractors.cli_extractor import CliCommandExtractor


async def get_extractors() -> Sequence[SchemaExtractorProtocol]:
    """
    Get all available schema extractors.

    Returns:
        List of schema extractors
    """
    # Type ignore because Protocol classes can't be instantiated directly
    # but we know these implementations follow the protocol
    return [
        ConfigExtractor(),  # Configuration classes
        ApiEndpointExtractor(),  # API endpoints
        ModelExtractor(),  # Data models
        ServiceExtractor(),  # Service classes
        CliCommandExtractor(),  # CLI commands
    ]


__all__ = [
    "get_extractors",
    "ConfigExtractor",
    "ApiEndpointExtractor",
    "ModelExtractor",
    "ServiceExtractor",
    "CliCommandExtractor",
]
