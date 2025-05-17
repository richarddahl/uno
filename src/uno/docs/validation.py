# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Advanced validation rules for documentation.

This module provides spell checking, grammar validation, style guide enforcement,
and link validation for ensuring high-quality documentation.
"""

from __future__ import annotations

import asyncio
import re
import string
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Protocol, cast
import urllib.parse

import httpx
from pydantic import BaseModel

from uno.docs.schema import DocumentableItem, SchemaInfo, FieldInfo, ExampleInfo


class ValidationSeverity(str, Enum):
    """Severity level for validation issues."""

    ERROR = "error"  # Must be fixed, fails validation
    WARNING = "warning"  # Should be fixed, but doesn't fail validation
    INFO = "info"  # Informational only


@dataclass
class ValidationIssue:
    """An issue found during documentation validation."""

    message: str
    severity: ValidationSeverity
    item_name: str
    field_name: str | None = None
    line: int | None = None
    column: int | None = None
    suggestion: str | None = None
    rule_id: str | None = None
    context: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert issue to dictionary."""
        return {
            "message": self.message,
            "severity": self.severity.value,
            "item_name": self.item_name,
            "field_name": self.field_name,
            "line": self.line,
            "column": self.column,
            "suggestion": self.suggestion,
            "rule_id": self.rule_id,
            "context": self.context,
        }


class ValidationRuleProtocol(Protocol):
    """Protocol for validation rules."""

    async def validate(self, item: DocumentableItem) -> list[ValidationIssue]:
        """
        Validate an item against this rule.
        
        Args:
            item: The item to validate
            
        Returns:
            List of validation issues found
        """
        ...


class ValidationRule(BaseModel):
    """Base class for validation rules."""

    name: str
    description: str
    severity: ValidationSeverity = ValidationSeverity.WARNING
    enabled: bool = True
    rule_id: str

    async def validate(self, item: DocumentableItem) -> list[ValidationIssue]:
        """
        Validate an item against this rule.
        
        Args:
            item: The item to validate
            
        Returns:
            List of validation issues found
        """
        return []


class SpellCheckRule(ValidationRule):
    """Rule for checking spelling in documentation."""

    rule_id: str = "spell-check"
    name: str = "Spelling Check"
    description: str = "Checks for spelling errors in documentation"
    custom_dictionary: list[str] = field(default_factory=list)
    ignore_words: list[str] = field(default_factory=list)
    language: str = "en"
    
    _dictionary: Any = None  # Will hold the SpellChecker instance
    
    async def validate(self, item: DocumentableItem) -> list[ValidationIssue]:
        """Check for spelling errors in item documentation."""
        try:
            # Import here to avoid hard dependency
            from spellchecker import SpellChecker
        except ImportError:
            return [ValidationIssue(
                message="pyspellchecker package is required for spell checking",
                severity=ValidationSeverity.INFO,
                item_name=item.schema_info.name,
                rule_id=self.rule_id
            )]
        
        # Initialize spell checker if needed
        if self._dictionary is None:
            self._dictionary = SpellChecker(language=self.language)
            
            # Add custom words to dictionary
            if self.custom_dictionary:
                self._dictionary.word_frequency.load_words(self.custom_dictionary)
                
        issues = []
        schema = item.schema_info
        
        # Check main description
        if schema.description:
            desc_issues = await self._check_text(
                schema.description, 
                schema.name, 
                "description"
            )
            issues.extend(desc_issues)
            
        # Check field descriptions
        for field in schema.fields:
            if field.description:
                field_issues = await self._check_text(
                    field.description,
                    schema.name,
                    f"field:{field.name}"
                )
                issues.extend(field_issues)
                
        # Check example descriptions
        for i, example in enumerate(schema.examples):
            if example.description:
                example_issues = await self._check_text(
                    example.description,
                    schema.name,
                    f"example:{i}"
                )
                issues.extend(example_issues)
                
        return issues
    
    async def _check_text(
        self, 
        text: str, 
        item_name: str, 
        field_name: str | None
    ) -> list[ValidationIssue]:
        """Check text for spelling errors."""
        # Skip if text is empty
        if not text or not text.strip():
            return []
            
        issues = []
        
        # Extract words from text
        words = re.findall(r'\b[a-zA-Z\']+\b', text.lower())
        
        # Check for misspelled words
        code_blocks = re.findall(r'```.*?```', text, re.DOTALL)
        
        # Remove code blocks to avoid checking them
        cleaned_text = text
        for block in code_blocks:
            cleaned_text = cleaned_text.replace(block, "")
            
        # Extract words from cleaned text
        words = re.findall(r'\b[a-zA-Z\']+\b', cleaned_text.lower())
        
        # Filter out words we should ignore
        words = [w for w in words if w not in self.ignore_words and len(w) > 1]
        
        # Check for misspelled words
        misspelled = cast(list[str], self._dictionary.unknown(words))
        
        # Create issues for misspelled words
        for word in misspelled:
            # Skip technical terms, acronyms, and standard code words
            if (word.isupper() or  # acronym
                '_' in word or # code variable
                word in self.ignore_words):
                continue
                
            candidates = self._dictionary.candidates(word)
            suggestion = next(iter(candidates), None) if candidates else None
            
            # Find position in text for better context
            match = re.search(r'\b' + re.escape(word) + r'\b', text, re.IGNORECASE)
            context = None
            line = None
            column = None
            
            if match:
                start, end = match.span()
                
                # Get line number and column
                lines = text[:start].split('\n')
                line = len(lines)
                column = len(lines[-1]) + 1
                
                # Extract context (show a few characters before and after)
                context_start = max(0, start - 20)
                context_end = min(len(text), end + 20)
                context = text[context_start:context_end]
                
                # Highlight the misspelled word in context
                if context:
                    word_in_context = text[start:end]
                    context = context.replace(
                        word_in_context, 
                        f"**{word_in_context}**"
                    )
            
            issues.append(ValidationIssue(
                message=f"Possible spelling error: '{word}'",
                severity=self.severity,
                item_name=item_name,
                field_name=field_name,
                line=line,
                column=column,
                suggestion=suggestion,
                rule_id=self.rule_id,
                context=context
            ))
            
        return issues


class GrammarCheckRule(ValidationRule):
    """Rule for checking grammar in documentation."""

    rule_id: str = "grammar-check"
    name: str = "Grammar Check"
    description: str = "Checks for grammar errors in documentation"
    language: str = "en-US"
    
    _tool: Any = None  # Will hold the LanguageTool instance
    
    async def validate(self, item: DocumentableItem) -> list[ValidationIssue]:
        """Check for grammar errors in item documentation."""
        try:
            # Import here to avoid hard dependency
            import language_tool_python
        except ImportError:
            return [ValidationIssue(
                message="language_tool_python package is required for grammar checking",
                severity=ValidationSeverity.INFO,
                item_name=item.schema_info.name,
                rule_id=self.rule_id
            )]
        
        # Initialize grammar checker if needed
        if self._tool is None:
            self._tool = language_tool_python.LanguageTool(self.language)
            
        issues = []
        schema = item.schema_info
        
        # Check main description
        if schema.description:
            desc_issues = await self._check_text(
                schema.description, 
                schema.name, 
                "description"
            )
            issues.extend(desc_issues)
            
        # Check field descriptions
        for field in schema.fields:
            if field.description:
                field_issues = await self._check_text(
                    field.description,
                    schema.name,
                    f"field:{field.name}"
                )
                issues.extend(field_issues)
                
        # Check example descriptions
        for i, example in enumerate(schema.examples):
            if example.description:
                example_issues = await self._check_text(
                    example.description,
                    schema.name,
                    f"example:{i}"
                )
                issues.extend(example_issues)
                
        return issues
    
    async def _check_text(
        self, 
        text: str, 
        item_name: str, 
        field_name: str | None
    ) -> list[ValidationIssue]:
        """Check text for grammar errors."""
        # Skip if text is empty
        if not text or not text.strip():
            return []
            
        issues = []
        
        # Skip code blocks
        code_blocks = re.findall(r'```.*?