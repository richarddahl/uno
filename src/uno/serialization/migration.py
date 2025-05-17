"""Schema migration utilities for serialized data."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type, TypeVar, cast

from pydantic import BaseModel, ValidationError

from uno.errors import MigrationError
from uno.logging import LoggerProtocol, get_logger
from uno.metrics import measure_time

T = TypeVar('T', bound=BaseModel)


@dataclass(frozen=True)
class MigrationResult:
    """Result of a migration operation."""
    
    success: bool
    migrated_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class Migration(ABC):
    """Base class for schema migrations."""
    
    def __init__(self, logger: Optional[LoggerProtocol] = None) -> None:
        self._logger = logger or get_logger("uno.serialization.migration")
    
    @property
    @abstractmethod
    def from_version(self) -> str:
        """The version this migration migrates from."""
        ...
    
    @property
    @abstractmethod
    def to_version(self) -> str:
        """The version this migration migrates to."""
        ...
    
    @abstractmethod
    @measure_time(namespace="migration")
    async def migrate(
        self,
        data: Dict[str, Any],
        model_type: Type[T],
    ) -> MigrationResult:
        """Migrate data from one version to another.
        
        Args:
            data: The data to migrate
            model_type: The target model type
            
        Returns:
            MigrationResult with the migration status and migrated data
        """
        ...


class SchemaMigrator:
    """Handles schema migrations between different versions."""
    
    def __init__(
        self,
        migrations: Optional[List[Migration]] = None,
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """Initialize the schema migrator.
        
        Args:
            migrations: List of available migrations
            logger: Logger instance (optional)
        """
        self._logger = logger or get_logger("uno.serialization.schema_migrator")
        self._migrations: Dict[str, Migration] = {}
        
        if migrations:
            for migration in migrations:
                self.add_migration(migration)
    
    def add_migration(self, migration: Migration) -> None:
        """Add a migration to the migrator.
        
        Args:
            migration: The migration to add
            
        Raises:
            ValueError: If a migration with the same from_version already exists
        """
        if migration.from_version in self._migrations:
            raise ValueError(f"Migration from version {migration.from_version} already exists")
        self._migrations[migration.from_version] = migration
    
    @measure_time(namespace="migration")
    async def migrate(
        self,
        data: Dict[str, Any],
        model_type: Type[T],
        current_version: str,
        target_version: str,
    ) -> Dict[str, Any]:
        """Migrate data from one version to another.
        
        Args:
            data: The data to migrate
            model_type: The target model type
            current_version: Current version of the data
            target_version: Target version to migrate to
            
        Returns:
            The migrated data
            
        Raises:
            MigrationError: If migration fails or no migration path is found
        """
        if current_version == target_version:
            return data
            
        self._logger.debug(
            "Migrating from version %s to %s",
            current_version,
            target_version,
        )
        
        version = current_version
        migrated_data = data.copy()
        
        # Apply migrations in sequence until we reach the target version
        while version != target_version:
            if version not in self._migrations:
                raise MigrationError(
                    f"No migration path from version {version} to {target_version}"
                )
            
            migration = self._migrations[version]
            self._logger.debug(
                "Applying migration from %s to %s",
                migration.from_version,
                migration.to_version,
            )
            
            result = await migration.migrate(migrated_data, model_type)
            if not result.success:
                raise MigrationError(
                    f"Migration from {migration.from_version} to {migration.to_version} failed: {result.error}"
                )
            
            migrated_data = cast(Dict[str, Any], result.migrated_data)
            version = migration.to_version
        
        return migrated_data


class InlineMigration(Migration):
    """A migration defined by a simple function."""
    
    def __init__(
        self,
        from_version: str,
        to_version: str,
        migrate_fn,
        logger: Optional[LoggerProtocol] = None,
    ) -> None:
        """Initialize the inline migration.
        
        Args:
            from_version: The version this migration migrates from
            to_version: The version this migration migrates to
            migrate_fn: Function that takes (data, model_type) and returns migrated data
            logger: Logger instance (optional)
        """
        super().__init__(logger)
        self._from_version = from_version
        self._to_version = to_version
        self._migrate_fn = migrate_fn
    
    @property
    def from_version(self) -> str:
        return self._from_version
    
    @property
    def to_version(self) -> str:
        return self._to_version
    
    async def migrate(
        self,
        data: Dict[str, Any],
        model_type: Type[T],
    ) -> MigrationResult:
        try:
            migrated_data = await self._migrate_fn(data, model_type)
            return MigrationResult(success=True, migrated_data=migrated_data)
        except Exception as e:
            self._logger.error(
                "Error in migration from %s to %s: %s",
                self.from_version,
                self.to_version,
                e,
                exc_info=True,
            )
            return MigrationResult(success=False, error=str(e))
