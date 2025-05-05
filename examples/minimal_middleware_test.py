"""
Minimal test script for middleware chain without dependencies.
This avoids circular imports by implementing the bare minimum needed.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

# Define basic types to avoid framework dependencies
T = TypeVar("T")
E = TypeVar("E", bound=Exception)


# Simple Result monad implementation for testing
class Result(Generic[T, E]):
    """Simple result monad to replace the framework version."""

    @property
    def is_success(self) -> bool:
        raise NotImplementedError

    @property
    def is_failure(self) -> bool:
        return not self.is_success


class Success(Result[T, E]):
    """Success result with a value."""

    def __init__(self, value: T):
        self.value = value

    @property
    def is_success(self) -> bool:
        return True


class Failure(Result[T, E]):
    """Failure result with an error."""

    def __init__(self, error: E):
        self.error = error

    @property
    def is_success(self) -> bool:
        return False


# Simple domain event
class DomainEvent:
    """Base domain event class."""

    event_type: str = "base_event"

    def __init__(self, aggregate_id: str = "test", event_id: str = "test-id"):
        self.aggregate_id = aggregate_id
        self.event_id = event_id


# Context for event handlers
@dataclass
class EventHandlerContext:
    """Context passed to event handlers."""

    event: DomainEvent
    metadata: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


# Event handler interface
class EventHandler(ABC):
    """Base event handler interface."""

    @abstractmethod
    async def handle(self, context: EventHandlerContext) -> Result[Any, Exception]:
        """Handle an event."""
        pass


# Middleware interface
class EventHandlerMiddleware(ABC):
    """Base middleware interface."""

    @abstractmethod
    async def process(
        self,
        context: EventHandlerContext,
        next_middleware: Callable[[EventHandlerContext], Result[Any, Exception]],
    ) -> Result[Any, Exception]:
        """Process an event through this middleware."""
        pass


# Middleware chain builder
class MiddlewareChainBuilder:
    """Helper class to build middleware chains without closure issues."""

    def __init__(self, handler: EventHandler):
        """Initialize with the handler that will process events."""
        self.handler = handler

    async def execute_direct(self, ctx: EventHandlerContext) -> Result[Any, Exception]:
        """Execute the handler directly without middleware."""
        return await self.handler.handle(ctx)

    def build_chain(
        self, middleware_list: list[EventHandlerMiddleware]
    ) -> Callable[[EventHandlerContext], Result[Any, Exception]]:
        """Build a middleware chain from a list of middleware components."""
        if not middleware_list:
            return self.execute_direct

        # Create a list of middleware processors in reverse order
        # The last middleware in the chain will call the handler
        processors = []

        async def final_processor(ctx: EventHandlerContext) -> Result[Any, Exception]:
            return await self.execute_direct(ctx)

        processors.append(final_processor)

        # Build the chain from inside out
        for middleware in reversed(middleware_list):
            # Create a processor for this middleware
            # Each processor captures its specific middleware and the next processor
            m = middleware  # Capture current middleware
            next_p = processors[-1]  # Get the previously added processor

            async def process(
                ctx: EventHandlerContext, middleware=m, next_processor=next_p
            ) -> Result[Any, Exception]:
                return await middleware.process(ctx, next_processor)

            processors.append(process)

        # Return the outermost processor (the last one we added)
        return processors[-1]


# Example middleware implementations
class RetryMiddleware(EventHandlerMiddleware):
    """Middleware that retries failed operations."""

    def __init__(self, max_retries: int = 3, delay_ms: int = 100):
        self.max_retries = max_retries
        self.delay_ms = delay_ms

    async def process(
        self,
        context: EventHandlerContext,
        next_middleware: Callable[[EventHandlerContext], Result[Any, Exception]],
    ) -> Result[Any, Exception]:
        """Process with retries on failure."""
        attempt = 0
        while True:
            attempt += 1
            result = await next_middleware(context)

            if result.is_success or attempt > self.max_retries:
                return result

            # Wait before retrying
            delay_seconds = self.delay_ms / 1000
            print(
                f"Retry attempt {attempt}/{self.max_retries} after {delay_seconds}s delay"
            )
            await asyncio.sleep(delay_seconds)


class LoggingMiddleware(EventHandlerMiddleware):
    """Middleware that logs handler execution."""

    def __init__(self, name: str = "Logger"):
        self.name = name

    async def process(
        self,
        context: EventHandlerContext,
        next_middleware: Callable[[EventHandlerContext], Result[Any, Exception]],
    ) -> Result[Any, Exception]:
        """Log before and after processing."""
        print(f"[{self.name}] Processing event: {context.event.event_type}")

        start_time = time.time()
        result = await next_middleware(context)
        duration = time.time() - start_time

        status = "SUCCESS" if result.is_success else "FAILURE"
        print(f"[{self.name}] Result: {status} (took {duration:.3f}s)")

        return result


# Test event and handlers
class TestEvent(DomainEvent):
    """Test event."""

    event_type = "test_event"


class SuccessHandler(EventHandler):
    """Always succeeds."""

    async def handle(self, context: EventHandlerContext) -> Result[str, Exception]:
        """Handle successfully."""
        return Success("Success result")


# Constants for retry logic
FAIL_ATTEMPTS = 2


class FlakyHandler(EventHandler):
    """Fails on first attempts."""

    def __init__(self):
        self.attempts = 0

    async def handle(self, context: EventHandlerContext) -> Result[str, Exception]:
        """Fail initially then succeed."""
        self.attempts += 1
        if self.attempts <= FAIL_ATTEMPTS:
            print(f"Failing on attempt {self.attempts}")
            return Failure(ValueError(f"Simulated failure on attempt {self.attempts}"))
        print(f"Succeeding on attempt {self.attempts}")
        return Success(f"Success after {self.attempts} attempts")


# Main test function
async def main():
    """Run tests for middleware chain."""
    print("\n===== MIDDLEWARE CHAIN TEST =====")

    # Create test event and context
    event = TestEvent()
    context = EventHandlerContext(event=event)

    # Test 1: Simple success
    print("\n--- Test 1: Simple Success ---")
    success_handler = SuccessHandler()
    logging_middleware = LoggingMiddleware("Test1Logger")

    chain_builder = MiddlewareChainBuilder(success_handler)
    chain = chain_builder.build_chain([logging_middleware])

    result = await chain(context)
    print(f"Test 1 result: {'Success' if result.is_success else 'Failure'}")

    # Test 2: Retry middleware with flaky handler
    print("\n--- Test 2: Retry Middleware ---")
    flaky_handler = FlakyHandler()
    retry_middleware = RetryMiddleware(max_retries=3, delay_ms=100)
    logging_middleware = LoggingMiddleware("Test2Logger")

    chain_builder = MiddlewareChainBuilder(flaky_handler)
    chain = chain_builder.build_chain([logging_middleware, retry_middleware])

    result = await chain(context)
    print(f"Test 2 result: {'Success' if result.is_success else 'Failure'}")
    print(f"Attempts required: {flaky_handler.attempts}")

    print("\n===== TESTS COMPLETE =====")


if __name__ == "__main__":
    asyncio.run(main())
