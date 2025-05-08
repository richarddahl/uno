"""
SQL migration management.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import os
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
from sqlalchemy import text, MetaData, Table, Column, String, Integer, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from uno.errors.result import Result, Success, Failure
from uno.infrastructure.sql.config import SQLConfig
from uno.infrastructure.sql.connection import ConnectionManager
from uno.infrastructure.logging.logger import LoggerService


class Migration(BaseModel):
    """Database migration."""

    version: int
    name: str
    description: str
    sql_up: str
    sql_down: str
    created_at: datetime
    applied_at: Optional[datetime] = None


class MigrationManager:
    """Manages database migrations."""

    def __init__(
        self,
        config: SQLConfig,
        connection_manager: ConnectionManager,
        logger: LoggerService,
    ) -> None:
        """Initialize migration manager.

        Args:
            config: SQL configuration
            connection_manager: Connection manager
            logger: Logger service
        """
        self._config = config
        self._connection_manager = connection_manager
        self._logger = logger
        self._migrations: list[Migration] = []
        self._ensure_migrations_table()

    async def _ensure_migrations_table(self) -> None:
        """Ensure migrations table exists."""
        try:
            async with self._connection_manager.get_connection() as session:
                metadata = MetaData()
                Table(
                    self._config.DB_MIGRATIONS_TABLE,
                    metadata,
                    Column("version", Integer, primary_key=True),
                    Column("name", String, nullable=False),
                    Column("description", String),
                    Column(
                        "applied_at", DateTime, nullable=False, default=datetime.now
                    ),
                )
                await session.run_sync(metadata.create_all)
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to create migrations table: {str(e)}",
                name="uno.sql.migration",
                error=e,
            )
            raise

    async def create_migration(
        self, name: str, description: str, sql_up: str, sql_down: str
    ) -> Result[Migration, str]:
        """Create a new migration.

        Args:
            name: Migration name
            description: Migration description
            sql_up: SQL for applying migration
            sql_down: SQL for rolling back migration

        Returns:
            Result containing migration or error
        """
        try:
            # Get current version
            async with self._connection_manager.get_connection() as session:
                result = await session.execute(
                    text(f"SELECT MAX(version) FROM {self._config.DB_MIGRATIONS_TABLE}")
                )
                current_version = result.scalar() or 0

                # Create migration
                migration = Migration(
                    version=current_version + 1,
                    name=name,
                    description=description,
                    sql_up=sql_up,
                    sql_down=sql_down,
                    created_at=datetime.now(),
                )

                # Save migration file
                migrations_dir = Path(self._config.DB_MIGRATIONS_DIR)
                migrations_dir.mkdir(parents=True, exist_ok=True)

                migration_file = migrations_dir / f"{migration.version:04d}_{name}.sql"
                with open(migration_file, "w") as f:
                    f.write(f"-- Migration: {migration.name}\n")
                    f.write(f"-- Description: {migration.description}\n")
                    f.write(f"-- Version: {migration.version}\n\n")
                    f.write("-- Up\n")
                    f.write(sql_up)
                    f.write("\n\n-- Down\n")
                    f.write(sql_down)

                self._migrations.append(migration)

                self._logger.structured_log(
                    "INFO",
                    f"Created migration {migration.version}: {migration.name}",
                    name="uno.sql.migration",
                    migration=migration.dict(),
                )
                return Success(migration)
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to create migration: {str(e)}",
                name="uno.sql.migration",
                error=e,
            )
            return Failure(f"Failed to create migration: {str(e)}")

    async def apply_migrations(
        self, target_version: Optional[int] = None
    ) -> Result[None, str]:
        """Apply pending migrations.

        Args:
            target_version: Optional target version to migrate to

        Returns:
            Result indicating success or failure
        """
        try:
            async with self._connection_manager.get_connection() as session:
                # Get current version
                result = await session.execute(
                    text(f"SELECT MAX(version) FROM {self._config.DB_MIGRATIONS_TABLE}")
                )
                current_version = result.scalar() or 0

                # Get pending migrations
                pending = [
                    m
                    for m in self._migrations
                    if m.version > current_version
                    and (target_version is None or m.version <= target_version)
                ]
                pending.sort(key=lambda m: m.version)

                for migration in pending:
                    try:
                        # Apply migration
                        await session.execute(text(migration.sql_up))

                        # Record migration
                        await session.execute(
                            text(
                                f"INSERT INTO {self._config.DB_MIGRATIONS_TABLE} "
                                f"(version, name, description, applied_at) "
                                f"VALUES (:version, :name, :description, :applied_at)"
                            ),
                            {
                                "version": migration.version,
                                "name": migration.name,
                                "description": migration.description,
                                "applied_at": datetime.now(),
                            },
                        )

                        migration.applied_at = datetime.now()

                        self._logger.structured_log(
                            "INFO",
                            f"Applied migration {migration.version}: {migration.name}",
                            name="uno.sql.migration",
                            migration=migration.dict(),
                        )
                    except Exception as e:
                        self._logger.structured_log(
                            "ERROR",
                            f"Failed to apply migration {migration.version}: {str(e)}",
                            name="uno.sql.migration",
                            error=e,
                        )
                        await session.rollback()
                        return Failure(
                            f"Failed to apply migration {migration.version}: {str(e)}"
                        )

                await session.commit()
                return Success(None)
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to apply migrations: {str(e)}",
                name="uno.sql.migration",
                error=e,
            )
            return Failure(f"Failed to apply migrations: {str(e)}")

    async def rollback_migration(self, version: int) -> Result[None, str]:
        """Rollback a specific migration.

        Args:
            version: Version to rollback

        Returns:
            Result indicating success or failure
        """
        try:
            async with self._connection_manager.get_connection() as session:
                # Get migration
                migration = next(
                    (m for m in self._migrations if m.version == version), None
                )
                if not migration:
                    return Failure(f"Migration version {version} not found")

                try:
                    # Rollback migration
                    await session.execute(text(migration.sql_down))

                    # Remove migration record
                    await session.execute(
                        text(
                            f"DELETE FROM {self._config.DB_MIGRATIONS_TABLE} WHERE version = :version"
                        ),
                        {"version": version},
                    )

                    migration.applied_at = None

                    self._logger.structured_log(
                        "INFO",
                        f"Rolled back migration {migration.version}: {migration.name}",
                        name="uno.sql.migration",
                        migration=migration.dict(),
                    )
                    await session.commit()
                    return Success(None)
                except Exception as e:
                    self._logger.structured_log(
                        "ERROR",
                        f"Failed to rollback migration {version}: {str(e)}",
                        name="uno.sql.migration",
                        error=e,
                    )
                    await session.rollback()
                    return Failure(f"Failed to rollback migration: {str(e)}")
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to rollback migration: {str(e)}",
                name="uno.sql.migration",
                error=e,
            )
            return Failure(f"Failed to rollback migration: {str(e)}")

    async def get_migration_status(self) -> Result[list[Migration], str]:
        """Get migration status.

        Returns:
            Result containing list of migrations with status
        """
        try:
            async with self._connection_manager.get_connection() as session:
                result = await session.execute(
                    text(
                        f"SELECT version, applied_at FROM {self._config.DB_MIGRATIONS_TABLE}"
                    )
                )
                applied = {row[0]: row[1] for row in result.fetchall()}

                for migration in self._migrations:
                    migration.applied_at = applied.get(migration.version)

                return Success(self._migrations)
        except Exception as e:
            self._logger.structured_log(
                "ERROR",
                f"Failed to get migration status: {str(e)}",
                name="uno.sql.migration",
                error=e,
            )
            return Failure(f"Failed to get migration status: {str(e)}")

    @property
    def migrations(self) -> list[Migration]:
        """Get all migrations.

        Returns:
            List of all migrations
        """
        return self._migrations
