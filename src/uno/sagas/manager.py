# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Saga orchestration engine for Uno event sourcing.
"""

from typing import Generic, TypeVar

from uno.di.protocols import ScopeProtocol  # Changed from uno.di.scope
from uno.errors import ErrorCategory, UnoError
from uno.logging import LoggerProtocol
from uno.sagas.protocols import SagaProtocol, SagaState, SagaStoreProtocol

E = TypeVar("E")  # Event type
C = TypeVar("C")  # Command type


class SagaManager(Generic[E, C]):
    """
    Saga orchestration engine for Uno event sourcing.

    Manages the lifecycle of sagas/process managers, including event handling,
    state persistence, and error recovery.
    """

    def __init__(
        self,
        saga_store: SagaStoreProtocol,
        scope: ScopeProtocol,
        logger: LoggerProtocol,
    ) -> None:
        """Initialize SagaManager with dependencies.

        Args:
            saga_store: Store for persisting saga state
            scope: DI scope for resolving saga instances
            logger: Logger instance (must be injected via DI)
        """
        self._saga_store = saga_store
        self._scope = scope
        self.logger = logger
        self._saga_types: dict[str, type[SagaProtocol[E, C]]] = {}
        self._active_sagas: dict[str, SagaProtocol[E, C]] = {}

    async def _get_or_create_saga(
        self, saga_id: str, saga_type: str
    ) -> SagaProtocol[E, C]:
        """
        Get an existing saga instance or create a new one.

        Args:
            saga_id: The ID of the saga to get or create
            saga_type: The type of saga to create if it doesn't exist

        Returns:
            The saga instance

        Raises:
            UnoError: if the saga type is unknown or creation fails
        """
        # Check if we already have an active instance
        if saga_id in self._active_sagas:
            return self._active_sagas[saga_id]

        # Try to load from store first
        state = await self._saga_store.load_state(saga_id)
        if state is not None:
            return await self._create_saga_instance(state)

        # Create new instance if not found
        return await self._create_saga_instance(
            SagaState(saga_id=saga_id, status="pending", data={}, saga_type=saga_type)
        )

    async def _create_saga_instance(self, state: SagaState) -> SagaProtocol[E, C]:
        """
        Create a saga instance from a given state.

        Args:
            state: The saga state to create from

        Returns:
            The saga instance

        Raises:
            UnoError: if saga creation fails
        """
        try:
            saga_cls = self._saga_types[state.saga_type]
        except KeyError:
            await self.logger.debug(f"No saga found for type: {state.saga_type}")
            raise UnoError(
                message=f"Unknown saga type: {state.saga_type}",
                category=ErrorCategory.INTERNAL,
                reason="SagaProtocol type not registered",
            ) from None

        try:
            saga = self._scope.resolve(saga_cls)  # type: ignore[no-any-return]
            # Verify the resolved object implements SagaProtocol
            if not isinstance(saga, SagaProtocol):
                raise UnoError(
                    message=f"Resolved saga {state.saga_type} does not implement SagaProtocol",
                    category=ErrorCategory.INTERNAL,
                    reason="Invalid saga type",
                )
            # Set the saga's state using the canonical method
            saga.set_state(state)
            self._active_sagas[state.saga_id] = saga
            return saga
        except Exception as e:
            raise UnoError(
                message=f"Failed to create saga {state.saga_type}: {e}",
                category=ErrorCategory.INTERNAL,
                reason=f"Saga creation error: {e}",
            ) from e

    def list_active_sagas(self) -> list[SagaProtocol[E, C]]:
        """
        List all currently active sagas.

        Returns:
            List of active saga instances
        """
        return list(self._active_sagas.values())

    async def register_saga(self, saga_type: type[SagaProtocol[E, C]]) -> None:
        """
        Register a saga type with the manager.

        Args:
            saga_type: The saga class to register

        Raises:
            UnoError: if saga registration fails
        """
        try:
            # Check if the type implements the required protocol methods
            required_attrs = ["handle_event", "saga_id", "saga_state"]
            is_protocol_compliant = all(
                hasattr(saga_type, attr) for attr in required_attrs
            )

            if is_protocol_compliant:
                await self.logger.info(f"Validated saga type: {saga_type.__name__}")
            else:
                raise UnoError(
                    message=f"Saga type {saga_type.__name__} does not implement required SagaProtocol methods",
                    category=ErrorCategory.INTERNAL,
                    reason="Invalid saga type - does not implement required Protocol methods/attributes",
                )

            self._saga_types[saga_type.__name__] = saga_type
        except Exception as e:
            raise UnoError(
                message=f"Failed to register saga type {saga_type.__name__}: {e}",
                category=ErrorCategory.INTERNAL,
                reason=f"Protocol registration error: {e}",
            ) from e

    async def handle_event(self, saga_id: str, saga_type: str, event: E) -> None:
        """
        Handle an event in the context of a specific saga.

        Args:
            saga_id: The ID of the saga to handle the event
            saga_type: The type of saga to create if it doesn't exist
            event: The event to handle

        Raises:
            UnoError: if event handling fails
        """
        try:
            saga = await self._get_or_create_saga(saga_id, saga_type)
            await saga.handle_event(event)
            if saga.saga_state is not None:
                await self._persist_state(saga)
                if saga.saga_state.is_completed:
                    await self._saga_store.delete_state(saga_id)
                    self._active_sagas.pop(saga_id, None)
        except Exception as e:
            raise UnoError(
                message=f"Failed to handle event in saga {saga_type}: {e}",
                category=ErrorCategory.INTERNAL,
                reason=f"Event handling error: {e}",
            ) from e
