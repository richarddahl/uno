# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Simple test to verify the restructured package imports.

This script just checks that all the imports work correctly from the restructured
packages without trying to run any actual functionality.
"""


def test_imports():
    """Test that all imports work from the restructured packages."""
    print("\n--- Testing Package Imports ---")

    # Test uno.events imports
    try:
        from uno.events.protocols import EventBusProtocol
from uno.persistence.event_sourcing.protocols import EventStoreProtocol
        from uno.events.implementations.bus import InMemoryEventBus
        from uno.events.implementations.store import InMemoryEventStore

        print("✅ Imported uno.events protocols and implementations successfully")
    except ImportError as e:
        print(f"❌ Failed to import from uno.events: {e}")

    # Test uno.uow imports
    try:
        from uno.uow.protocols import UnitOfWork
        from uno.uow.implementations.memory import InMemoryUnitOfWork
        from uno.uow.implementations.postgres import PostgresUnitOfWork

        print("✅ Imported uno.uow protocols and implementations successfully")
    except ImportError as e:
        print(f"❌ Failed to import from uno.uow: {e}")

    # Test uno.persistence imports
    try:
        from uno.persistence.event_sourcing import (
            PostgresEventStore,
            PostgresEventBus,
            PostgresCommandBus,
            PostgresSagaStore,
        )

        print("✅ Imported uno.persistence implementations successfully")
    except ImportError as e:
        print(f"❌ Failed to import from uno.persistence: {e}")

    # Test uno.sagas imports
    try:
        from uno.sagas.protocols import SagaStoreProtocol, SagaState
        from uno.sagas.implementations.memory import InMemorySagaStore

        print("✅ Imported uno.sagas protocols and implementations successfully")
    except ImportError as e:
        print(f"❌ Failed to import from uno.sagas: {e}")

    print("\nImport tests completed.")


if __name__ == "__main__":
    print("Starting import tests...")
    test_imports()
