"""
Tests for asynchronous event handling patterns.

This module tests the async patterns in the Uno events system, ensuring that
both synchronous and asynchronous handlers work correctly in all combinations.
"""

import pytest
from typing import Any

from uno.core.errors.result import Result, Success
from uno.core.events.async_utils import AsyncEventHandlerAdapter
from uno.core.events.context import EventHandlerContext
from uno.core.events.events import DomainEvent, EventBus
from uno.core.events.handlers import EventHandler, EventHandlerRegistry


# Define constants for test magic values
EXPECTED_HANDLER_COUNT = 3
EXPECTED_RESULTS_COUNT = 2
TEST_EVENT_DATA = "test_data"


class TestEvent(DomainEvent):
    """Test event for async pattern tests."""
    event_type: str = 'test_event'  # Type annotation required for Pydantic v2
    data: str
    
    def __init__(self, data: str = TEST_EVENT_DATA):
        super().__init__(data=data)


class SyncHandler:
    """A synchronous handler function (not a class)."""
    
    def __init__(self):
        self.called = False
        self.event_id = None
        
    def __call__(self, context: EventHandlerContext) -> Result[Any, Exception]:
        """Handle the event synchronously."""
        self.called = True
        self.event_id = context.event.event_id
        return Success({"handled_sync": True})


class AsyncHandler:
    """An asynchronous handler function (not a class)."""
    
    def __init__(self):
        self.called = False
        self.event_id = None
        
    async def __call__(self, context: EventHandlerContext) -> Result[Any, Exception]:
        """Handle the event asynchronously."""
        self.called = True
        self.event_id = context.event.event_id
        return Success({"handled_async": True})


class TestAsyncHandlerAdapter:
    """Tests for the AsyncEventHandlerAdapter."""
    
    def test_detect_sync_handler(self):
        """Test that sync handlers are correctly detected."""
        handler = SyncHandler()
        adapter = AsyncEventHandlerAdapter(handler)
        assert adapter._is_async is False
        
    def test_detect_async_handler(self):
        """Test that async handlers are correctly detected."""
        handler = AsyncHandler()
        adapter = AsyncEventHandlerAdapter(handler)
        assert adapter._is_async is True
        
    @pytest.mark.asyncio
    async def test_handle_sync_handler(self):
        """Test handling an event with a sync handler."""
        handler = SyncHandler()
        adapter = AsyncEventHandlerAdapter(handler)
        
        event = TestEvent(data="test data")
        context = EventHandlerContext(event=event)
        
        result = await adapter.handle(context)
        
        assert result.is_success
        assert handler.called
        assert handler.event_id == event.event_id
        assert result.value == {"handled_sync": True}
        
    @pytest.mark.asyncio
    async def test_handle_async_handler(self):
        """Test handling an event with an async handler."""
        handler = AsyncHandler()
        adapter = AsyncEventHandlerAdapter(handler)
        
        event = TestEvent(data="test data")
        context = EventHandlerContext(event=event)
        
        result = await adapter.handle(context)
        
        assert result.is_success
        assert handler.called
        assert handler.event_id == event.event_id
        assert result.value == {"handled_async": True}


class TestAsyncEventHandlerAdapter:
    """Tests for the AsyncEventHandlerAdapter class."""



    @pytest.mark.asyncio
    async def test_async_handler_adapter_with_async_handler(self):
        """Test that AsyncEventHandlerAdapter properly works with async handlers."""
        # Define async handler class inline
        class AsyncTestHandler(EventHandler):
            was_called = False
            
            async def handle(self, context: EventHandlerContext) -> Result[None, Exception]:
                AsyncTestHandler.was_called = True
                return Success(None)

        handler = AsyncTestHandler()
        adapter = AsyncEventHandlerAdapter(handler)
        event = TestEvent()
        context = EventHandlerContext(event=event)
        
        # Execute the handler through the adapter
        result = await adapter.handle(context)
        
        assert result.is_success
        assert AsyncTestHandler.was_called is True
        
    @pytest.mark.asyncio
    async def test_async_handler_adapter_with_sync_handler(self):
        """Test that AsyncEventHandlerAdapter properly works with sync handlers."""
        # Define sync handler class inline
        class SyncTestHandler(EventHandler):
            was_called = False
            
            def handle(self, context: EventHandlerContext) -> Result[None, Exception]:
                SyncTestHandler.was_called = True
                return Success(None)

        handler = SyncTestHandler()
        adapter = AsyncEventHandlerAdapter(handler)
        event = TestEvent()
        context = EventHandlerContext(event=event)
        
        # Execute the handler through the adapter
        result = await adapter.handle(context)
        
        assert result.is_success
        assert SyncTestHandler.was_called is True


class TestHandlerClass(EventHandler):
    """A test handler class that implements the EventHandler interface."""
    
    def __init__(self):
        super().__init__(TestEvent)
        self.called = False
        self.event_id = None
        
    async def handle(self, context: EventHandlerContext) -> Result[Any, Exception]:
        """Handle the event."""
        self.called = True
        self.event_id = context.event.event_id
        return Success({"handled_by_class": True})


class TestEventBus:
    """Tests for the updated EventBus with consistent async patterns."""
    
    @pytest.fixture
    def logger_service(self):
        """Provide a logger service for testing."""
        # Mock a simple logger service for testing
        class MockLoggerService:
            def debug(self, message, **kwargs):
                pass
            
            def info(self, message, **kwargs):
                pass
            
            def warning(self, message, **kwargs):
                pass
            
            def error(self, message, **kwargs):
                pass
        
        return MockLoggerService()
    
    @pytest.fixture
    def event_bus(self, logger_service):
        """Fixture for a test event bus."""
        return EventBus(logger_service)
    
    @pytest.mark.asyncio
    async def test_publish_to_sync_handler(self, event_bus):
        """Test publishing an event to a sync handler."""
        # Register a sync handler
        handler = SyncHandler()
        event_bus._registry.register_handler("test_event", handler)
        
        # Create and publish an event
        event = TestEvent(data="test sync data")
        result = await event_bus.publish(event)
        
        # Check the results
        assert result.is_success
        assert len(result.value) == 1
        assert result.value[0].is_success
        assert result.value[0].value == {"handled_sync": True}
        assert handler.called
        assert handler.event_id == event.event_id
    
    @pytest.mark.asyncio
    async def test_publish_to_async_handler(self, event_bus):
        """Test publishing an event to an async handler."""
        # Register an async handler
        handler = AsyncHandler()
        event_bus._registry.register_handler("test_event", handler)
        
        # Create and publish an event
        event = TestEvent(data="test async data")
        result = await event_bus.publish(event)
        
        # Check the results
        assert result.is_success
        assert len(result.value) == 1
        assert result.value[0].is_success
        assert result.value[0].value == {"handled_async": True}
        assert handler.called
        assert handler.event_id == event.event_id
    
    @pytest.mark.asyncio
    async def test_publish_to_handler_class(self, event_bus):
        """Test publishing an event to a handler class."""
        # Register a handler class
        handler = TestHandlerClass()
        event_bus._registry.register_handler("test_event", handler)
        
        # Create and publish an event
        event = TestEvent(data="test class data")
        result = await event_bus.publish(event)
        
        # Check the results
        assert result.is_success
        assert len(result.value) == 1
        assert result.value[0].is_success
        assert result.value[0].value == {"handled_by_class": True}
        assert handler.called
        assert handler.event_id == event.event_id
    
    @pytest.mark.asyncio
    async def test_publish_to_multiple_handlers(self, event_bus):
        """Test publishing an event to multiple handlers of different types."""
        # Register multiple handlers
        sync_handler = SyncHandler()
        async_handler = AsyncHandler()
        class_handler = TestHandlerClass()
        
        event_bus._registry.register_handler("test_event", sync_handler)
        event_bus._registry.register_handler("test_event", async_handler)
        event_bus._registry.register_handler("test_event", class_handler)
        
        # Create and publish an event
        event = TestEvent(data="test multi data")
        result = await event_bus.publish(event)
        
        # Check the results
        assert result.is_success
        assert len(result.value) == 3
        assert all(r.is_success for r in result.value)
        
        # Check that all handlers were called
        assert sync_handler.called
        assert sync_handler.event_id == event.event_id
        
        assert async_handler.called
        assert async_handler.event_id == event.event_id
        
        assert class_handler.called
        assert class_handler.event_id == event.event_id
    
    @pytest.mark.asyncio
    async def test_publish_many(self, event_bus):
        """Test publishing multiple events."""
        # Register a handler
        handler = SyncHandler()
        event_bus._registry.register_handler("test_event", handler)
        
        # Create and publish multiple events
        events = [
            TestEvent(data="test data 1"),
            TestEvent(data="test data 2"),
            TestEvent(data="test data 3")
        ]
        
        result = await event_bus.publish_many(events)
        
        # Check the results
        assert result.is_success
        assert len(result.value) == 3
        assert all(r.is_success for r in result.value)
        
        # The handler should have been called 3 times
        # and the event_id should be the id of the last event
        assert handler.called
        assert handler.event_id == events[2].event_id
