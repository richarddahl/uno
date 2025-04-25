"""
A minimal standalone script to verify async patterns for event handlers.

This script is completely isolated from the main codebase to avoid import issues.
"""

import asyncio
import inspect
from typing import Any, Callable, Dict, Generic, TypeVar

# Define basic type variables
T = TypeVar('T')
E = TypeVar('E', bound=Exception)


# Minimal implementation of Result
class Result(Generic[T, E]):
    """A simplified Result type similar to uno.core.errors.result."""
    
    def __init__(self, value: T = None, error: E = None):
        self.value = value
        self.error = error
        self._is_success = error is None
    
    @property
    def is_success(self) -> bool:
        return self._is_success


def Success(value: T = None) -> Result[T, Any]:
    """Create a successful result."""
    return Result(value=value)


def Failure(error: E) -> Result[Any, E]:
    """Create a failed result."""
    return Result(error=error)


# Simplified EventHandlerContext
class EventHandlerContext:
    """A simplified event handler context."""
    
    def __init__(self, event: Any, metadata: Dict[str, Any] = None, extra: Dict[str, Any] = None):
        self.event = event
        self.metadata = metadata or {}
        self.extra = extra or {}


# Handler protocol
class EventHandler:
    """Base class for event handlers."""
    
    def handle(self, context: EventHandlerContext) -> Result[Any, Exception]:
        """Handle an event."""
        raise NotImplementedError("Subclasses must implement handle method")


# Function to check if a callable is async
def is_async_callable(callable_obj: Callable) -> bool:
    """Check if a callable is asynchronous."""
    if callable_obj is None:
        return False
    
    if inspect.iscoroutinefunction(callable_obj):
        return True
    
    # Handle decorated functions and methods
    if hasattr(callable_obj, "__func__") and inspect.iscoroutinefunction(callable_obj.__func__):
        return True
    
    return False


# AsyncEventHandlerAdapter
class AsyncEventHandlerAdapter:
    """Adapter to ensure consistent async handling for both sync and async handlers."""
    
    def __init__(self, handler: EventHandler):
        self.handler = handler
        self._is_async = is_async_callable(handler.handle)
    
    async def handle(self, context: EventHandlerContext) -> Result[Any, Exception]:
        """Handle an event asynchronously."""
        try:
            if self._is_async:
                return await self.handler.handle(context)
            else:
                return self.handler.handle(context)
        except Exception as ex:
            return Failure(ex)


# Test event class
class TestEvent:
    """Simple event for testing."""
    
    def __init__(self, data: str = "test_data"):
        self.data = data


# Test implementations
class AsyncHandler(EventHandler):
    """Test async handler."""
    
    async def handle(self, context: EventHandlerContext) -> Result[Dict[str, Any], Exception]:
        """Handle an event asynchronously."""
        print(f"AsyncHandler processing event with data: {context.event.data}")
        return Success({"handler_type": "async", "processed": True})


class SyncHandler(EventHandler):
    """Test sync handler."""
    
    def handle(self, context: EventHandlerContext) -> Result[Dict[str, Any], Exception]:
        """Handle an event synchronously."""
        print(f"SyncHandler processing event with data: {context.event.data}")
        return Success({"handler_type": "sync", "processed": True})


# Test functions
async def test_async_handler():
    """Test that async handlers work with the adapter."""
    handler = AsyncHandler()
    adapter = AsyncEventHandlerAdapter(handler)
    event = TestEvent("async_test")
    context = EventHandlerContext(event=event)
    
    print("\nTesting async handler...")
    result = await adapter.handle(context)
    
    print(f"  Is success: {result.is_success}")
    print(f"  Value: {result.value}")
    
    return result.is_success and result.value.get("processed", False)


async def test_sync_handler():
    """Test that sync handlers work with the adapter."""
    handler = SyncHandler()
    adapter = AsyncEventHandlerAdapter(handler)
    event = TestEvent("sync_test")
    context = EventHandlerContext(event=event)
    
    print("\nTesting sync handler...")
    result = await adapter.handle(context)
    
    print(f"  Is success: {result.is_success}")
    print(f"  Value: {result.value}")
    
    return result.is_success and result.value.get("processed", False)


async def test_is_async_callable_utility():
    """Test the is_async_callable utility function."""
    print("\nTesting is_async_callable utility...")
    
    # Define test functions and methods
    async def async_func():
        pass
    
    def sync_func():
        pass
    
    class TestClass:
        async def async_method(self):
            pass
        
        def sync_method(self):
            pass
    
    instance = TestClass()
    
    # Test them
    results = {
        "async_func": is_async_callable(async_func),
        "sync_func": is_async_callable(sync_func),
        "async_method": is_async_callable(instance.async_method),
        "sync_method": is_async_callable(instance.sync_method),
    }
    
    for name, result in results.items():
        print(f"  {name}: {result}")
    
    return all([
        results["async_func"] is True,
        results["sync_func"] is False,
        results["async_method"] is True,
        results["sync_method"] is False,
    ])


async def run_all_tests():
    """Run all tests and return overall result."""
    print("Starting minimal async pattern tests...\n")
    
    async_handler_test = await test_async_handler()
    sync_handler_test = await test_sync_handler()
    is_async_test = await test_is_async_callable_utility()
    
    # Aggregate results
    all_passed = async_handler_test and sync_handler_test and is_async_test
    
    print("\nTest Results:")
    print(f"  Async handler test: {'PASSED' if async_handler_test else 'FAILED'}")
    print(f"  Sync handler test: {'PASSED' if sync_handler_test else 'FAILED'}")
    print(f"  is_async_callable test: {'PASSED' if is_async_test else 'FAILED'}")
    print(f"\nOverall: {'PASSED' if all_passed else 'FAILED'}")
    
    return all_passed


if __name__ == "__main__":
    # Run the tests
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(run_all_tests())
    
    # Exit with appropriate code
    import sys
    sys.exit(0 if result else 1)
