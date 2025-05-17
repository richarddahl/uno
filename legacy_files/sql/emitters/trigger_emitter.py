"""
SQL trigger emitter implementation.
"""

from typing import Any
from uno.persistance.sql.errors import SQLEmitterError
from uno.persistance.sql.interfaces import SQLEmitterProtocol


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

    def emit(self) -> str:
        """
        Emit the SQL statement for creating a trigger.

        Raises:
            UnoError: If there's an error creating the trigger emitter
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
            return sql
        except Exception as e:
            raise SQLEmitterError(
                reason=f"Failed to create trigger emitter: {e}",
                emitter=self.__class__.__name__,
            ) from e


class DropTriggerEmitter:
    """
    Emitter for dropping SQL triggers.
    """

    def __init__(self, name: str, table: str):
        self.name = name
        self.table = table

    def emit(self) -> str:
        """
        Emit the SQL statement for dropping a trigger.

        Raises:
            UnoError: If there's an error creating the drop trigger emitter
        """
        try:
            sql = f"DROP TRIGGER IF EXISTS {self.name} ON {self.table};"
            return sql
        except Exception as e:
            raise SQLEmitterError(
                reason=f"Failed to create drop trigger emitter: {e}",
                emitter=self.__class__.__name__,
            ) from e
