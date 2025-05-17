# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Relationship graph generator for visualizing component dependencies.

This module provides utilities to detect and visualize relationships
between components in the Uno framework.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import os
from pathlib import Path
from typing import Any, cast

from uno.docs.schema import DocumentableItem, DocumentationType


class RelationshipNode:
    """Node representing a component in the relationship graph."""

    def __init__(
        self,
        id: str,
        name: str,
        type: DocumentationType,
        module: str,
    ) -> None:
        """Initialize a relationship node."""
        self.id = id
        self.name = name
        self.type = type
        self.module = module

    def to_dict(self) -> dict[str, Any]:
        """Convert the node to a dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "module": self.module,
        }


class RelationshipEdge:
    """Edge representing a relationship between components."""

    def __init__(
        self,
        source: str,
        target: str,
        type: str,
        weight: int = 1,
        description: str | None = None,
    ) -> None:
        """Initialize a relationship edge."""
        self.source = source
        self.target = target
        self.type = type
        self.weight = weight
        self.description = description

    def to_dict(self) -> dict[str, Any]:
        """Convert the edge to a dictionary representation."""
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "weight": self.weight,
            "description": self.description,
        }


class RelationshipGraph:
    """Graph representing relationships between components."""

    def __init__(self) -> None:
        """Initialize an empty relationship graph."""
        self.nodes: dict[str, RelationshipNode] = {}
        self.edges: list[RelationshipEdge] = []

    def add_node(self, node: RelationshipNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: RelationshipEdge) -> None:
        """Add an edge to the graph."""
        # Only add edge if both source and target nodes exist
        if edge.source in self.nodes and edge.target in self.nodes:
            self.edges.append(edge)

    def to_dict(self) -> dict[str, Any]:
        """Convert the graph to a dictionary representation."""
        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
        }


async def build_relationship_graph(
    items: list[DocumentableItem],
    include_modules: bool = True,
) -> RelationshipGraph:
    """
    Build a relationship graph from documentable items.

    Args:
        items: List of documentable items
        include_modules: Whether to include module relationships

    Returns:
        Relationship graph
    """
    graph = RelationshipGraph()

    # First pass: add all items as nodes
    for item in items:
        schema = item.schema_info
        node = RelationshipNode(
            id=f"{schema.module}.{schema.name}",
            name=schema.name,
            type=schema.type,
            module=schema.module,
        )
        graph.add_node(node)

    # Second pass: detect relationships and add edges
    for item in items:
        schema = item.schema_info
        item_id = f"{schema.module}.{schema.name}"

        # 1. Base classes for inheritance relationships
        for base_class in schema.base_classes:
            edge = RelationshipEdge(
                source=item_id,
                target=base_class,
                type="inherits",
                description=f"{schema.name} inherits from {base_class.split('.')[-1]}",
            )
            graph.add_edge(edge)

        # 2. Dependencies from constructor arguments
        if (
            schema.type == DocumentationType.SERVICE
            and "dependencies" in schema.extra_info
        ):
            for dep in schema.extra_info["dependencies"]:
                # Try to match dependency to a node by name in any module
                for node_id, node in graph.nodes.items():
                    if node.name == dep["type"].split(".")[-1]:
                        edge = RelationshipEdge(
                            source=item_id,
                            target=node_id,
                            type="depends",
                            description=f"{schema.name} depends on {node.name}",
                        )
                        graph.add_edge(edge)

        # 3. API endpoint relationships with models
        if schema.type == DocumentationType.API:
            for field in schema.fields:
                if (
                    "response_model" in field.extra_info
                    and field.extra_info["response_model"]
                ):
                    response_model_name = field.extra_info["response_model"].split(".")[
                        -1
                    ]
                    # Look for matching model node
                    for node_id, node in graph.nodes.items():
                        if (
                            node.name == response_model_name
                            and node.type == DocumentationType.MODEL
                        ):
                            edge = RelationshipEdge(
                                source=item_id,
                                target=node_id,
                                type="returns",
                                description=f"{schema.name} returns {node.name}",
                            )
                            graph.add_edge(edge)

        # 4. CLI command relationships with service/config
        if schema.type == DocumentationType.CLI:
            # Look for potential service dependencies
            for node_id, node in graph.nodes.items():
                if (
                    node.type == DocumentationType.SERVICE
                    and node.name.lower() in schema.name.lower()
                ):
                    edge = RelationshipEdge(
                        source=item_id,
                        target=node_id,
                        type="uses",
                        description=f"{schema.name} uses {node.name}",
                    )
                    graph.add_edge(edge)

    # Add module relationships if requested
    if include_modules:
        await _add_module_relationships(graph, items)

    return graph


async def _add_module_relationships(
    graph: RelationshipGraph,
    items: list[DocumentableItem],
) -> None:
    """
    Add module-level relationships to the graph.

    This detects parent-child relationships between modules and adds them as edges.

    Args:
        graph: Relationship graph to update
        items: List of documentable items
    """
    modules = set()

    # Collect all modules
    for item in items:
        modules.add(item.schema_info.module)

    # Add module nodes
    for module_name in modules:
        parts = module_name.split(".")
        node = RelationshipNode(
            id=module_name,
            name=parts[-1],
            type=DocumentationType.OTHER,
            module=".".join(parts[:-1]) if len(parts) > 1 else "",
        )
        graph.add_node(node)

    # Add module relationships
    for module_name in modules:
        parts = module_name.split(".")
        if len(parts) > 1:
            parent_module = ".".join(parts[:-1])
            if parent_module in graph.nodes:
                edge = RelationshipEdge(
                    source=module_name,
                    target=parent_module,
                    type="in",
                    description=f"{parts[-1]} is in {parent_module}",
                )
                graph.add_edge(edge)


async def detect_impl_protocol_relationships(
    graph: RelationshipGraph,
    items: list[DocumentableItem],
) -> None:
    """
    Detect implementation-protocol relationships.

    This identifies classes that implement protocols and adds them as edges.

    Args:
        graph: Relationship graph to update
        items: List of documentable items
    """
    # Find protocol nodes
    protocol_nodes = {
        node_id: node
        for node_id, node in graph.nodes.items()
        if node.name.endswith("Protocol")
    }

    # For each item, check if it implements any protocol
    for item in items:
        if not hasattr(item.original, "__annotations__"):
            continue

        schema = item.schema_info
        item_id = f"{schema.module}.{schema.name}"

        # Skip protocol definitions themselves
        if schema.name.endswith("Protocol"):
            continue

        # Check the class's annotations and methods
        for protocol_id, protocol_node in protocol_nodes.items():
            protocol_name = protocol_node.name

            # Simple name-based heuristic for implementation naming convention
            # Example: FooProtocol -> Foo
            if protocol_name.endswith("Protocol"):
                expected_impl_name = protocol_name[:-8]  # Remove "Protocol" suffix
                if schema.name == expected_impl_name:
                    edge = RelationshipEdge(
                        source=item_id,
                        target=protocol_id,
                        type="implements",
                        description=f"{schema.name} implements {protocol_name}",
                    )
                    graph.add_edge(edge)
                    continue

            # TODO: More sophisticated protocol implementation detection
            # We would need to check that all protocol methods are implemented
            # This would require access to method signatures and comparing them


async def filter_graph(
    graph: RelationshipGraph,
    types: list[DocumentationType] | None = None,
    modules: list[str] | None = None,
) -> RelationshipGraph:
    """
    Filter a relationship graph by node types and modules.

    Args:
        graph: Relationship graph to filter
        types: List of node types to include (None = all)
        modules: List of modules to include (None = all)

    Returns:
        Filtered relationship graph
    """
    filtered = RelationshipGraph()

    # Filter nodes
    for node_id, node in graph.nodes.items():
        include = True

        if types and node.type not in types:
            include = False

        if modules and not any(node.module.startswith(m) for m in modules):
            include = False

        if include:
            filtered.add_node(node)

    # Filter edges (only include edges where both nodes are in the filtered graph)
    for edge in graph.edges:
        if edge.source in filtered.nodes and edge.target in filtered.nodes:
            filtered.add_edge(edge)

    return filtered
