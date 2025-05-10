"""
SQL function emitter implementation.
"""

from typing import Any
from uno.errors import UnoError
from uno.persistence.sql.interfaces import SQLEmitterProtocol


class CreateFunctionEmitter:
    """
    Emitter for creating SQL functions.
    """

    def __init__(self, name: str, definition: str):
        self.name = name
        self.definition = definition

    def emit(self) -> str:
        """
        Emit the SQL statement for creating a function.
        
        Raises:
            UnoError: If there's an error creating the function emitter
        """
        try:
            sql = f"""
CREATE OR REPLACE FUNCTION {self.name}()
RETURNS void AS $$
BEGIN
    {self.definition}
END;
$$ LANGUAGE plpgsql;
"""
            return sql
        except Exception as e:
            raise UnoError(
                f"Failed to create function emitter: {e}",
                "SQL_EMITTER_ERROR",
            ) from e


class DropFunctionEmitter:
    """
    Emitter for dropping SQL functions.
    """

    def __init__(self, name: str):
        self.name = name

    def emit(self) -> str:
        """
        Emit the SQL statement for dropping a function.
        
        Raises:
            UnoError: If there's an error creating the drop function emitter
        """
        try:
            sql = f"DROP FUNCTION IF EXISTS {self.name}();"
            return sql
        except Exception as e:
            raise UnoError(
                f"Failed to create drop function emitter: {e}",
                "SQL_EMITTER_ERROR",
            ) from e
