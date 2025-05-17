"""
SQL documentation generation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, UTC
from typing import Any, TypeVar, TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession
from uno.errors import UnoError
from uno.persistance.sql.config import SQLConfig
from uno.persistance.sql.connection import ConnectionManager
from uno.logging.protocols import LoggerProtocol
from uno.logging.level import LogLevel

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path
    from sqlalchemy.ext.asyncio import AsyncSession
    from uno.persistance.sql.config import SQLConfig
    from uno.persistance.sql.connection import ConnectionManager

# Type variables for generic types
T = TypeVar("T")


class TableDocumentation(BaseModel):
    """Table documentation."""

    name: str
    db_schema: str
    description: str | None
    columns: list[dict[str, Any]]
    indexes: list[dict[str, Any]]
    foreign_keys: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime | None = None


class FunctionDocumentation(BaseModel):
    """Function documentation."""

    name: str
    db_schema: str
    description: str | None
    parameters: list[dict[str, Any]]
    return_type: str
    language: str
    created_at: datetime
    updated_at: datetime | None = None


class ViewDocumentation(BaseModel):
    """View documentation."""

    name: str
    db_schema: str
    description: str | None
    definition: str
    columns: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime | None = None


class TriggerDocumentation(BaseModel):
    """Trigger documentation."""

    name: str
    table: str
    db_schema: str
    description: str | None
    event: str
    timing: str
    function: str
    created_at: datetime
    updated_at: datetime | None = None


class SQLDocumentationGenerator:
    """Generates database documentation."""

    def __init__(
        self,
        config: SQLConfig,
        connection_manager: ConnectionManager,
        logger: LoggerProtocol,
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

    async def generate_schema_docs(self) -> Mapping[str, Any]:
        """Generate db_schema documentation.

        Returns:
            Dictionary containing db_schema documentation

        Raises:
            Exception: If db_schema documentation generation fails
        """
        if not self._config.DB_DOCS_INCLUDE_SCHEMAS:
            return {}

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
                LogLevel.INFO,
                "Generated db_schema documentation",
                name="uno.sql.documentation",
                schema_count=len(schemas),
            )
            return schemas

    async def generate_table_docs(self) -> Sequence[TableDocumentation]:
        """Generate table documentation.

        Returns:
            List of table documentation objects

        Raises:
            Exception: If table documentation generation fails
        """
        if not self._config.DB_DOCS_INCLUDE_TABLES:
            return []

        async with self._connection_manager.get_connection() as session:
            inspector = inspect(self._connection_manager.engine)
            tables: list[TableDocumentation] = []

            for db_schema in await self._get_schemas(session):
                for table_name in await self._get_tables(session, db_schema):
                    # Get table info
                    columns = (
                        inspector.get_columns(table_name, db_schema=db_schema) or []
                    )
                    indexes = (
                        inspector.get_indexes(table_name, db_schema=db_schema) or []
                    )
                    foreign_keys = (
                        inspector.get_foreign_keys(table_name, db_schema=db_schema)
                        or []
                    )

                    # Get table description
                    result = await session.execute(
                        text(
                            "SELECT description "
                            "FROM pg_description "
                            "JOIN pg_class ON pg_description.objoid = pg_class.oid "
                            "JOIN pg_namespace ON pg_class.relnamespace = pg_namespace.oid "
                            "WHERE pg_class.relname = :table "
                            "AND pg_namespace.nspname = :db_schema"
                        ),
                        {"table": table_name, "db_schema": db_schema},
                    )
                    description = result.scalar()

                    tables.append(
                        TableDocumentation(
                            name=table_name,
                            db_schema=db_schema,
                            description=description,
                            columns=columns,
                            indexes=indexes,
                            foreign_keys=foreign_keys,
                            created_at=datetime.now(tz=UTC),
                            updated_at=None,
                        )
                    )

            self._logger.structured_log(
                LogLevel.INFO,
                "Generated table documentation",
                name="uno.sql.documentation",
                table_count=len(tables),
            )
            return tables

    async def generate_function_docs(self) -> Sequence[FunctionDocumentation]:
        """Generate function documentation.

        Returns:
            List of function documentation objects

        Raises:
            Exception: If function documentation generation fails
        """
        if not self._config.DB_DOCS_INCLUDE_FUNCTIONS:
            return []

        async with self._connection_manager.get_connection() as session:
            functions: list[FunctionDocumentation] = []

            for db_schema in await self._get_schemas(session):
                for function_name in await self._get_functions(session, db_schema):
                    # Get function info
                    result = await session.execute(
                        text(
                            "SELECT proname, nspname, prosrc, prolang, prorettype, proargtypes, proargnames, proargmodes "
                            "FROM pg_proc "
                            "JOIN pg_namespace ON pg_proc.pronamespace = pg_namespace.oid "
                            "WHERE proname = :function AND nspname = :db_schema"
                        ),
                        {"function": function_name, "db_schema": db_schema},
                    )
                    row = result.fetchone()
                    if not row:
                        continue

                    # Get function description
                    desc_result = await session.execute(
                        text(
                            "SELECT description "
                            "FROM pg_description "
                            "JOIN pg_proc ON pg_description.objoid = pg_proc.oid "
                            "JOIN pg_namespace ON pg_proc.pronamespace = pg_namespace.oid "
                            "WHERE proname = :function AND nspname = :db_schema"
                        ),
                        {"function": function_name, "db_schema": db_schema},
                    )
                    description = desc_result.scalar()

                    # Parse argument types and names
                    arg_types = [] if row[5] is None else row[5].split()
                    arg_names = [] if row[6] is None else row[6].split()
                    arg_modes = [] if row[7] is None else row[7].split()

                    parameters = []
                    for i in range(len(arg_types)):
                        param = {
                            "name": arg_names[i] if i < len(arg_names) else f"arg{i}",
                            "type": arg_types[i],
                            "mode": arg_modes[i] if i < len(arg_modes) else "in",
                        }
                        parameters.append(param)

                    functions.append(
                        FunctionDocumentation(
                            name=row[0],
                            db_schema=row[1],
                            description=description,
                            parameters=parameters,
                            return_type=row[4],
                            language=row[3],
                            created_at=datetime.now(tz=UTC),
                            updated_at=None,
                        )
                    )

            self._logger.structured_log(
                LogLevel.INFO,
                "Generated function documentation",
                name="uno.sql.documentation",
                function_count=len(functions),
            )
            return functions

    async def generate_view_docs(self) -> Sequence[ViewDocumentation]:
        """Generate view documentation.

        Returns:
            List of view documentation objects

        Raises:
            Exception: If view documentation generation fails
        """
        if not self._config.DB_DOCS_INCLUDE_VIEWS:
            return []

        async with self._connection_manager.get_connection() as session:
            views: list[ViewDocumentation] = []

            for db_schema in await self._get_schemas(session):
                result = await session.execute(
                    text(
                        "SELECT viewname, definition "
                        "FROM pg_views "
                        "WHERE schemaname = :db_schema"
                    ),
                    {"db_schema": db_schema},
                )
                for row in result.fetchall():
                    # Get view description
                    desc_result = await session.execute(
                        text(
                            "SELECT description "
                            "FROM pg_description "
                            "JOIN pg_class ON pg_description.objoid = pg_class.oid "
                            "JOIN pg_namespace ON pg_class.relnamespace = pg_namespace.oid "
                            "WHERE pg_class.relname = :view "
                            "AND pg_namespace.nspname = :db_schema"
                        ),
                        {"view": row[0], "db_schema": db_schema},
                    )
                    description = desc_result.scalar()

                    # Get view columns
                    col_result = await session.execute(
                        text(
                            "SELECT column_name, data_type "
                            "FROM information_schema.columns "
                            "WHERE table_schema = :db_schema "
                            "AND table_name = :view"
                        ),
                        {"view": row[0], "db_schema": db_schema},
                    )
                    columns = [
                        {"name": col[0], "type": col[1]}
                        for col in col_result.fetchall()
                    ]

                    views.append(
                        ViewDocumentation(
                            name=row[0],
                            db_schema=db_schema,
                            description=description,
                            definition=row[1],
                            columns=columns,
                            created_at=datetime.now(tz=UTC),
                            updated_at=None,
                        )
                    )

            self._logger.structured_log(
                LogLevel.INFO,
                "Generated view documentation",
                name="uno.sql.documentation",
                view_count=len(views),
            )
            return views

    async def generate_trigger_docs(self) -> list[TriggerDocumentation]:
        """Generate trigger documentation.

        Returns:
            List of trigger documentation objects
        """
        try:
            if not self._config.DB_DOCS_INCLUDE_TRIGGERS:
                return []

            async with self._connection_manager.get_connection() as session:
                triggers = []

                for db_schema in await self._get_schemas(session):
                    result = await session.execute(
                        text(
                            "SELECT t.tgname, c.relname as table_name, "
                            "pg_get_triggerdef(t.oid) as definition, d.description "
                            "FROM pg_trigger t "
                            "JOIN pg_class c ON t.tgrelid = c.oid "
                            "JOIN pg_namespace n ON c.relnamespace = n.oid "
                            "LEFT JOIN pg_description d ON t.oid = d.objoid "
                            "WHERE n.nspname = :db_schema "
                            "AND NOT t.tgisinternal"
                        ),
                        {"db_schema": db_schema},
                    )

                    for row in result.fetchall():
                        # Parse trigger definition
                        event, timing, function = self._parse_trigger_def(row[2])

                        triggers.append(
                            TriggerDocumentation(
                                name=row[0],
                                table=row[1],
                                db_schema=db_schema,
                                description=row[3],
                                event=event,
                                timing=timing,
                                function=function,
                                created_at=datetime.now(tz=datetime.UTC),
                                updated_at=None,
                            )
                        )

                self._logger.structured_log(
                    LogLevel.INFO,
                    "Generated trigger documentation",
                    name="uno.sql.documentation",
                    trigger_count=len(triggers),
                )
                return triggers
        except Exception as e:
            self._logger.structured_log(
                LogLevel.ERROR,
                f"Failed to generate trigger documentation: {str(e)}",
                name="uno.sql.documentation",
                error=e,
            )
            raise UnoError(f"Failed to generate trigger documentation: {str(e)}")

    async def generate_markdown(self, output_dir: Path) -> None:
        """Generate markdown documentation.

        Args:
            output_dir: Output directory for documentation

        Raises:
            UnoError: If markdown generation fails
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
                isinstance(r)
                for r in [
                    schema_docs,
                    table_docs,
                    function_docs,
                    view_docs,
                    trigger_docs,
                ]
            ):
                raise UnoError("Failed to generate some documentation")

            # Write db_schema documentation
            with open(output_dir / "schemas.md", "w") as f:
                f.write("# Database Schemas\n\n")
                for db_schema, info in schema_docs.value.items():
                    f.write(f"## {db_schema}\n\n")
                    if info["description"]:
                        f.write(f"{info['description']}\n\n")

            # Write table documentation
            with open(output_dir / "tables.md", "w") as f:
                f.write("# Database Tables\n\n")
                for table in table_docs.value:
                    f.write(f"## {table.db_schema}.{table.name}\n\n")
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
                    f.write(f"## {func.db_schema}.{func.name}\n\n")
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
                    f.write(f"## {view.db_schema}.{view.name}\n\n")
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
                    f.write(f"## {trigger.db_schema}.{trigger.name}\n\n")
                    if trigger.description:
                        f.write(f"{trigger.description}\n\n")

                    f.write(f"### Table\n\n{trigger.table}\n\n")
                    f.write(f"### Event\n\n{trigger.event}\n\n")
                    f.write(f"### Timing\n\n{trigger.timing}\n\n")
                    f.write(f"### Function\n\n{trigger.function}\n\n")

            self._logger.structured_log(
                LogLevel.INFO,
                "Generated markdown documentation",
                name="uno.sql.documentation",
                output_dir=str(output_dir),
            )
            return None
        except Exception as e:
            self._logger.structured_log(
                LogLevel.ERROR,
                f"Failed to generate markdown documentation: {str(e)}",
                name="uno.sql.documentation",
                error=e,
            )
            raise UnoError(f"Failed to generate markdown documentation: {str(e)}")

    async def _get_schemas(self, session: AsyncSession) -> list[str]:
        """Get list of schemas.

        Args:
            session: Database session

        Returns:
            List of db_schema names
        """
        result = await session.execute(
            text(
                "SELECT schema_name "
                "FROM information_schema.schemata "
                "WHERE schema_name NOT IN ('information_schema', 'pg_catalog')"
            )
        )
        return [row[0] for row in result.fetchall()]

    async def _get_tables(self, session: AsyncSession, db_schema: str) -> list[str]:
        """Get list of tables in db_schema.

        Args:
            session: Database session
            db_schema: Schema name

        Returns:
            List of table names
        """
        result = await session.execute(
            text(
                "SELECT table_name "
                "FROM information_schema.tables "
                "WHERE table_schema = :db_schema "
                "AND table_type = 'BASE TABLE'"
            ),
            {"db_schema": db_schema},
        )
        return [row[0] for row in result.fetchall()]

    async def _get_view_columns(
        self, session: AsyncSession, db_schema: str, view: str
    ) -> list[dict[str, Any]]:
        """Get view columns.

        Args:
            session: Database session
            db_schema: Schema name
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
                "WHERE table_schema = :db_schema "
                "AND table_name = :view"
            ),
            {"db_schema": db_schema, "view": view},
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
