"""Unit tests for the Unit of Work implementation."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from uno.domain.aggregate import AggregateRoot
from uno.uow import (
    UnitOfWorkError,
    ConcurrencyError,
    RepositoryError,
    UnitOfWorkManager,
    UnitOfWorkFactory,
    BaseUnitOfWork,
)


class MockAggregate(AggregateRoot):
    """Test aggregate for unit testing."""

    name: str = "Test"


class TestUnitOfWork:
    """Unit tests for the Unit of Work implementation."""

    async def test_uow_context_manager_success(self, uow_factory: UnitOfWorkManager):
        """Test successful UoW context manager usage."""
        async with uow_factory.transaction() as uow:
            repo = uow.get_repository(MockAggregate)
            aggregate = MockAggregate()
            await repo.add(aggregate)

            # Verify the aggregate was added to the repository
            assert aggregate in repo.seen()

        # After successful commit, the UoW should be disposed
        assert uow._disposed

    async def test_uow_context_manager_error(self, uow_factory: UnitOfWorkManager):
        """Test UoW context manager with error handling."""
        with pytest.raises(ValueError, match="Something went wrong"):
            async with uow_factory.transaction() as uow:
                repo = uow.get_repository(MockAggregate)
                aggregate = MockAggregate()
                await repo.add(aggregate)
                raise ValueError("Something went wrong")

        # The UoW should be disposed even on error
        assert uow._disposed

    async def test_get_repository_caching(self, uow: BaseUnitOfWork):
        """Test that repositories are cached by aggregate type."""
        repo1 = uow.get_repository(MockAggregate)
        repo2 = uow.get_repository(MockAggregate)

        assert repo1 is repo2  # Should be the same instance

    async def test_collect_new_events(self, uow: BaseUnitOfWork):
        """Test collecting new events from aggregates."""
        # Setup
        repo = uow.get_repository(MockAggregate)
        aggregate = MockAggregate()

        # Add an event
        event = type("MockEvent", (), {"__module__": "test"})
        aggregate._pending_events = [event]

        # Add aggregate to repository
        await repo.add(aggregate)

        # Collect events
        events = uow.collect_new_events()

        # Verify
        assert len(events) == 1
        assert events[0] is event
        assert not aggregate.pending_events  # Events should be cleared


class TestUnitOfWorkFactory:
    """Unit tests for the UnitOfWorkFactory."""

    async def test_create_uow(self, uow_factory: UnitOfWorkFactory):
        """Test creating a new Unit of Work."""
        uow = await uow_factory.start()
        try:
            assert isinstance(uow, BaseUnitOfWork)
        finally:
            await uow.dispose()

    async def test_commit_uow(self, uow_factory: UnitOfWorkFactory):
        """Test committing a Unit of Work."""
        uow = await uow_factory.start()
        try:
            # The mock UoW doesn't actually do anything on commit
            await uow_factory.commit(uow)
            assert not uow._disposed
        finally:
            await uow.dispose()

    async def test_rollback_uow(self, uow_factory: UnitOfWorkFactory):
        """Test rolling back a Unit of Work."""
        uow = await uow_factory.start()
        try:
            # The mock UoW doesn't actually do anything on rollback
            await uow_factory.rollback(uow)
            assert not uow._disposed
        finally:
            await uow.dispose()


class TestErrorHandling:
    """Test error handling in the Unit of Work."""

    async def test_double_commit(self, uow: BaseUnitOfWork):
        """Test that committing twice raises an error."""
        await uow.commit()
        with pytest.raises(RuntimeError, match="already committed"):
            await uow.commit()

    async def test_commit_after_dispose(self, uow: BaseUnitOfWork):
        """Test that committing after dispose raises an error."""
        await uow.dispose()
        with pytest.raises(RuntimeError, match="disposed"):
            await uow.commit()

    async def test_reuse_disposed_uow(self, uow: BaseUnitOfWork):
        """Test that a disposed UoW cannot be reused."""
        await uow.dispose()
        with pytest.raises(RuntimeError, match="Cannot reuse"):
            async with uow:
                pass
