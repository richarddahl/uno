# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Saga orchestration engine for Uno event sourcing.
"""

import logging
from typing import Any, Generic, TypeVar, cast

from uno.di.protocols import ScopeProtocol
from uno.errors import ErrorCategory, UnoError
from uno.sagas.protocols import SagaProtocol, SagaState, SagaStoreProtocol

logger = logging.getLogger(__name__)

E = TypeVar("E")  # Event type
C = TypeVar("C")  # Command type


class SagaManager(Generic[E, C]):
    """
    Saga orchestration engine for Uno event sourcing.

    Manages the lifecycle of sagas/process managers, including event handling,
    state persistence, and error recovery.
    """

    def __init__(self, saga_store: SagaStoreProtocol, scope: ScopeProtocol) -> None:
        """
        Initialize the saga manager.

        Args:
            saga_store: Store for saga state persistence
            scope: Service scope for dependency resolution
        """
        self._saga_store = saga_store
        self._scope = scope
        self._saga_types: dict[str, type[SagaProtocol[E, C]]] = {}
        self._active_sagas: dict[str, SagaProtocol[E, C]] = {}

    async def _get_or_create_saga(self, saga_id: str, saga_type: str) -> SagaProtocol[E, C]:
        """
        Get an existing saga or create a new one.

        Args:
            saga_id: Unique identifier for the saga
            saga_type: Type of saga to create

        Returns:
            The saga instance

        Raises:
            UnoError: if saga type is not registered or creation fails
        """
        if saga_id in self._active_sagas:
            return self._active_sagas[saga_id]

        try:
            saga_cls = self._saga_types[saga_type]
        except KeyError:
                raise UnoError(
                    message=f"Unknown saga type: {saga_type}",
                    error_category=ErrorCategory.INTERNAL,
                    reason="SagaProtocol type not registered"
                )

        try:
            saga = self._scope.resolve(saga_cls)
            # Verify the resolved object implements SagaProtocol
            if not isinstance(saga, SagaProtocol):
                raise UnoError(
                    message=f"Resolved saga {saga_type} does not implement SagaProtocol",
                    error_category=ErrorCategory.INTERNAL,
                    reason="Invalid saga type"
                )
                
            # Now we know it's a SagaProtocol, set its properties
            # We explicitly access these as properties since mypy knows SagaProtocol has them
            saga_protocol = cast("SagaProtocol[E, C]", saga)  # Properly cast using typing.cast with quotes
            saga_protocol.saga_id = saga_id
            saga_protocol.saga_state = SagaState(saga_id=saga_id, status="pending", data={})
            self._active_sagas[saga_id] = saga_protocol
            return saga_protocol
        except Exception as e:
            raise UnoError(
                message=f"Failed to create saga {saga_type}: {str(e)}",
                error_category=ErrorCategory.INTERNAL,
                reason=f"Saga creation error: {str(e)}"
            ) from e

    def list_active_sagas(self) -> list[SagaProtocol[E, C]]:
        """
        List all currently active sagas.

        Returns:
            List of active saga instances
        """
        return list(self._active_sagas.values())  # explicit conversion

    def register_saga(self, saga_type: type[SagaProtocol[E, C]]) -> None:
        """
        Register a saga type with the manager.

        Args:
            saga_type: The saga class to register

        Raises:
            UnoError: if saga registration fails
        """
        try:
            # For Protocol classes, we validate by checking if they support the required methods/attributes
            # rather than using issubclass which is for inheritance-based checks
            sample_instance = None
            
            # Try to create a sample instance to check protocol compliance
            try:
                sample_instance = saga_type()  # type: ignore
            except Exception as inst_ex:
                logger.debug(f"Could not instantiate {saga_type.__name__} for protocol check: {inst_ex}")
            
            # If we have a sample instance, check directly; otherwise infer from class attributes
            is_protocol_compliant = False
            if sample_instance is not None:
                is_protocol_compliant = isinstance(sample_instance, SagaProtocol)  
            else:
                # Check if the class has all required methods/attributes of SagaProtocol
                required_attrs = ["saga_id", "saga_state", "handle_event", "is_completed", "compensate"]
                is_protocol_compliant = all(hasattr(saga_type, attr) for attr in required_attrs)  
                
            if is_protocol_compliant:
                logger.info(f"Validated {saga_type.__name__} as SagaProtocol compatible via attributes check")
                
            if not is_protocol_compliant:
                raise UnoError(
                    message=f"Cannot register {saga_type.__name__}: does not implement SagaProtocol",
                    error_category=ErrorCategory.INTERNAL,
                    reason="Invalid saga type - does not implement required Protocol methods/attributes",
                )
            
            self._saga_types[saga_type.__name__] = saga_type
        except Exception as e:
            raise UnoError(
                message=f"Failed to register saga type {saga_type.__name__}: {str(e)}",
                error_category=ErrorCategory.INTERNAL,
                reason=f"Protocol registration error: {str(e)}",
            ) from e

    async def handle_event(self, saga_id: str, saga_type: str, event: E) -> None:
        """
        Handle an event in the context of a specific saga.

        Args:
            saga_id: Unique identifier for the saga
            saga_type: Type of saga to handle the event
            event: The event to process

        Raises:
            UnoError: if event handling fails
        """
        try:
            saga = await self._get_or_create_saga(saga_id, saga_type)
            # Load existing state if available
            state = await self._saga_store.load_state(saga_id)
            if state:
                saga.saga_state = state
            await saga.handle_event(event)
            if bool(saga.saga_state):  # explicit bool conversion
                await self._saga_store.save_state(saga_id, saga.saga_state)
            if bool(saga.is_completed()):  # explicit bool conversion
                await self._saga_store.delete_state(saga_id)
                self._active_sagas.pop(saga_id, None)  # pop with default of None
        except Exception as e:
            raise UnoError(
                message=f"Failed to handle event in saga {saga_type}: {str(e)}",
                error_category=ErrorCategory.INTERNAL,
                reason=f"Event handling error: {str(e)}"
            ) from e
