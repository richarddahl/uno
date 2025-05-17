# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Schema models for the Uno documentation system.

This module defines the data models used to represent documentation schema.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentationType(str, Enum):
    """Type of documentable item."""

    CONFIG = "config"
    API = "api"
    MODEL = "model"
    SERVICE = "service"
    CLI = "cli"
    OTHER = "other"


class ExampleInfo(BaseModel):
    """Information about an example."""

    title: str = "Example"
    code: str
    language: str = "python"
    description: str | None = None


class FieldInfo(BaseModel):
    """Information about a field in a schema."""

    name: str
    type_name: str
    type_hint: str
    default_value: str | None = None
    description: str = ""
    is_required: bool = False
    is_secure: bool = False
    secure_handling: str | None = None
    validators: list[str] = Field(default_factory=list)
    extra_info: dict[str, Any] = Field(default_factory=dict)


class SchemaInfo(BaseModel):
    """Schema information for a documentable item."""

    name: str
    module: str
    description: str = ""
    type: DocumentationType = DocumentationType.OTHER
    fields: list[FieldInfo] = Field(default_factory=list)
    base_classes: list[str] = Field(default_factory=list)
    examples: list[ExampleInfo] = Field(default_factory=list)
    extra_info: dict[str, Any] = Field(default_factory=dict)


class DocumentableItem(BaseModel):
    """A documentable item with its schema information."""

    # Rename 'schema' to 'schema_info' to avoid shadowing BaseModel attribute
    schema_info: SchemaInfo
    original: Any | None = None
