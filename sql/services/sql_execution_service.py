"""
SQL execution service implementation.
"""

import logging
from typing import Any

from uno.persistance.sql.interfaces import SQLExecutionServiceProtocol
from uno.persistance.sql.interfaces import DBManagerProtocol
from uno.persistance.sql.errors import SQLExecutionError


class SQLExecutionService:
    """
    Service for executing SQL statements and scripts.
    """

    def __init__(self, db_manager: DBManagerProtocol, logger: logging.Logger):
        self.db_manager = db_manager
        self.logger = logger

    def execute_ddl(self, ddl: str) -> None:
        """
        Execute a DDL statement.
        """
        await self.logger.debug(f"Executing DDL: {ddl}")
        try:
            self.db_manager.execute_ddl(ddl)
        except Exception as e:
            await self.logger.error(f"Failed to execute DDL: {e}")
            raise SQLExecutionError(
                reason=f"Failed to execute DDL: {e}",
                statement_type="DDL",
            ) from e

    def execute_script(self, script: str) -> None:
        """
        Execute a SQL script.
        """
        await self.logger.debug(f"Executing script: {script}")
        try:
            self.db_manager.execute_script(script)
        except Exception as e:
            await self.logger.error(f"Failed to execute script: {e}")
            raise SQLExecutionError(
                reason=f"Failed to execute script: {e}",
                statement_type="SCRIPT",
            ) from e

    def execute_emitter(self, emitter: Any, dry_run: bool = False) -> list[Any]:
        """
        Execute a SQL emitter.
        """
        await self.logger.debug(f"Executing emitter: {emitter}")
        try:
            return self.db_manager.execute_emitter(emitter, dry_run)
        except Exception as e:
            await self.logger.error(f"Failed to execute emitter: {e}")
            raise SQLExecutionError(
                reason=f"Failed to execute emitter: {e}",
                statement_type="EMITTER",
            ) from e

    """
    Service for executing SQL statements and scripts.
    """

    def __init__(self, db_manager: DBManagerProtocol, logger: logging.Logger):
        self.db_manager = db_manager
        self.logger = logger

    def execute_ddl(self, ddl: str) -> None:
        """
        Execute a DDL statement.
        """
        await self.logger.debug(f"Executing DDL: {ddl}")
        try:
            self.db_manager.execute_ddl(ddl)
        except Exception as e:
            await self.logger.error(f"Failed to execute DDL: {e}")
            raise SQLExecutionError(
                reason=f"Failed to execute DDL: {e}",
                statement_type="DDL",
            ) from e

    def execute_script(self, script: str) -> None:
        """
        Execute a SQL script.
        """
        await self.logger.debug(f"Executing script: {script}")
        try:
            self.db_manager.execute_script(script)
        except Exception as e:
            await self.logger.error(f"Failed to execute script: {e}")
            raise SQLExecutionError(
                reason=f"Failed to execute script: {e}",
                statement_type="SCRIPT",
            ) from e

    def execute_emitter(self, emitter: Any, dry_run: bool = False) -> list[Any]:
        """
        Execute SQL statements from an emitter.
        """
        await self.logger.debug(f"Executing emitter: {emitter.__class__.__name__}")
        try:
            if dry_run:
                return emitter.generate_sql()
            self.db_manager.execute_from_emitter(emitter)
            return [None]
        except Exception as e:
            await self.logger.error(f"Failed to execute emitter: {e}")
            raise SQLExecutionError(
                reason=f"Failed to execute emitter: {e}",
                statement_type="EMITTER",
            ) from e
