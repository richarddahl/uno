"""
Dimensional tagging implementation for the Uno metrics system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Hashable, Mapping, Optional
from collections.abc import Iterator


class TagKey:
    """A tag key that can be used to identify a tag value."""

    def __init__(self, name: str) -> None:
        """Initialize a tag key with a name."""
        self._name = name

    @property
    def name(self) -> str:
        """Get the name of the tag key."""
        return self._name

    def __hash__(self) -> int:
        """Get the hash of the tag key."""
        return hash(self._name)

    def __eq__(self, other: Any) -> bool:
        """Check if two tag keys are equal."""
        if not isinstance(other, TagKey):
            return False
        return self._name == other._name

    def __str__(self) -> str:
        """Get the string representation of the tag key."""
        return self._name


class TagValue:
    """A tag value that can be associated with a tag key."""

    def __init__(self, value: Any) -> None:
        """Initialize a tag value with a value."""
        self._value = value

    @property
    def value(self) -> Any:
        """Get the value of the tag."""
        return self._value

    def __str__(self) -> str:
        """Get the string representation of the tag value."""
        return str(self._value)


class TagSet:
    """A set of tags that can be associated with a metric."""

    def __init__(self, tags: Optional[Mapping[TagKey, TagValue]] = None) -> None:
        """Initialize a tag set with optional initial tags."""
        self._tags: dict[TagKey, TagValue] = dict(tags or {})

    def __getitem__(self, key: TagKey) -> TagValue:
        """Get a tag value by key."""
        return self._tags[key]

    def __setitem__(self, key: TagKey, value: TagValue) -> None:
        """Set a tag value for a key."""
        self._tags[key] = value

    def __delitem__(self, key: TagKey) -> None:
        """Remove a tag by key."""
        del self._tags[key]

    def __contains__(self, key: TagKey) -> bool:
        """Check if a tag key exists."""
        return key in self._tags

    def __iter__(self) -> Iterator[TagKey]:
        """Iterate over tag keys."""
        return iter(self._tags)

    def __len__(self) -> int:
        """Get the number of tags."""
        return len(self._tags)

    def copy(self) -> TagSet:
        """Create a copy of the tag set."""
        return TagSet(self._tags.copy())

    def merge(self, other: TagSet) -> TagSet:
        """Merge with another tag set."""
        result = self.copy()
        result._tags.update(other._tags)
        return result


class Taggable:
    """A mixin class that makes an object taggable."""

    def __init__(self) -> None:
        """Initialize a taggable object."""
        self._tags = TagSet()

    @property
    def tags(self) -> TagSet:
        """Get the tag set."""
        return self._tags

    def with_tags(self, tags: TagSet) -> Taggable:
        """Create a copy with additional tags."""
        copy = self.copy()
        copy._tags = self._tags.merge(tags)
        return copy

    def copy(self) -> Taggable:
        """Create a copy of the object."""
        raise NotImplementedError("Must be implemented by subclasses")


class TagContext:
    """A context manager for tag management."""

    def __init__(self, tags: TagSet) -> None:
        """Initialize a tag context with tags."""
        self._tags = tags

    def __enter__(self) -> TagContext:
        """Enter the tag context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the tag context."""
        pass

    def __aenter__(self) -> TagContext:
        """Enter the async tag context."""
        return self

    def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async tag context."""
        pass
