"""Tests for the event handler discovery system."""

import asyncio
from typing import Any, ClassVar, cast

import pytest
from unittest.mock import Mock, patch

from uno.core.errors.result import Result, Success, Failure
from uno.core.events.context import EventHandlerContext
from uno.core.events.decorators import EventHandlerDecorator, handles, function_handler
from uno.core.events.discovery import discover_handlers, register_handlers_from_modules
from uno.core.events.events import DomainEvent
from uno.core.events.handlers import EventHandler, EventHandlerRegistry
from uno.core.events.async_utils import FunctionHandlerAdapter, AsyncEventHandlerAdapter
from uno.core.logging.logger import LoggerService


# Test events
class TestEvent(DomainEvent):
    """Test event for discovery tests."""
    event_type = "test_event"
    
    def __init__(self, event_id: str = "test"):
        self.event_id = event_id
        super().__init__()


class AnotherTestEvent(DomainEvent):
    """Another test event for discovery tests."""
    event_type = "another_test_event"
    
    def __init__(self, data: str = "test_data"):
        self.data = data
        super().__init__()


# Test handler classes
@handles(TestEvent)
class TestHandler(EventHandler):
    """Test handler class with handles decorator."""
    handler_called: ClassVar[bool] = False
    
    async def handle(self, context: EventHandlerContext) -> Result[None, Exception]:
        """Handle the test event."""
        event = context.get_typed_event(TestEvent)
        TestHandler.handler_called = True
        return Success(None)


class PlainHandler(EventHandler):
    """Test handler without decorator (for manual registration)."""
    handler_called: ClassVar[bool] = False
    
    def __init__(self):
        self._event_type = "another_test_event"
        self._is_event_handler = True
    
    async def handle(self, context: EventHandlerContext) -> Result[None, Exception]:
        """Handle another test event."""
        event = cast('AnotherTestEvent', context.event)
        PlainHandler.handler_called = True
        return Success(None)


# Function handlers
@function_handler(TestEvent)
async def async_function_handler(context: EventHandlerContext) -> Result[None, Exception]:
    """Async function handler for test events."""
    event = context.get_typed_event(TestEvent)
    return Success({"function_handled": True, "event_id": event.event_id})


@function_handler(AnotherTestEvent)
def sync_function_handler(context: EventHandlerContext) -> Result[None, Exception]:
    """Sync function handler for another test events."""
    event = cast('AnotherTestEvent', context.event)
    return Success({"function_handled": True, "data": event.data})


# Module-like handler object
class HandlerModule:
    """Module with handle method that acts as a handler."""
    handler_called: ClassVar[bool] = False
    
    def __init__(self):
        self._event_type = "test_event"
        self._is_event_handler = True
    
    async def handle(self, context: EventHandlerContext) -> Result[None, Exception]:
        """Handle the test event."""
        HandlerModule.handler_called = True
        return Success(None)


class TestEventHandlerContext:
    """Tests for the enhanced EventHandlerContext."""
    
    def test_get_typed_event(self):
        """Test the get_typed_event method for type-safe event access."""
        event = TestEvent("test123")
        context = EventHandlerContext(event=event)
        
        # Should correctly return typed event
        typed_event = context.get_typed_event(TestEvent)
        assert typed_event.event_id == "test123"
        
        # Should raise TypeError for wrong type
        with pytest.raises(TypeError):
            context.get_typed_event(AnotherTestEvent)
    
    def test_with_extra(self):
        """Test the with_extra method for immutable context updates."""
        event = TestEvent()
        context = EventHandlerContext(event=event, metadata={"request_id": "abc"})
        
        # Create new context with extra data
        new_context = context.with_extra("correlation_id", "xyz")
        
        # Original should remain unchanged
        assert "correlation_id" not in context.extra
        
        # New context should have the extra data
        assert new_context.extra["correlation_id"] == "xyz"
        
        # New context should keep original metadata
        assert new_context.metadata["request_id"] == "abc"
        
        # Both contexts should refer to same event
        assert new_context.event is context.event


class TestEventHandlerDiscovery:
    """Tests for the event handler discovery functionality."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Reset class variables
        TestHandler.handler_called = False
        PlainHandler.handler_called = False
        HandlerModule.handler_called = False
        
        # Create registry and logger
        self.registry = EventHandlerRegistry()
        self.logger = LoggerService(name="test_logger")
        
        # Set up decorator registry
        EventHandlerDecorator.set_registry(None)  # Reset to avoid test interference
    
    def test_discover_class_handlers(self):
        """Test discovering class-based handlers with decorators."""
        handlers = discover_handlers(globals(), None, self.logger)
        
        # Find our test handler in results
        test_handlers = [h for h in handlers if hasattr(h, "__name__") and h.__name__ == "TestHandler"]
        assert len(test_handlers) == 1
        assert test_handlers[0]._event_type == "test_event"
        assert test_handlers[0]._is_event_handler is True
    
    def test_discover_function_handlers(self):
        """Test discovering function handlers with decorators."""
        handlers = discover_handlers(globals(), None, self.logger)
        
        # Find our function handlers in results
        function_handlers = [h for h in handlers if hasattr(h, "__name__") and 
                            (h.__name__ == "async_function_handler" or h.__name__ == "sync_function_handler")]
        
        assert len(function_handlers) == 2
        
        # Verify properties
        async_handler = next(h for h in function_handlers if h.__name__ == "async_function_handler")
        sync_handler = next(h for h in function_handlers if h.__name__ == "sync_function_handler")
        
        assert async_handler._event_type == "test_event"
        assert async_handler._is_event_handler is True
        
        assert sync_handler._event_type == "another_test_event"
        assert sync_handler._is_event_handler is True
    
    def test_discover_module_handlers(self):
        """Test discovering custom objects with _is_event_handler attribute."""
        # Create a module handler in the globals
        module_handler = HandlerModule()
        globals()["my_module_handler"] = module_handler
        
        try:
            handlers = discover_handlers(globals(), None, self.logger)
            
            # Find module handlers
            module_handlers = [h for h in handlers if isinstance(h, HandlerModule)]
            assert len(module_handlers) == 1
            assert module_handlers[0]._event_type == "test_event"
            assert module_handlers[0]._is_event_handler is True
        finally:
            # Clean up global
            del globals()["my_module_handler"]
    
    def test_register_handlers_from_discovery(self):
        """Test automatic registration of discovered handlers."""
        # Register handlers with our registry
        handlers = discover_handlers(globals(), self.registry, self.logger)
        
        # Check handler counts by event type
        test_event_handlers = self.registry.get_handlers("test_event")
        another_event_handlers = self.registry.get_handlers("another_test_event")
        
        # We expect:
        # - TestHandler class instantiated and registered
        # - async_function_handler wrapped in FunctionHandlerAdapter
        # - HandlerModule not registered (we didn't add to globals in this test)
        assert len(test_event_handlers) == 2
        
        # Check types (one instance of TestHandler and one FunctionHandlerAdapter)
        test_handler_types = {type(h).__name__ for h in test_event_handlers}
        assert "TestHandler" in test_handler_types
        assert "FunctionHandlerAdapter" in test_handler_types
        
        # We expect:
        # - sync_function_handler wrapped in FunctionHandlerAdapter
        assert len(another_event_handlers) == 1
        assert isinstance(another_event_handlers[0], FunctionHandlerAdapter)


class TestFunctionHandlerAdapter:
    """Tests for the FunctionHandlerAdapter."""
    
    @pytest.mark.asyncio
    async def test_async_function_adapter(self):
        """Test adapter with async function."""
        event = TestEvent("async_test")
        context = EventHandlerContext(event=event)
        
        adapter = FunctionHandlerAdapter(async_function_handler, "test_event")
        result = await adapter.handle(context)
        
        assert result.is_success
        assert result.value["function_handled"] is True
        assert result.value["event_id"] == "async_test"
    
    @pytest.mark.asyncio
    async def test_sync_function_adapter(self):
        """Test adapter with sync function."""
        event = AnotherTestEvent("sync_test")
        context = EventHandlerContext(event=event)
        
        adapter = FunctionHandlerAdapter(sync_function_handler, "another_test_event")
        result = await adapter.handle(context)
        
        assert result.is_success
        assert result.value["function_handled"] is True
        assert result.value["data"] == "sync_test"
    
    @pytest.mark.asyncio
    async def test_function_adapter_error_handling(self):
        """Test adapter handles errors properly."""
        # Define a function that raises an exception
        @function_handler(TestEvent)
        def error_function(_: EventHandlerContext) -> Result[None, Exception]:
            raise ValueError("Test error")
        
        event = TestEvent()
        context = EventHandlerContext(event=event)
        
        adapter = FunctionHandlerAdapter(error_function, "test_event")
        result = await adapter.handle(context)
        
        assert result.is_failure
        assert isinstance(result.error, ValueError)
        assert str(result.error) == "Test error"


class TestAsyncEventHandlerAdapter:
    """Tests for the AsyncEventHandlerAdapter."""
    
    @pytest.mark.asyncio
    async def test_async_handler_adapter(self):
        """Test adapter with async handlers."""
        handler = TestHandler()
        adapter = AsyncEventHandlerAdapter(handler)
        
        event = TestEvent()
        context = EventHandlerContext(event=event)
        
        result = await adapter.handle(context)
        
        assert result.is_success
        assert TestHandler.handler_called is True
    
    @pytest.mark.asyncio
    async def test_sync_handler_adapter(self):
        """Test adapter with sync handlers."""
        # Create a handler with sync handle method
        class SyncHandler(EventHandler):
            handler_called = False
            
            def handle(self, context: EventHandlerContext) -> Result[None, Exception]:
                SyncHandler.handler_called = True
                return Success(None)
        
        handler = SyncHandler()
        adapter = AsyncEventHandlerAdapter(handler)
        
        event = TestEvent()
        context = EventHandlerContext(event=event)
        
        result = await adapter.handle(context)
        
        assert result.is_success
        assert SyncHandler.handler_called is True


class TestEventHandlerDecorator:
    """Tests for the event handler decorators."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Reset registry
        EventHandlerDecorator.set_registry(None)
    
    def test_handles_decorator_class(self):
        """Test the handles decorator on classes."""
        registry = EventHandlerRegistry()
        EventHandlerDecorator.set_registry(registry)
        
        # Apply decorator
        @handles(TestEvent)
        class MyHandler(EventHandler):
            async def handle(self, context: EventHandlerContext) -> Result[None, Exception]:
                return Success(None)
        
        # Check class has the right attributes
        assert hasattr(MyHandler, "_event_type")
        assert MyHandler._event_type == "test_event"
        assert hasattr(MyHandler, "_is_event_handler")
        assert MyHandler._is_event_handler is True
        
        # Check handler was registered
        handlers = registry.get_handlers("test_event")
        assert len(handlers) == 1
        assert isinstance(handlers[0], MyHandler)
    
    def test_function_handler_decorator(self):
        """Test the function_handler decorator."""
        registry = EventHandlerRegistry()
        EventHandlerDecorator.set_registry(registry)
        
        # Apply decorator
        @function_handler(AnotherTestEvent)
        def my_handler(context: EventHandlerContext) -> Result[None, Exception]:
            return Success(None)
        
        # Check function has the right attributes
        assert hasattr(my_handler, "_event_type")
        assert my_handler._event_type == "another_test_event"
        assert hasattr(my_handler, "_is_event_handler")
        assert my_handler._is_event_handler is True
        
        # Check adapter was registered
        handlers = registry.get_handlers("another_test_event")
        assert len(handlers) == 1
        assert isinstance(handlers[0], FunctionHandlerAdapter)
        assert handlers[0].func == my_handler


@pytest.mark.asyncio
async def test_end_to_end_discovery_and_execution():
    """End to end test for discovery, registration, and execution."""
    # Create registry and discover handlers
    registry = EventHandlerRegistry()
    handlers = discover_handlers(globals(), registry)
    
    # Reset handler flags
    TestHandler.handler_called = False
    PlainHandler.handler_called = False
    
    # Create test events
    test_event = TestEvent("e2e_test")
    another_event = AnotherTestEvent("e2e_data")
    
    # Create contexts
    test_context = EventHandlerContext(event=test_event)
    another_context = EventHandlerContext(event=another_event)
    
    # Execute handlers for test_event
    results = []
    for handler in registry.get_handlers("test_event"):
        result = await handler.handle(test_context)
        results.append(result)
    
    # Check results
    assert len(results) == 2  # TestHandler and function_handler
    assert all(r.is_success for r in results)
    assert TestHandler.handler_called is True
    
    # One result should be from the function handler
    function_results = [r for r in results if hasattr(r.value, "get") and r.value.get("function_handled") is True]
    assert len(function_results) == 1
    assert function_results[0].value["event_id"] == "e2e_test"
