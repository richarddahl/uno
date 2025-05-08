"""
SQL function emitter implementation.
"""

from typing import Any

from uno.infrastructure.sql.interfaces import SQLEmitterProtocol
from uno.errors.result import Result, Success, Failure
from uno.errors.base import UnoError


class CreateFunctionEmitter:
    """
    Emitter for creating SQL functions.
    """

    def __init__(self, name: str, definition: str):
        self.name = name
        self.definition = definition

    def emit(self) -> Result[str, UnoError]:
        """
        Emit the SQL statement for creating a function.
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
            return Success(sql)
        except Exception as e:
            return Failure(
                UnoError(
                    f"Failed to create function emitter: {e}",
                    "SQL_EMITTER_ERROR",
                )
            )


class DropFunctionEmitter:
    """
    Emitter for dropping SQL functions.
    """

    def __init__(self, name: str):
        self.name = name

    def emit(self) -> Result[str, UnoError]:
        """
        Emit the SQL statement for dropping a function.
        """
        try:
            sql = f"DROP FUNCTION IF EXISTS {self.name}();"
            return Success(sql)
        except Exception as e:
            return Failure(
                UnoError(
                    f"Failed to create drop function emitter: {e}",
                    "SQL_EMITTER_ERROR",
                )
            )
