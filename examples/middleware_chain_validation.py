"""
Standalone validation script for the event middleware chain.

This script validates the middleware chain implementation without relying on the full
test framework, helping to confirm our middleware implementation works correctly.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict

from uno.core.errors.result import Failure, Result, Success
from uno.core.events.events import DomainEvent
from uno.core.events.handlers import (
    EventHandler,
    EventHandlerContext,
    EventHandlerMiddleware,
    MiddlewareChainBuilder,
)
from uno.core.events.middleware import (
    CircuitBreakerMiddleware,
    MetricsMiddleware,
    RetryMiddleware,
    RetryOptions,
)


# Simple test event for our examples
class TestEvent(DomainEvent):
    """Test event for middleware examples."""
    
    event_type = "test_standalone_event"
    
    def __init__(self, aggregate_id: str = "test-aggregate", event_id: str = "test-id"):
        super().__init__(aggregate_id=aggregate_id, event_id=event_id)


# Simple handlers for testing
class SuccessHandler(EventHandler):
    """Handler that always succeeds."""
    
    def __init__(self):
        self.call_count = 0
    
    async def handle(self, context: EventHandlerContext) -> Result[str, Exception]:
        """Handle the event successfully."""
        self.call_count += 1
        print(f"✅ [{time.time():.3f}] SuccessHandler called (count: {self.call_count})")
        return Success(f"success-{self.call_count}")


class FlakyHandler(EventHandler):
    """Handler that fails initially but succeeds after a few attempts."""
    
    def __init__(self, succeed_after: int = 2):
        self.call_count = 0
        self.succeed_after = succeed_after
    
    async def handle(self, context: EventHandlerContext) -> Result[str, Exception]:
        """Handle the event, failing initially."""
        self.call_count += 1
        
        if self.call_count <= self.succeed_after:
            print(f"❌ [{time.time():.3f}] FlakyHandler failed (attempt: {self.call_count}/{self.succeed_after+1})")
            return Failure(ValueError(f"Simulated failure {self.call_count}"))
        
        print(f"✅ [{time.time():.3f}] FlakyHandler succeeded after {self.call_count} attempts")
        return Success(f"success-after-{self.call_count}-attempts")


class FailureHandler(EventHandler):
    """Handler that always fails."""
    
    def __init__(self):
        self.call_count = 0
    
    async def handle(self, context: EventHandlerContext) -> Result[str, Exception]:
        """Handle the event with failure."""
        self.call_count += 1
        print(f"❌ [{time.time():.3f}] FailureHandler called (always fails) (count: {self.call_count})")
        return Failure(ValueError(f"Permanent failure {self.call_count}"))


class LoggingMiddleware(EventHandlerMiddleware):
    """Simple middleware that logs events as they pass through."""
    
    def __init__(self, name: str = "LoggingMiddleware"):
        self.name = name
        self.logs = []
    
    async def process(
        self, 
        context: EventHandlerContext, 
        next_middleware: callable[[EventHandlerContext], Result[Any, Exception]]
    ) -> Result[Any, Exception]:
        """Process the event and log it."""
        timestamp = time.time()
        entry = f"[{timestamp:.3f}] {self.name} pre-processing event {context.event.event_type}"
        print(entry)
        self.logs.append(entry)
        
        # Process through the middleware chain
        start_time = time.time()
        result = await next_middleware(context)
        duration = time.time() - start_time
        
        # Log the result
        status = "✅ success" if result.is_success else "❌ failure"
        timestamp = time.time()
        entry = f"[{timestamp:.3f}] {self.name} post-processing event {context.event.event_type} ({status}) in {duration:.3f}s"
        print(entry)
        self.logs.append(entry)
        
        return result


async def test_single_middleware():
    """Test a single middleware with a handler."""
    print("\n\n=== TEST: Single Middleware ===")
    
    # Create event and context
    event = TestEvent()
    context = EventHandlerContext(event=event)
    
    # Create handler and middleware
    handler = SuccessHandler()
    logging_middleware = LoggingMiddleware(name="TestLogger")
    
    # Build and execute the middleware chain
    chain_builder = MiddlewareChainBuilder(handler)
    processor = chain_builder.build_chain([logging_middleware])
    
    # Process the event
    result = await processor(context)
    
    # Verify result
    if result.is_success and result.value == "success-1" and len(logging_middleware.logs) == 2:
        print("✅ TEST PASSED: Single middleware test succeeded")
    else:
        print("❌ TEST FAILED: Single middleware test failed")
        
    print(f"Result: {result}")
    print(f"Handler call count: {handler.call_count}")
    print(f"Log count: {len(logging_middleware.logs)}")


async def test_retry_middleware():
    """Test retry middleware with a flaky handler."""
    print("\n\n=== TEST: Retry Middleware ===")
    
    # Create event and context
    event = TestEvent()
    context = EventHandlerContext(event=event)
    
    # Create a flaky handler that succeeds on the 3rd attempt
    handler = FlakyHandler(succeed_after=2)
    
    # Create retry middleware
    retry_options = RetryOptions(
        max_retries=3,               # Allow up to 3 retries
        base_delay_ms=100,           # Start with 100ms delay
        backoff_factor=2.0,          # Double the delay each time
        retryable_exceptions=[ValueError]  # Only retry ValueErrors
    )
    retry_middleware = RetryMiddleware(options=retry_options)
    
    # Add logging middleware to observe the process
    logging_middleware = LoggingMiddleware(name="RetryLogger")
    
    # Build the middleware chain with both middlewares
    chain_builder = MiddlewareChainBuilder(handler)
    processor = chain_builder.build_chain([logging_middleware, retry_middleware])
    
    # Process the event
    start_time = time.time()
    result = await processor(context)
    total_duration = time.time() - start_time
    
    # Verify result
    expected_result = "success-after-3-attempts"
    expected_call_count = 3  # Initial + 2 retries
    
    if result.is_success and result.value == expected_result and handler.call_count == expected_call_count:
        print(f"✅ TEST PASSED: Retry middleware test succeeded in {total_duration:.3f}s")
    else:
        print(f"❌ TEST FAILED: Retry middleware test failed")
        
    print(f"Result: {result}")
    print(f"Handler call count: {handler.call_count} (expected: {expected_call_count})")
    print(f"Log entries: {len(logging_middleware.logs)} (expected: 2)")
    print(f"Total duration: {total_duration:.3f}s")


async def test_circuit_breaker():
    """Test circuit breaker middleware with a failing handler."""
    print("\n\n=== TEST: Circuit Breaker Middleware ===")
    
    # Create event and context
    event = TestEvent()
    context = EventHandlerContext(event=event)
    
    # Create a handler that always fails
    handler = FailureHandler()
    
    # Create circuit breaker middleware
    circuit_breaker = CircuitBreakerMiddleware(
        failure_threshold=2,         # Open after 2 failures
        reset_timeout_seconds=2.0,   # Wait 2 seconds before trying again
        half_open_success_threshold=1  # Close after 1 success in half-open state
    )
    
    # Add logging middleware to observe the process
    logging_middleware = LoggingMiddleware(name="CircuitLogger")
    
    # Build the middleware chain
    chain_builder = MiddlewareChainBuilder(handler)
    processor = chain_builder.build_chain([logging_middleware, circuit_breaker])
    
    # First call - should reach the handler and fail
    print("\n> First call - should fail but circuit remains closed")
    result1 = await processor(context)
    print(f"Circuit state: {circuit_breaker.circuit_state.get(event.event_type, 'unknown')}")
    
    # Second call - should reach the handler and fail again
    print("\n> Second call - should fail and open the circuit")
    result2 = await processor(context)
    print(f"Circuit state: {circuit_breaker.circuit_state.get(event.event_type, 'unknown')}")
    
    # Third call - circuit should be open, so handler not called
    print("\n> Third call - circuit open, should fail quickly without calling handler")
    handler.call_count = 0  # Reset to verify
    result3 = await processor(context)
    print(f"Handler was called: {handler.call_count > 0}")
    print(f"Circuit state: {circuit_breaker.circuit_state.get(event.event_type, 'unknown')}")
    
    # Wait for reset timeout
    print("\n> Waiting for circuit to transition to half-open...")
    await asyncio.sleep(2.5)  # Slightly longer than reset timeout
    print(f"Circuit state: {circuit_breaker.circuit_state.get(event.event_type, 'unknown')}")
    
    # Fourth call - circuit half-open, should try handler again
    print("\n> Fourth call - circuit half-open, should try handler again")
    handler.call_count = 0  # Reset to verify
    result4 = await processor(context)
    print(f"Handler was called: {handler.call_count > 0}")
    print(f"Circuit state: {circuit_breaker.circuit_state.get(event.event_type, 'unknown')}")
    
    # Verify test results
    expected_circuit_state = "open"  # After the 4th call, should still be open
    if (not result1.is_success and 
        not result2.is_success and 
        not result3.is_success and 
        not result4.is_success and
        circuit_breaker.circuit_state.get(event.event_type) == expected_circuit_state):
        print("\n✅ TEST PASSED: Circuit breaker middleware test succeeded")
    else:
        print("\n❌ TEST FAILED: Circuit breaker middleware test failed")
    
    print(f"Results: fail={not result1.is_success}, fail={not result2.is_success}, " +
          f"fail={not result3.is_success}, fail={not result4.is_success}")
    print(f"Final circuit state: {circuit_breaker.circuit_state.get(event.event_type)}")


async def test_metrics_middleware():
    """Test metrics middleware."""
    print("\n\n=== TEST: Metrics Middleware ===")
    
    # Create event and context
    event = TestEvent()
    context = EventHandlerContext(event=event)
    
    # Create handlers
    success_handler = SuccessHandler()
    failure_handler = FailureHandler()
    
    # Create metrics middleware
    metrics_middleware = MetricsMiddleware(report_interval_seconds=60)  # Long interval to avoid auto-reporting
    
    # Test with success handler
    print("\n> Testing with success handler")
    success_chain = MiddlewareChainBuilder(success_handler)
    success_processor = success_chain.build_chain([metrics_middleware])
    await success_processor(context)
    
    # Test with failure handler
    print("\n> Testing with failure handler")
    failure_chain = MiddlewareChainBuilder(failure_handler)
    failure_processor = failure_chain.build_chain([metrics_middleware])
    await failure_processor(context)
    
    # Get metrics for the event type
    metrics = metrics_middleware.metrics.get(event.event_type)
    
    # Print metrics
    if metrics:
        print("\nMetrics for event type:", event.event_type)
        print(f"  Total count: {metrics.count}")
        print(f"  Success count: {metrics.success_count}")
        print(f"  Failure count: {metrics.failure_count}")
        print(f"  Success rate: {metrics.success_rate:.2f}%")
        print(f"  Min duration: {metrics.min_duration_ms:.2f}ms")
        print(f"  Max duration: {metrics.max_duration_ms:.2f}ms")
        print(f"  Avg duration: {metrics.average_duration_ms:.2f}ms")
        
        # Verify test results
        if (metrics.count == 2 and 
            metrics.success_count == 1 and 
            metrics.failure_count == 1 and 
            abs(metrics.success_rate - 50.0) < 0.1):  # Should be ~50%
            print("\n✅ TEST PASSED: Metrics middleware test succeeded")
        else:
            print("\n❌ TEST FAILED: Metrics middleware test failed")
    else:
        print("\n❌ TEST FAILED: No metrics found for event type:", event.event_type)


async def test_combined_middleware():
    """Test all middleware components working together."""
    print("\n\n=== TEST: Combined Middleware Stack ===")
    
    # Create event and context
    event = TestEvent()
    context = EventHandlerContext(event=event)
    
    # Create a flaky handler
    handler = FlakyHandler(succeed_after=1)  # Succeed on the 2nd attempt
    
    # Create all middleware components
    logging_middleware = LoggingMiddleware(name="OuterLogger")
    metrics_middleware = MetricsMiddleware()
    retry_middleware = RetryMiddleware(options=RetryOptions(
        max_retries=3,
        base_delay_ms=50,
        backoff_factor=1.5
    ))
    circuit_breaker = CircuitBreakerMiddleware(
        failure_threshold=5,  # Set high to not interfere with test
        reset_timeout_seconds=1.0
    )
    
    # Build the middleware chain - order matters!
    chain_builder = MiddlewareChainBuilder(handler)
    processor = chain_builder.build_chain([
        logging_middleware,   # Outermost - logs everything
        metrics_middleware,   # Records overall metrics
        circuit_breaker,      # Prevents cascading failures
        retry_middleware      # Innermost - retries the handler
    ])
    
    # Process the event
    start_time = time.time()
    result = await processor(context)
    total_duration = time.time() - start_time
    
    # Verify result
    expected_result = "success-after-2-attempts"
    expected_call_count = 2  # Initial + 1 retry to succeed
    
    if result.is_success and result.value == expected_result and handler.call_count == expected_call_count:
        print(f"✅ TEST PASSED: Combined middleware test succeeded in {total_duration:.3f}s")
    else:
        print(f"❌ TEST FAILED: Combined middleware test failed")
        
    # Print details
    print(f"Result: {result}")
    print(f"Handler call count: {handler.call_count} (expected: {expected_call_count})")
    print(f"Log entries: {len(logging_middleware.logs)} (expected: 2)")
    
    # Print metrics
    metrics = metrics_middleware.metrics.get(event.event_type)
    if metrics:
        print("\nMetrics:")
        print(f"  Count: {metrics.count} (expected: 1)")
        print(f"  Success: {metrics.success_count} (expected: 1)")
        print(f"  Failure: {metrics.failure_count} (expected: 0)")
        print(f"  Success rate: {metrics.success_rate:.2f}% (expected: 100%)")
    else:
        print("No metrics found!")


async def main():
    """Run all middleware tests."""
    print("\n" + "=" * 80)
    print("UNO MIDDLEWARE VALIDATION SCRIPT")
    print("=" * 80)
    
    # Run individual tests
    await test_single_middleware()
    await test_retry_middleware()
    await test_circuit_breaker()
    await test_metrics_middleware()
    await test_combined_middleware()
    
    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
