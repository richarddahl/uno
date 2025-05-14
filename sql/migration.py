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
from uno.persistence.sql.connection import ConnectionManager
from uno.logging.protocols import LoggerProtocol


class Migration(BaseModel):
    """Database migration."""

    version: int
    name: str
    description: str
    sql_up: str
    sql_down: str
    created_at: datetime
    applied_at: int | None = None


class MigrationManager:
    """Manages database migrations."""

    def __init__(
        self,
        db_migrations_table: str,
        db_migrations_dir: str,
        connection_manager: ConnectionManager,
        logger: LoggerProtocol,
    ) -> None:
        """
        Initialize migration manager.

        Args:
            db_migrations_table: Name of the migrations table
            db_migrations_dir: Directory for migration files
            connection_manager: Connection manager
            logger: Logger service
        """
        self._db_migrations_table = db_migrations_table
        self._db_migrations_dir = db_migrations_dir
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
                    self._db_migrations_table,
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
                LogLevel.ERROR,
                f"Failed to create migrations table: {str(e)}",
                name="uno.sql.migration",
                error=e,
            )
            raise

    async def create_migration(
        self, name: str, description: str, sql_up: str, sql_down: str
    ) -> Migration:
        """
        Create a new migration.

        Args:
            name: Migration name
            description: Migration description
            sql_up: SQL for applying migration
            sql_down: SQL for rolling back migration

        Returns:
            The created migration instance.

        Raises:
            Exception: If migration creation fails.
        """
        try:
            async with self._connection_manager.get_connection() as session:
                result = await session.execute(
                    text(f"SELECT MAX(version) FROM {self._db_migrations_table}")
                )
                current_version = result.scalar() or 0

                migration = Migration(
                    version=current_version + 1,
                    name=name,
                    description=description,
                    sql_up=sql_up,
                    sql_down=sql_down,
                    created_at=datetime.now(),
                )

                migrations_dir = Path(self._db_migrations_dir)
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
                    LogLevel.INFO,
                    f"Created migration {migration.version}: {migration.name}",
                    name="uno.sql.migration",
                    migration=migration.dict(),
                )
                return migration
        except Exception as e:
            self._logger.structured_log(
                LogLevel.ERROR,
                f"Failed to create migration: {str(e)}",
                name="uno.sql.migration",
                error=e,
            )
            raise Exception(f"Failed to create migration: {str(e)}")

    async def apply_migrations(self, target_version: int | None = None) -> None:
        """
        Apply pending migrations.

        Args:
            target_version: Optional target version to migrate to

        Raises:
            Exception: If applying migrations fails.
        """
        try:
            async with self._connection_manager.get_connection() as session:
                result = await session.execute(
                    text(f"SELECT MAX(version) FROM {self._db_migrations_table}")
                )
                current_version = result.scalar() or 0

                pending = [
                    m
                    for m in self._migrations
                    if m.version > current_version
                    and (target_version is None or m.version <= target_version)
                ]
                pending.sort(key=lambda m: m.version)

                for migration in pending:
                    try:
                        await session.execute(text(migration.sql_up))

                        await session.execute(
                            text(
                                f"INSERT INTO {self._db_migrations_table} "
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
                            LogLevel.INFO,
                            f"Applied migration {migration.version}: {migration.name}",
                            name="uno.sql.migration",
                            migration=migration.dict(),
                        )
                    except Exception as e:
                        self._logger.structured_log(
                            LogLevel.ERROR,
                            f"Failed to apply migration {migration.version}: {str(e)}",
                            name="uno.sql.migration",
                            error=e,
                        )
                        await session.rollback()
                        raise Exception(
                            f"Failed to apply migration {migration.version}: {str(e)}"
                        )

                await session.commit()
        except Exception as e:
            self._logger.structured_log(
                LogLevel.ERROR,
                f"Failed to apply migrations: {str(e)}",
                name="uno.sql.migration",
                error=e,
            )
            raise Exception(f"Failed to apply migrations: {str(e)}")

    async def rollback_migration(self, version: int) -> None:
        """
        Rollback a specific migration.

        Args:
            version: Version to rollback

        Raises:
            Exception: If rollback fails.
        """
        try:
            async with self._connection_manager.get_connection() as session:
                migration = next(
                    (m for m in self._migrations if m.version == version), None
                )
                if not migration:
                    raise Exception(f"Migration version {version} not found")

                try:
                    await session.execute(text(migration.sql_down))

                    await session.execute(
                        text(
                            f"DELETE FROM {self._db_migrations_table} WHERE version = :version"
                        ),
                        {"version": version},
                    )

                    migration.applied_at = None

                    self._logger.structured_log(
                        LogLevel.INFO,
                        f"Rolled back migration {migration.version}: {migration.name}",
                        name="uno.sql.migration",
                        migration=migration.dict(),
                    )
                    await session.commit()
                except Exception as e:
                    self._logger.structured_log(
                        LogLevel.ERROR,
                        f"Failed to rollback migration {version}: {str(e)}",
                        name="uno.sql.migration",
                        error=e,
                    )
                    await session.rollback()
                    raise Exception(f"Failed to rollback migration: {str(e)}")
        except Exception as e:
            self._logger.structured_log(
                LogLevel.ERROR,
                f"Failed to rollback migration: {str(e)}",
                name="uno.sql.migration",
                error=e,
            )
            raise Exception(f"Failed to rollback migration: {str(e)}")

    async def get_migration_status(self) -> list[Migration]:
        """
        Get migration status.

        Returns:
            List of migrations with status.

        Raises:
            Exception: If fetching migration status fails.
        """
        try:
            async with self._connection_manager.get_connection() as session:
                result = await session.execute(
                    text(f"SELECT version, applied_at FROM {self._db_migrations_table}")
                )
                applied = {row[0]: row[1] for row in result.fetchall()}

                for migration in self._migrations:
                    migration.applied_at = applied.get(migration.version)

                return self._migrations
        except Exception as e:
            self._logger.structured_log(
                LogLevel.ERROR,
                f"Failed to get migration status: {str(e)}",
                name="uno.sql.migration",
                error=e,
            )
            raise Exception(f"Failed to get migration status: {str(e)}")

    @property
    def migrations(self) -> list[Migration]:
        """Get all migrations.

        Returns:
            List of all migrations
        """
        return self._migrations
