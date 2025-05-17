# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Enhanced search capabilities for documentation.

This module provides advanced search functionality with relevance scoring,
filtering, and highlighting for the Uno documentation system.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from uno.docs.schema import DocumentableItem, DocumentationType


class SearchResultType(str, Enum):
    """Type of search result match."""

    TITLE = "title"
    DESCRIPTION = "description"
    FIELD = "field"
    FIELD_DESCRIPTION = "field_description"
    EXAMPLE = "example"
    MODULE = "module"


@dataclass
class SearchMatch:
    """A match in the search results."""

    text: str
    type: SearchResultType
    field_name: str | None = None
    fragment: str | None = None
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert the match to a dictionary."""
        return {
            "text": self.text,
            "type": self.type.value,
            "field_name": self.field_name,
            "fragment": self.fragment,
            "score": self.score,
        }


@dataclass
class SearchResult:
    """A search result for a documentable item."""

    item: DocumentableItem
    matches: list[SearchMatch] = field(default_factory=list)
    total_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a dictionary."""
        return {
            "item_name": self.item.schema_info.name,
            "item_type": self.item.schema_info.type.value,
            "item_module": self.item.schema_info.module,
            "matches": [match.to_dict() for match in self.matches],
            "total_score": self.total_score,
        }


class SearchIndex:
    """Search index for documentable items."""

    def __init__(self) -> None:
        """Initialize an empty search index."""
        self.items: list[DocumentableItem] = []
        self.item_by_name: dict[str, DocumentableItem] = {}
        self.word_to_items: dict[str, set[str]] = defaultdict(set)
        self.exact_phrases: dict[str, set[str]] = defaultdict(set)

    async def index_items(self, items: list[DocumentableItem]) -> None:
        """
        Index a list of documentable items.

        Args:
            items: List of documentable items to index
        """
        self.items = items

        # Build indices
        for item in items:
            schema = item.schema_info
            item_id = f"{schema.module}.{schema.name}"
            self.item_by_name[schema.name.lower()] = item

            # Index name, module, and description
            self._index_text(schema.name, item_id)
            self._index_text(schema.module, item_id)
            self._index_text(schema.description, item_id)

            # Add exact phrases from name and description
            self._add_exact_phrase(schema.name, item_id)
            self._add_exact_phrases_from_text(schema.description, item_id)

            # Index fields
            for field in schema.fields:
                self._index_text(field.name, item_id)
                self._index_text(field.description, item_id)
                self._add_exact_phrase(field.name, item_id)
                self._add_exact_phrases_from_text(field.description, item_id)

            # Index examples
            for example in schema.examples:
                self._index_text(example.title, item_id)
                self._index_text(example.description or "", item_id)
                self._add_exact_phrase(example.title, item_id)

    def _index_text(self, text: str, item_id: str) -> None:
        """Index words in text."""
        if not text:
            return

        # Extract clean words
        words = re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())

        # Add to word index
        for word in words:
            if len(word) > 2:  # Skip very short words
                self.word_to_items[word].add(item_id)

    def _add_exact_phrase(self, phrase: str, item_id: str) -> None:
        """Add an exact phrase to the index."""
        if phrase:
            self.exact_phrases[phrase.lower().strip()].add(item_id)

    def _add_exact_phrases_from_text(self, text: str, item_id: str) -> None:
        """Extract and add phrases from text."""
        if not text:
            return

        # Add sentences and phrases in quotes as exact matches
        sentences = re.split(r"[.!?]", text)
        for sentence in sentences:
            if len(sentence.strip()) > 10:
                self.exact_phrases[sentence.lower().strip()].add(item_id)

        # Extract phrases in quotes
        quoted_phrases = re.findall(r'"([^"]*)"', text)
        for phrase in quoted_phrases:
            if phrase:
                self.exact_phrases[phrase.lower().strip()].add(item_id)

    async def search(
        self,
        query: str,
        doc_types: list[DocumentationType] | None = None,
        modules: list[str] | None = None,
        max_results: int = 20,
        min_score: float = 0.1,
    ) -> list[SearchResult]:
        """
        Search for items matching the query.

        Args:
            query: The search query
            doc_types: Filter by document types
            modules: Filter by modules
            max_results: Maximum number of results to return
            min_score: Minimum score for results

        Returns:
            Sorted list of search results
        """
        query = query.strip()
        if not query:
            return []

        # Extract search terms
        terms = re.findall(r'(?:"[^"]+"|[^\s]+)', query)
        processed_terms = []
        exact_matches = []

        for term in terms:
            # Handle quoted phrases
            if term.startswith('"') and term.endswith('"'):
                exact_matches.append(term[1:-1].lower())
            else:
                processed_terms.append(term.lower())

        # Find candidate items
        candidate_items = set()

        # First, check for exact phrase matches
        for phrase in exact_matches:
            matching_items = self.exact_phrases.get(phrase, set())
            if not candidate_items:
                candidate_items = matching_items
            else:
                candidate_items &= matching_items

            # If no matches for a required term, exit early
            if not candidate_items:
                return []

        # Then check for word matches
        for term in processed_terms:
            matching_items = self.word_to_items.get(term, set())

            # If first term, initialize candidates
            if not candidate_items:
                candidate_items = matching_items
            else:
                # Intersect with previous matches (AND logic)
                candidate_items &= matching_items

            # If no matches for a required term, exit early
            if not candidate_items:
                return []

        # No candidates
        if not candidate_items:
            return []

        # Score and rank the results
        results: list[SearchResult] = []

        for item_id in candidate_items:
            # Get the item from the ID (module.name)
            item_parts = item_id.rsplit(".", 1)
            if len(item_parts) != 2:
                continue

            module, name = item_parts

            # Find the item
            found_item = None
            for item in self.items:
                if item.schema_info.module == module and item.schema_info.name == name:
                    found_item = item
                    break

            if not found_item:
                continue

            # Apply filters
            if doc_types and found_item.schema_info.type not in doc_types:
                continue

            if modules and not any(
                found_item.schema_info.module.startswith(m) for m in modules
            ):
                continue

            # Score the item
            result = await self._score_item(found_item, processed_terms, exact_matches)

            # Add to results if score is high enough
            if result.total_score >= min_score:
                results.append(result)

        # Sort results by score
        results.sort(key=lambda r: r.total_score, reverse=True)

        # Limit to max_results
        return results[:max_results]

    async def _score_item(
        self,
        item: DocumentableItem,
        terms: list[str],
        exact_matches: list[str],
    ) -> SearchResult:
        """Score an item based on search terms."""
        schema = item.schema_info
        result = SearchResult(item=item)

        # Score name match (highest weight)
        name_lower = schema.name.lower()
        for term in terms:
            if term in name_lower:
                score = 5.0 if term == name_lower else 3.0
                match = SearchMatch(
                    text=schema.name,
                    type=SearchResultType.TITLE,
                    score=score,
                    fragment=schema.name,
                )
                result.matches.append(match)
                result.total_score += score

        # Score description match
        desc = schema.description.lower()
        for term in terms:
            if term in desc:
                positions = [m.start() for m in re.finditer(re.escape(term), desc)]
                for pos in positions:
                    # Get surrounding context
                    start = max(0, pos - 40)
                    end = min(len(desc), pos + len(term) + 40)
                    fragment = f"...{desc[start:end]}..."

                    score = 2.0
                    match = SearchMatch(
                        text=term,
                        type=SearchResultType.DESCRIPTION,
                        score=score,
                        fragment=fragment,
                    )
                    result.matches.append(match)
                    result.total_score += score

        # Score exact phrase matches
        for phrase in exact_matches:
            # Check name
            if phrase in name_lower:
                score = 10.0  # Exact phrase in name is very relevant
                match = SearchMatch(
                    text=phrase,
                    type=SearchResultType.TITLE,
                    score=score,
                    fragment=schema.name,
                )
                result.matches.append(match)
                result.total_score += score

            # Check description
            if phrase in desc:
                positions = [m.start() for m in re.finditer(re.escape(phrase), desc)]
                for pos in positions:
                    # Get surrounding context
                    start = max(0, pos - 30)
                    end = min(len(desc), pos + len(phrase) + 30)
                    fragment = f"...{desc[start:end]}..."

                    score = 7.0  # Exact phrase in description is very relevant
                    match = SearchMatch(
                        text=phrase,
                        type=SearchResultType.DESCRIPTION,
                        score=score,
                        fragment=fragment,
                    )
                    result.matches.append(match)
                    result.total_score += score

        # Score field matches
        for field in schema.fields:
            # Check field name
            field_name_lower = field.name.lower()
            for term in terms:
                if term in field_name_lower:
                    score = 1.5
                    match = SearchMatch(
                        text=term,
                        type=SearchResultType.FIELD,
                        field_name=field.name,
                        score=score,
                        fragment=field.name,
                    )
                    result.matches.append(match)
                    result.total_score += score

            # Check field description
            field_desc = field.description.lower()
            for term in terms:
                if term in field_desc:
                    positions = [
                        m.start() for m in re.finditer(re.escape(term), field_desc)
                    ]
                    if positions:
                        # Get first occurrence context
                        pos = positions[0]
                        start = max(0, pos - 30)
                        end = min(len(field_desc), pos + len(term) + 30)
                        fragment = f"...{field_desc[start:end]}..."

                        score = 1.0
                        match = SearchMatch(
                            text=term,
                            type=SearchResultType.FIELD_DESCRIPTION,
                            field_name=field.name,
                            score=score,
                            fragment=fragment,
                        )
                        result.matches.append(match)
                        result.total_score += score

        # Score module match (lowest weight)
        module_lower = schema.module.lower()
        for term in terms:
            if term in module_lower:
                score = 0.5
                match = SearchMatch(
                    text=term,
                    type=SearchResultType.MODULE,
                    score=score,
                    fragment=schema.module,
                )
                result.matches.append(match)
                result.total_score += score

        return result


async def create_search_index(items: list[DocumentableItem]) -> SearchIndex:
    """
    Create a search index from a list of documentable items.

    Args:
        items: List of documentable items to index

    Returns:
        Search index for the items
    """
    index = SearchIndex()
    await index.index_items(items)
    return index


async def search_items(
    items: list[DocumentableItem],
    query: str,
    doc_types: list[DocumentationType] | None = None,
    modules: list[str] | None = None,
    max_results: int = 20,
    min_score: float = 0.1,
) -> list[dict[str, Any]]:
    """
    Search for items matching the query.

    Args:
        items: List of documentable items to search
        query: The search query
        doc_types: Filter by document types
        modules: Filter by modules
        max_results: Maximum number of results to return
        min_score: Minimum score for results

    Returns:
        List of search results as dictionaries
    """
    # Create index
    index = await create_search_index(items)

    # Perform search
    results = await index.search(query, doc_types, modules, max_results, min_score)

    # Convert to dictionaries with minimal information
    return [result.to_dict() for result in results]
