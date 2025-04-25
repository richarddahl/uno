"""
A standalone script to verify our async patterns implementation for event handlers.

This script doesn't depend on the full test suite and avoids circular imports.
"""

import asyncio
import sys
from typing import Any, Dict

from uno.core.errors.result import Result, Success
from uno.core.events.async_utils import AsyncEventHandlerAdapter, is_async_callable
from uno.core.events.context import EventHandlerContext
from uno.core.events.handlers import EventHandler


class TestEvent:
    """Simple event class for testing."""
    event_type: str = "test_event"
    data: str
    
    def __init__(self, data: str = "test_data"):
        self.data = data


async def test_async_handler_adapter():
    """Test the AsyncEventHandlerAdapter with both sync and async handlers."""
    results = {}
    
    # Test with async handler
    class AsyncTestHandler(EventHandler):
        was_called = False
        
        async def handle(self, context: EventHandlerContext) -> Result[Dict[str, Any], Exception]:
            AsyncTestHandler.was_called = True
            return Success({"handler_type": "async", "data": context.event.data})
    
    # Test with sync handler
    class SyncTestHandler(EventHandler):
        was_called = False
        
        def handle(self, context: EventHandlerContext) -> Result[Dict[str, Any], Exception]:
            SyncTestHandler.was_called = True
            return Success({"handler_type": "sync", "data": context.event.data})
    
    # Create handlers and adapters
    async_handler = AsyncTestHandler()
    sync_handler = SyncTestHandler()
    async_adapter = AsyncEventHandlerAdapter(async_handler)
    sync_adapter = AsyncEventHandlerAdapter(sync_handler)
    
    # Create event and context
    event = TestEvent("test_data")
    context = EventHandlerContext(event=event)
    
    # Test async handler
    async_result = await async_adapter.handle(context)
    results["async_result"] = async_result.is_success
    results["async_called"] = AsyncTestHandler.was_called
    results["async_value"] = async_result.value if async_result.is_success else None
    
    # Test sync handler
    sync_result = await sync_adapter.handle(context)
    results["sync_result"] = sync_result.is_success
    results["sync_called"] = SyncTestHandler.was_called
    results["sync_value"] = sync_result.value if sync_result.is_success else None
    
    return results


async def test_is_async_callable():
    """Test the is_async_callable utility."""
    results = {}
    
    # Define async function
    async def async_func():
        return "async"
    
    # Define sync function
    def sync_func():
        return "sync"
    
    # Test both
    results["async_func"] = is_async_callable(async_func)
    results["sync_func"] = is_async_callable(sync_func)
    
    # Test methods
    class TestClass:
        async def async_method(self):
            return "async_method"
            
        def sync_method(self):
            return "sync_method"
    
    test_obj = TestClass()
    results["async_method"] = is_async_callable(test_obj.async_method)
    results["sync_method"] = is_async_callable(test_obj.sync_method)
    
    return results


async def run_tests():
    """Run all tests and return results."""
    results = {}
    
    print("Testing AsyncEventHandlerAdapter...")
    adapter_results = await test_async_handler_adapter()
    for key, value in adapter_results.items():
        print(f"  {key}: {value}")
    results["adapter_test"] = adapter_results
    
    print("\nTesting is_async_callable utility...")
    callable_results = await test_is_async_callable()
    for key, value in callable_results.items():
        print(f"  {key}: {value}")
    results["callable_test"] = callable_results
    
    return results


if __name__ == "__main__":
    print("Starting async pattern verification tests...\n")
    loop = asyncio.get_event_loop()
    test_results = loop.run_until_complete(run_tests())
    
    # Determine if all tests passed
    adapter_test = test_results["adapter_test"]
    callable_test = test_results["callable_test"]
    
    all_passed = (
        adapter_test["async_result"] and
        adapter_test["sync_result"] and
        adapter_test["async_called"] and
        adapter_test["sync_called"] and
        callable_test["async_func"] and
        not callable_test["sync_func"] and
        callable_test["async_method"] and
        not callable_test["sync_method"]
    )
    
    print("\nTest Summary:")
    print(f"All tests passed: {all_passed}")
    
    # Exit with appropriate status code
    sys.exit(0 if all_passed else 1)
