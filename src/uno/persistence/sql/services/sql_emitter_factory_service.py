"""
SQL emitter factory service implementation.
"""

from typing import Any

from uno.persistence.sql.interfaces import SQLEmitterFactoryProtocol
from uno.persistence.sql.emitters import (
    CreateTriggerEmitter,
    DropTriggerEmitter,
    CreateFunctionEmitter,
    DropFunctionEmitter,
)


class SQLEmitterFactoryService:
    """
    Factory service for creating SQL emitters.
    """

    def create(self, emitter_type: str, **kwargs: Any) -> Any:
        """
        Create a SQL emitter based on the type and provided arguments.

        Args:
            emitter_type: Type of emitter to create ('trigger', 'function')
            kwargs: Additional arguments for the emitter

        Returns:
            The created emitter instance
        """
        if emitter_type == "trigger":
            if "action" in kwargs:
                return CreateTriggerEmitter(
                    kwargs["name"],
                    kwargs["definition"],
                    kwargs["when"],
                    kwargs["event"],
                    kwargs["table"],
                )
            else:
                return DropTriggerEmitter(kwargs["name"], kwargs["table"])
        elif emitter_type == "function":
            if "definition" in kwargs:
                return CreateFunctionEmitter(kwargs["name"], kwargs["definition"])
            else:
                return DropFunctionEmitter(kwargs["name"])
        raise ValueError(f"Unknown emitter type: {emitter_type}")

    """
    Factory service for creating SQL emitters.
    """

    def create_trigger_emitter(
        self, name: str, definition: str, when: str, event: str, table: str
    ) -> Any:
        """
        Create a trigger emitter.
        """
        return CreateTriggerEmitter(name, definition, when, event, table)

    def drop_trigger_emitter(self, name: str, table: str) -> Any:
        """
        Create a drop trigger emitter.
        """
        return DropTriggerEmitter(name, table)

    def create_function_emitter(self, name: str, definition: str) -> Any:
        """
        Create a function emitter.
        """
        return CreateFunctionEmitter(name, definition)

    def drop_function_emitter(self, name: str) -> Any:
        """
        Create a drop function emitter.
        """
        return DropFunctionEmitter(name)

    """
    Factory service for creating SQL emitters.
    """

    def create_trigger_emitter(
        self, name: str, definition: str, when: str, event: str, table: str
    ) -> Any:
        """
        Create a trigger emitter.
        """
        return CreateTriggerEmitter(name, definition, when, event, table)

    def drop_trigger_emitter(self, name: str, table: str) -> Any:
        """
        Create a drop trigger emitter.
        """
        return DropTriggerEmitter(name, table)

    def create_function_emitter(self, name: str, definition: str) -> Any:
        """
        Create a function emitter.
        """
        return CreateFunctionEmitter(name, definition)

    def drop_function_emitter(self, name: str) -> Any:
        """
        Create a drop function emitter.
        """
        return DropFunctionEmitter(name)
