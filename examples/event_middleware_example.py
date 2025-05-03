"""
Example demonstrating the use of event handler middleware.

This example shows how to configure and use the various middleware
components for event handlers:
- RetryMiddleware: For automatic retrying of failed event handlers
- CircuitBreakerMiddleware: For preventing cascading failures
- MetricsMiddleware: For collecting performance metrics

This is a simplified example that doesn't require the full domain model
to be implemented.
"""

import asyncio
import logging
from dataclasses import dataclass

from uno.core.errors.result import Failure, Success
from uno.core.events.events import DomainEvent
from uno.core.events.handlers import (
    EventHandlerContext,
    EventHandler,
    EventHandlerRegistry,
    LoggingMiddleware,
    TimingMiddleware,
)
from uno.core.events.middleware import (
    CircuitBreakerMiddleware,
    CircuitBreakerState,
    MetricsMiddleware,
    RetryMiddleware,
    RetryOptions,
)
from uno.infrastructure.logging.logger import LoggerService


# Setup basic logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@dataclass
class UserCreatedEvent(DomainEvent):
    """Event representing a user being created."""

    event_type = "user.created"
    username: str
    email: str


@dataclass
class OrderPlacedEvent(DomainEvent):
    """Event representing an order being placed."""

    event_type = "order.placed"
    order_id: str
    user_id: str
    total_amount: float


class EmailNotificationHandler(EventHandler):
    """Handler that sends email notifications for events."""

    def __init__(self, fail_rate: float = 0.0):
        """
        Initialize the handler.

        Args:
            fail_rate: Rate at which the handler should simulate failure (0.0-1.0)
        """
        self.logger = LoggerService(name="notifications.email")
        self.fail_rate = fail_rate
        self.call_count = 0

    async def handle(self, context: EventHandlerContext) -> Success | Failure:
        """
        Handle the event by sending an email notification.

        Args:
            context: The event handler context

        Returns:
            Success or Failure
        """
        event = context.event
        self.call_count += 1

        # Simulate occasional failures if requested
        if self.fail_rate > 0.0 and self.call_count % int(1 / self.fail_rate) == 0:
            self.logger.structured_log(
                "ERROR",
                f"Failed to send email notification for event {event.event_type}",
                name="notifications.email",
                event_id=event.event_id,
            )
            return Failure(Exception("Email service unavailable"))

        # Simulate processing delay
        await asyncio.sleep(0.05)

        if isinstance(event, UserCreatedEvent):
            self.logger.structured_log(
                "INFO",
                f"Sent welcome email to {event.username} ({event.email})",
                name="notifications.email",
                event_id=event.event_id,
            )
        elif isinstance(event, OrderPlacedEvent):
            self.logger.structured_log(
                "INFO",
                f"Sent order confirmation email for order {event.order_id}",
                name="notifications.email",
                event_id=event.event_id,
            )

        return Success("Email sent")


class SlowExternalServiceHandler(EventHandler):
    """Handler that integrates with an external service."""

    def __init__(self, service_name: str, delay_seconds: float = 0.1):
        """
        Initialize the handler.

        Args:
            service_name: Name of the external service
            delay_seconds: Simulated delay for the service call
        """
        self.logger = LoggerService(name=f"integrations.{service_name}")
        self.service_name = service_name
        self.delay_seconds = delay_seconds

    async def handle(self, context: EventHandlerContext) -> Success | Failure:
        """
        Handle the event by calling an external service.

        Args:
            context: The event handler context

        Returns:
            Success or Failure
        """
        event = context.event

        # Simulate an external service call with delay
        await asyncio.sleep(self.delay_seconds)

        self.logger.structured_log(
            "INFO",
            f"Processed event {event.event_type} with {self.service_name}",
            name=f"integrations.{self.service_name}",
            event_id=event.event_id,
        )

        return Success(f"Processed with {self.service_name}")


async def process_event(registry: EventHandlerRegistry, event: DomainEvent) -> None:
    """
    Process an event with all registered handlers.

    Args:
        registry: The event handler registry
        event: The event to process
    """
    context = EventHandlerContext(event=event)

    # Get handlers for this event type
    handlers = registry.get_handlers(event.event_type)
    if not handlers:
        print(f"No handlers registered for event type {event.event_type}")
        return

    # Process with each handler
    for handler in handlers:
        # Build middleware chain
        middleware = registry.get_middleware()

        # Start with the handler
        async def execute_handler(ctx: EventHandlerContext):
            return await handler.handle(ctx)

        # Build the middleware chain in reverse order
        next_middleware = execute_handler
        for mw in reversed(middleware):
            current_mw = mw
            prev_next = next_middleware

            # Create closure to preserve the current middleware and next function
            async def chain_middleware(
                ctx: EventHandlerContext, mw=current_mw, next_fn=prev_next
            ):
                return await mw.process(ctx, next_fn)

            next_middleware = chain_middleware

        # Execute the middleware chain
        result = await next_middleware(context)

        if result.is_failure:
            print(f"Handler {handler.__class__.__name__} failed: {result.error}")
        else:
            print(f"Handler {handler.__class__.__name__} succeeded: {result.value}")


async def main() -> None:
    """Run the example."""
    # Create event handler registry
    registry = EventHandlerRegistry()

    # Register middleware
    # Order matters - middleware is executed in the order registered

    # Timing middleware - records execution time
    registry.register_middleware(TimingMiddleware())

    # Logging middleware - logs events and results
    registry.register_middleware(LoggingMiddleware())

    # Metrics middleware - collects metrics about event handler performance
    registry.register_middleware(MetricsMiddleware(report_interval_seconds=5.0))

    # Retry middleware - automatically retries failed handlers
    retry_options = RetryOptions(max_retries=3, base_delay_ms=100, backoff_factor=2.0)
    registry.register_middleware(RetryMiddleware(options=retry_options))

    # Circuit breaker middleware - prevents cascading failures
    circuit_options = CircuitBreakerState(
        failure_threshold=5, recovery_timeout_seconds=10.0, success_threshold=2
    )
    registry.register_middleware(CircuitBreakerMiddleware(options=circuit_options))

    # Register event handlers
    registry.register_handler("user.created", EmailNotificationHandler())
    registry.register_handler("order.placed", EmailNotificationHandler(fail_rate=0.3))
    registry.register_handler("user.created", SlowExternalServiceHandler("analytics"))
    registry.register_handler(
        "order.placed", SlowExternalServiceHandler("shipping", delay_seconds=0.2)
    )

    # Process some events
    print("\n--- Processing User Created Events ---")
    for i in range(3):
        event = UserCreatedEvent(
            aggregate_id=f"user-{i}",
            event_id=f"evt-{i}",
            username=f"user{i}",
            email=f"user{i}@example.com",
        )
        print(f"\nProcessing event: {event.event_type} (ID: {event.event_id})")
        await process_event(registry, event)

    print("\n--- Processing Order Placed Events (with occasional failures) ---")
    for i in range(10):
        event = OrderPlacedEvent(
            aggregate_id=f"order-{i}",
            event_id=f"evt-order-{i}",
            order_id=f"ord{i}",
            user_id=f"user-{i % 3}",
            total_amount=99.99 + i,
        )
        print(f"\nProcessing event: {event.event_type} (ID: {event.event_id})")
        await process_event(registry, event)

        # Add small delay between events
        await asyncio.sleep(0.1)

    # Wait to see metrics report (happens every 5 seconds)
    print("\nWaiting for metrics report...")
    await asyncio.sleep(6)


if __name__ == "__main__":
    asyncio.run(main())
