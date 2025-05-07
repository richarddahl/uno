"""
SQL trigger emitter implementation.
"""

from typing import Any

from uno.infrastructure.sql.interfaces import SQLEmitterProtocol
from uno.core.errors.result import Result, Success, Failure
from uno.core.errors.base import FrameworkError


class CreateTriggerEmitter:
    """
    Emitter for creating SQL triggers.
    """

    def __init__(self, name: str, definition: str, when: str, event: str, table: str):
        self.name = name
        self.definition = definition
        self.when = when
        self.event = event
        self.table = table

    def emit(self) -> Result[str, FrameworkError]:
        """
        Emit the SQL statement for creating a trigger.
        """
        try:
            sql = f"""
CREATE OR REPLACE TRIGGER {self.name}
    {self.when} {self.event} ON {self.table}
    FOR EACH ROW
BEGIN
    {self.definition}
END;
"""
            return Success(sql)
        except Exception as e:
            return Failure(
                FrameworkError(
                    f"Failed to create trigger emitter: {e}",
                    "SQL_EMITTER_ERROR",
                )
            )


class DropTriggerEmitter:
    """
    Emitter for dropping SQL triggers.
    """

    def __init__(self, name: str, table: str):
        self.name = name
        self.table = table

    def emit(self) -> Result[str, FrameworkError]:
        """
        Emit the SQL statement for dropping a trigger.
        """
        try:
            sql = f"DROP TRIGGER IF EXISTS {self.name} ON {self.table};"
            return Success(sql)
        except Exception as e:
            return Failure(
                FrameworkError(
                    f"Failed to create drop trigger emitter: {e}",
                    "SQL_EMITTER_ERROR",
                )
            )
