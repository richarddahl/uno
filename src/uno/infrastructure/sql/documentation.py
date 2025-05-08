"""
SQL documentation generation.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
from sqlalchemy import text, MetaData, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from uno.errors.result import Result, Success, Failure
from uno.infrastructure.sql.config import SQLConfig
from uno.infrastructure.sql.connection import ConnectionManager
from uno.infrastructure.logging.logger import LoggerService


class TableDocumentation(BaseModel):
    """Table documentation."""

    name: str
    schema: str
    description: Optional[str]
    columns: list[dict[str, Any]]
    indexes: list[dict[str, Any]]
    foreign_keys: list[dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]


class FunctionDocumentation(BaseModel):
    """Function documentation."""

    name: str
    schema: str
    description: Optional[str]
    parameters: list[dict[str, Any]]
    return_type: str
    language: str
    created_at: datetime
    updated_at: Optional[datetime]


class ViewDocumentation(BaseModel):
    """View documentation."""

    name: str
    schema: str
    description: Optional[str]
    definition: str
    columns: list[dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]


class TriggerDocumentation(BaseModel):
    """Trigger documentation."""

    name: str
    table: str
    schema: str
    description: Optional[str]
    event: str
    timing: str
    function: str
    created_at: datetime
    updated_at: Optional[datetime]


class SQLDocumentationGenerator:
    """Generates database documentation."""

    def __init__(
        self,
        config: SQLConfig,
        connection_manager: ConnectionManager,
        logger: LoggerService,
    ) -> None:
        """Initialize documentation generator.

        Args:
            config: SQL configuration
            connection_manager: Connection manager
            logger: Logger service
        """
        self._config = config
        self._connection_manager = connection_manager
        self._logger = logger

    async def generate_schema_docs(self) -> Result[dict[str, Any], str]:
        """Generate schema documentation.

        Returns:
            Result containing schema documentation or error
        """
        try:
            if not self._config.DB_DOCS_INCLUDE_SCHEMAS:
                return Success({})

            async with self._connection_manager.get_connection() as session:
                result = await session.execute(
                    text(
                        "SELECT schema_name, description "
                        "FROM information_schema.schemata "
                        "WHERE schema_name NOT IN ('information_schema', 'pg_catalog')"
                    )
                )
                schemas = {row[0]: {"description": row[1]} for row in result.fetchall()}

                self._logger.structured_log(
                    "INFO",
                    "Generated schema documentation",
                    name="uno.sql.documentation",
                    schema_count=len(schemas),
                )
                return Success(schemas)
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to generate schema documentation: {str(e)}",
                name="uno.sql.documentation",
                error=e,
            )
            return Failure(f"Failed to generate schema documentation: {str(e)}")

    async def generate_table_docs(self) -> Result[list[TableDocumentation], str]:
        """Generate table documentation.

        Returns:
            Result containing table documentation or error
        """
        try:
            if not self._config.DB_DOCS_INCLUDE_TABLES:
                return Success([])

            async with self._connection_manager.get_connection() as session:
                inspector = inspect(self._connection_manager.engine)
                tables = []

                for schema in await self._get_schemas(session):
                    for table_name in await self._get_tables(session, schema):
                        # Get table info
                        columns = inspector.get_columns(table_name, schema=schema)
                        indexes = inspector.get_indexes(table_name, schema=schema)
                        foreign_keys = inspector.get_foreign_keys(
                            table_name, schema=schema
                        )

                        # Get table description
                        result = await session.execute(
                            text(
                                "SELECT description "
                                "FROM pg_description "
                                "JOIN pg_class ON pg_description.objoid = pg_class.oid "
                                "JOIN pg_namespace ON pg_class.relnamespace = pg_namespace.oid "
                                "WHERE pg_class.relname = :table "
                                "AND pg_namespace.nspname = :schema"
                            ),
                            {"table": table_name, "schema": schema},
                        )
                        description = result.scalar()

                        tables.append(
                            TableDocumentation(
                                name=table_name,
                                schema=schema,
                                description=description,
                                columns=columns,
                                indexes=indexes,
                                foreign_keys=foreign_keys,
                                created_at=datetime.now(),
                                updated_at=None,
                            )
                        )

                self._logger.structured_log(
                    "INFO",
                    "Generated table documentation",
                    name="uno.sql.documentation",
                    table_count=len(tables),
                )
                return Success(tables)
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to generate table documentation: {str(e)}",
                name="uno.sql.documentation",
                error=e,
            )
            return Failure(f"Failed to generate table documentation: {str(e)}")

    async def generate_function_docs(self) -> Result[list[FunctionDocumentation], str]:
        """Generate function documentation.

        Returns:
            Result containing function documentation or error
        """
        try:
            if not self._config.DB_DOCS_INCLUDE_FUNCTIONS:
                return Success([])

            async with self._connection_manager.get_connection() as session:
                functions = []

                for schema in await self._get_schemas(session):
                    result = await session.execute(
                        text(
                            "SELECT p.proname, pg_get_function_arguments(p.oid) as args, "
                            "pg_get_function_result(p.oid) as result_type, "
                            "p.prolang::regproc as language, d.description "
                            "FROM pg_proc p "
                            "JOIN pg_namespace n ON p.pronamespace = n.oid "
                            "LEFT JOIN pg_description d ON p.oid = d.objoid "
                            "WHERE n.nspname = :schema"
                        ),
                        {"schema": schema},
                    )

                    for row in result.fetchall():
                        functions.append(
                            FunctionDocumentation(
                                name=row[0],
                                schema=schema,
                                description=row[4],
                                parameters=self._parse_function_args(row[1]),
                                return_type=row[2],
                                language=row[3],
                                created_at=datetime.now(),
                                updated_at=None,
                            )
                        )

                self._logger.structured_log(
                    "INFO",
                    "Generated function documentation",
                    name="uno.sql.documentation",
                    function_count=len(functions),
                )
                return Success(functions)
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to generate function documentation: {str(e)}",
                name="uno.sql.documentation",
                error=e,
            )
            return Failure(f"Failed to generate function documentation: {str(e)}")

    async def generate_view_docs(self) -> Result[list[ViewDocumentation], str]:
        """Generate view documentation.

        Returns:
            Result containing view documentation or error
        """
        try:
            if not self._config.DB_DOCS_INCLUDE_VIEWS:
                return Success([])

            async with self._connection_manager.get_connection() as session:
                views = []

                for schema in await self._get_schemas(session):
                    result = await session.execute(
                        text(
                            "SELECT c.relname, pg_get_viewdef(c.oid) as definition, d.description "
                            "FROM pg_class c "
                            "JOIN pg_namespace n ON c.relnamespace = n.oid "
                            "LEFT JOIN pg_description d ON c.oid = d.objoid "
                            "WHERE n.nspname = :schema "
                            "AND c.relkind = 'v'"
                        ),
                        {"schema": schema},
                    )

                    for row in result.fetchall():
                        # Get view columns
                        columns = await self._get_view_columns(session, schema, row[0])

                        views.append(
                            ViewDocumentation(
                                name=row[0],
                                schema=schema,
                                description=row[2],
                                definition=row[1],
                                columns=columns,
                                created_at=datetime.now(),
                                updated_at=None,
                            )
                        )

                self._logger.structured_log(
                    "INFO",
                    "Generated view documentation",
                    name="uno.sql.documentation",
                    view_count=len(views),
                )
                return Success(views)
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to generate view documentation: {str(e)}",
                name="uno.sql.documentation",
                error=e,
            )
            return Failure(f"Failed to generate view documentation: {str(e)}")

    async def generate_trigger_docs(self) -> Result[list[TriggerDocumentation], str]:
        """Generate trigger documentation.

        Returns:
            Result containing trigger documentation or error
        """
        try:
            if not self._config.DB_DOCS_INCLUDE_TRIGGERS:
                return Success([])

            async with self._connection_manager.get_connection() as session:
                triggers = []

                for schema in await self._get_schemas(session):
                    result = await session.execute(
                        text(
                            "SELECT t.tgname, c.relname as table_name, "
                            "pg_get_triggerdef(t.oid) as definition, d.description "
                            "FROM pg_trigger t "
                            "JOIN pg_class c ON t.tgrelid = c.oid "
                            "JOIN pg_namespace n ON c.relnamespace = n.oid "
                            "LEFT JOIN pg_description d ON t.oid = d.objoid "
                            "WHERE n.nspname = :schema "
                            "AND NOT t.tgisinternal"
                        ),
                        {"schema": schema},
                    )

                    for row in result.fetchall():
                        # Parse trigger definition
                        event, timing, function = self._parse_trigger_def(row[2])

                        triggers.append(
                            TriggerDocumentation(
                                name=row[0],
                                table=row[1],
                                schema=schema,
                                description=row[3],
                                event=event,
                                timing=timing,
                                function=function,
                                created_at=datetime.now(),
                                updated_at=None,
                            )
                        )

                self._logger.structured_log(
                    "INFO",
                    "Generated trigger documentation",
                    name="uno.sql.documentation",
                    trigger_count=len(triggers),
                )
                return Success(triggers)
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to generate trigger documentation: {str(e)}",
                name="uno.sql.documentation",
                error=e,
            )
            return Failure(f"Failed to generate trigger documentation: {str(e)}")

    async def generate_markdown(self, output_dir: Path) -> Result[None, str]:
        """Generate markdown documentation.

        Args:
            output_dir: Output directory for documentation

        Returns:
            Result indicating success or failure
        """
        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate all documentation
            schema_docs = await self.generate_schema_docs()
            table_docs = await self.generate_table_docs()
            function_docs = await self.generate_function_docs()
            view_docs = await self.generate_view_docs()
            trigger_docs = await self.generate_trigger_docs()

            if not all(
                isinstance(r, Success)
                for r in [
                    schema_docs,
                    table_docs,
                    function_docs,
                    view_docs,
                    trigger_docs,
                ]
            ):
                return Failure("Failed to generate some documentation")

            # Write schema documentation
            with open(output_dir / "schemas.md", "w") as f:
                f.write("# Database Schemas\n\n")
                for schema, info in schema_docs.value.items():
                    f.write(f"## {schema}\n\n")
                    if info["description"]:
                        f.write(f"{info['description']}\n\n")

            # Write table documentation
            with open(output_dir / "tables.md", "w") as f:
                f.write("# Database Tables\n\n")
                for table in table_docs.value:
                    f.write(f"## {table.schema}.{table.name}\n\n")
                    if table.description:
                        f.write(f"{table.description}\n\n")

                    f.write("### Columns\n\n")
                    f.write("| Name | Type | Nullable | Default | Description |\n")
                    f.write("|------|------|----------|----------|-------------|\n")
                    for col in table.columns:
                        f.write(
                            f"| {col['name']} | {col['type']} | "
                            f"{'Yes' if col.get('nullable', True) else 'No'} | "
                            f"{col.get('default', '')} | {col.get('description', '')} |\n"
                        )

                    if table.indexes:
                        f.write("\n### Indexes\n\n")
                        for idx in table.indexes:
                            f.write(
                                f"- {idx['name']}: {', '.join(idx['column_names'])}\n"
                            )

                    if table.foreign_keys:
                        f.write("\n### Foreign Keys\n\n")
                        for fk in table.foreign_keys:
                            f.write(
                                f"- {', '.join(fk['constrained_columns'])} -> "
                                f"{fk['referred_schema']}.{fk['referred_table']}"
                                f"({', '.join(fk['referred_columns'])})\n"
                            )

            # Write function documentation
            with open(output_dir / "functions.md", "w") as f:
                f.write("# Database Functions\n\n")
                for func in function_docs.value:
                    f.write(f"## {func.schema}.{func.name}\n\n")
                    if func.description:
                        f.write(f"{func.description}\n\n")

                    f.write("### Parameters\n\n")
                    for param in func.parameters:
                        f.write(f"- {param['name']}: {param['type']}\n")

                    f.write(f"\n### Returns\n\n{func.return_type}\n\n")
                    f.write(f"### Language\n\n{func.language}\n\n")

            # Write view documentation
            with open(output_dir / "views.md", "w") as f:
                f.write("# Database Views\n\n")
                for view in view_docs.value:
                    f.write(f"## {view.schema}.{view.name}\n\n")
                    if view.description:
                        f.write(f"{view.description}\n\n")

                    f.write("### Columns\n\n")
                    f.write("| Name | Type | Description |\n")
                    f.write("|------|------|-------------|\n")
                    for col in view.columns:
                        f.write(
                            f"| {col['name']} | {col['type']} | "
                            f"{col.get('description', '')} |\n"
                        )

                    f.write("\n### Definition\n\n```sql\n")
                    f.write(view.definition)
                    f.write("\n```\n\n")

            # Write trigger documentation
            with open(output_dir / "triggers.md", "w") as f:
                f.write("# Database Triggers\n\n")
                for trigger in trigger_docs.value:
                    f.write(f"## {trigger.schema}.{trigger.name}\n\n")
                    if trigger.description:
                        f.write(f"{trigger.description}\n\n")

                    f.write(f"### Table\n\n{trigger.table}\n\n")
                    f.write(f"### Event\n\n{trigger.event}\n\n")
                    f.write(f"### Timing\n\n{trigger.timing}\n\n")
                    f.write(f"### Function\n\n{trigger.function}\n\n")

            self._logger.structured_log(
                "INFO",
                "Generated markdown documentation",
                name="uno.sql.documentation",
                output_dir=str(output_dir),
            )
            return Success(None)
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to generate markdown documentation: {str(e)}",
                name="uno.sql.documentation",
                error=e,
            )
            return Failure(f"Failed to generate markdown documentation: {str(e)}")

    async def _get_schemas(self, session: AsyncSession) -> list[str]:
        """Get list of schemas.

        Args:
            session: Database session

        Returns:
            List of schema names
        """
        result = await session.execute(
            text(
                "SELECT schema_name "
                "FROM information_schema.schemata "
                "WHERE schema_name NOT IN ('information_schema', 'pg_catalog')"
            )
        )
        return [row[0] for row in result.fetchall()]

    async def _get_tables(self, session: AsyncSession, schema: str) -> list[str]:
        """Get list of tables in schema.

        Args:
            session: Database session
            schema: Schema name

        Returns:
            List of table names
        """
        result = await session.execute(
            text(
                "SELECT table_name "
                "FROM information_schema.tables "
                "WHERE table_schema = :schema "
                "AND table_type = 'BASE TABLE'"
            ),
            {"schema": schema},
        )
        return [row[0] for row in result.fetchall()]

    async def _get_view_columns(
        self, session: AsyncSession, schema: str, view: str
    ) -> list[dict[str, Any]]:
        """Get view columns.

        Args:
            session: Database session
            schema: Schema name
            view: View name

        Returns:
            List of column information
        """
        result = await session.execute(
            text(
                "SELECT column_name, data_type, description "
                "FROM information_schema.columns c "
                "LEFT JOIN pg_description d ON d.objoid = c.table_name::regclass "
                "AND d.objsubid = c.ordinal_position "
                "WHERE table_schema = :schema "
                "AND table_name = :view"
            ),
            {"schema": schema, "view": view},
        )
        return [
            {"name": row[0], "type": row[1], "description": row[2]}
            for row in result.fetchall()
        ]

    def _parse_function_args(self, args: str) -> list[dict[str, str]]:
        """Parse function arguments.

        Args:
            args: Function arguments string

        Returns:
            List of argument information
        """
        params = []
        for arg in args.split(", "):
            if " " in arg:
                name, type_ = arg.split(" ", 1)
                params.append({"name": name, "type": type_})
            else:
                params.append({"name": arg, "type": "unknown"})
        return params

    def _parse_trigger_def(self, definition: str) -> tuple[str, str, str]:
        """Parse trigger definition.

        Args:
            definition: Trigger definition string

        Returns:
            Tuple of (event, timing, function)
        """
        # Example: CREATE TRIGGER name BEFORE INSERT ON table FOR EACH ROW EXECUTE FUNCTION func()
        parts = definition.split()
        event = parts[parts.index("ON") + 2]
        timing = parts[
            parts.index("BEFORE") if "BEFORE" in parts else parts.index("AFTER")
        ]
        function = parts[-1].strip("()")
        return event, timing, function
