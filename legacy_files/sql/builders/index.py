# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""SQL index builder."""

from pydantic import BaseModel, field_validator


class SQLIndexBuilderConfig(BaseModel):
    db_schema: str
    table_name: str
    index_name: str
    columns: list[str]

    @field_validator("db_schema", "table_name", "index_name")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field must not be empty")
        return v

    @field_validator("columns")
    @classmethod
    def columns_not_empty(cls, v: list[str]) -> list[str]:
        if not v or not all(isinstance(col, str) and col.strip() for col in v):
            raise ValueError(
                "Columns list must not be empty and all items must be non-empty strings"
            )
        return v


class SQLIndexBuilder:
    """Builder for SQL indexes.

    This class provides a fluent interface for building SQL index
    statements with proper validation and formatting.

    Example:
        ```python
        index_sql = (
            SQLIndexBuilder()
            .with_schema("public")
            .with_table("users")
            .with_name("users_email_idx")
            .with_columns(["email"])
            .unique()
            .build()
        )
        ```
    """

    def __init__(self) -> None:
        """Initialize the SQL index builder."""
        self.db_schema: str | None = None
        self.table_name: str | None = None
        self.index_name: str | None = None
        self.columns: list[str] = []
        self.is_unique: bool = False
        self.index_method: str = "btree"
        self.nulls_distinct: bool = True
        self.include_columns: list[str] = []
        self.where_clause: str | None = None

    def with_schema(self, db_schema: str) -> "SQLIndexBuilder":
        """Set the db_schema for the index.

        Args:
            db_schema: Schema name

        Returns:
            Self for method chaining
        """
        self.db_schema = db_schema
        return self

    def with_table(self, table_name: str) -> "SQLIndexBuilder":
        """Set the table for the index.

        Args:
            table_name: Table name

        Returns:
            Self for method chaining
        """
        self.table_name = table_name
        return self

    def with_name(self, index_name: str) -> "SQLIndexBuilder":
        """Set the name of the index.

        Args:
            index_name: Index name

        Returns:
            Self for method chaining
        """
        self.index_name = index_name
        return self

    def with_columns(self, columns: list[str]) -> "SQLIndexBuilder":
        """Set the columns for the index.

        Args:
            columns: List of column names

        Returns:
            Self for method chaining
        """
        self.columns = columns
        return self

    def with_method(self, method: str) -> "SQLIndexBuilder":
        """Set the index method.

        Args:
            method: Index method (btree, hash, gist, etc.)

        Returns:
            Self for method chaining
        """
        self.index_method = method
        return self

    def unique(self, is_unique: bool = True) -> "SQLIndexBuilder":
        """Set the index to be unique.

        Args:
            is_unique: Whether the index is unique

        Returns:
            Self for method chaining
        """
        self.is_unique = is_unique
        return self

    def with_nulls_not_distinct(self) -> "SQLIndexBuilder":
        """Set NULLS NOT DISTINCT for the index.

        Returns:
            Self for method chaining
        """
        self.nulls_distinct = False
        return self

    def include(self, columns: list[str]) -> "SQLIndexBuilder":
        """Add columns to include in the index but not in the key.

        Args:
            columns: List of column names to include

        Returns:
            Self for method chaining
        """
        self.include_columns = columns
        return self

    def where(self, condition: str) -> "SQLIndexBuilder":
        """Add a WHERE clause to the index.

        Args:
            condition: WHERE condition

        Returns:
            Self for method chaining
        """
        self.where_clause = condition
        return self

    def build(self) -> str:
        """Build the SQL index statement, validating required fields.

        Returns:
            SQL index statement

        Raises:
            pydantic.ValidationError: If required parameters are missing or invalid
        """
        # Validate required fields with Pydantic
        config = SQLIndexBuilderConfig(
            db_schema=self.db_schema or "",
            table_name=self.table_name or "",
            index_name=self.index_name or "",
            columns=self.columns or [],
        )

        unique = "UNIQUE" if self.is_unique else ""
        include = (
            f"INCLUDE ({', '.join(self.include_columns)})"
            if self.include_columns
            else ""
        )
        where = f"WHERE {self.where_clause}" if self.where_clause else ""
        nulls = "NULLS DISTINCT" if self.nulls_distinct else "NULLS NOT DISTINCT"

        return f"""
            CREATE {unique} INDEX {config.index_name}
            ON {config.db_schema}.{config.table_name} USING {self.index_method}
            ({", ".join(config.columns)})
            {include}
            {where}
            {nulls};
        """
