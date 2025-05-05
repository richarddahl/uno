"""
Example of configuring and using event middleware with dependency injection.

This example demonstrates:
1. Registering middleware services in the DI container
2. Configuring middleware with custom options
3. Using middleware in an application
"""

import asyncio
import logging
from dataclasses import dataclass

from uno.infrastructure.di.service_collection import ServiceCollection, ServiceProvider
from uno.infrastructure.di.middleware import configure_event_middleware
from uno.core.errors.result import Failure, Result, Success
from uno.core.events.events import DomainEvent
from uno.core.events.handlers import (
    EventHandler,
    EventHandlerContext,
    EventHandlerRegistry,
)
from uno.core.events.middleware import CircuitBreakerOptions, RetryOptions
from uno.infrastructure.logging.factory import LoggerServiceFactory
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig


# Sample domain events
class OrderCreatedEvent(DomainEvent):
    """Event representing a new order being created."""

    event_type = "order_created"

    def __init__(self, order_id: str, customer_id: str, total_amount: float):
        super().__init__(aggregate_id=order_id)
        self.order_id = order_id
        self.customer_id = customer_id
        self.total_amount = total_amount


class PaymentProcessedEvent(DomainEvent):
    """Event representing a payment being processed."""

    event_type = "payment_processed"

    def __init__(self, payment_id: str, order_id: str, amount: float, successful: bool):
        super().__init__(aggregate_id=payment_id)
        self.payment_id = payment_id
        self.order_id = order_id
        self.amount = amount
        self.successful = successful


# Sample event handlers
class OrderCreatedHandler(EventHandler):
    """Handler for order created events."""

    def __init__(self, logger: LoggerService):
        self.logger = logger
        self.failures = 0  # For testing retry

    async def handle(self, context: EventHandlerContext) -> Result[str, Exception]:
        """Handle order created event."""
        event = context.event
        if not isinstance(event, OrderCreatedEvent):
            return Failure(
                ValueError(f"Expected OrderCreatedEvent, got {type(event).__name__}")
            )

        # Constants for failure simulation
        max_failures = 2

        # Simulate occasional failure for testing retry middleware
        self.failures += 1
        if self.failures <= max_failures:
            self.logger.info(
                f"Simulating failure in OrderCreatedHandler (attempt {self.failures})"
            )
            return Failure(RuntimeError("Simulated temporary failure"))

        self.logger.info(
            f"Processing order {event.order_id} for customer {event.customer_id}"
        )
        # Process order logic would go here
        return Success(f"Order {event.order_id} processed successfully")


class PaymentProcessedHandler(EventHandler):
    """Handler for payment processed events."""

    def __init__(self, logger: LoggerService):
        self.logger = logger
        self.processed_count = 0

    async def handle(self, context: EventHandlerContext) -> Result[str, Exception]:
        """Handle payment processed event."""
        event = context.event
        if not isinstance(event, PaymentProcessedEvent):
            return Failure(
                ValueError(
                    f"Expected PaymentProcessedEvent, got {type(event).__name__}"
                )
            )

        self.processed_count += 1
        self.logger.info(
            f"Processing payment {event.payment_id} for order {event.order_id} "
            f"(amount: ${event.amount:.2f}, successful: {event.successful})"
        )

        # Business logic for payment processing would go here
        if not event.successful:
            return Failure(RuntimeError(f"Payment {event.payment_id} failed"))

        return Success(f"Payment {event.payment_id} processed successfully")


# Application setup
@dataclass
class Application:
    """Sample application that uses event middleware."""

    service_provider: ServiceProvider
    registry: EventHandlerRegistry
    logger: LoggerService

    @classmethod
    async def create(cls) -> "Application":
        """Create and configure the application."""
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        logger_factory = LoggerServiceFactory()
        logger = logger_factory("app")

        # Create service collection
        services = ServiceCollection()

        # Register logger factory
        services.add_singleton(
            LoggerServiceFactory, implementation=LoggerServiceFactory
        )

        # Register custom loggers
        services.add_singleton(
            LoggerService,
            factory=lambda p: logger_factory("order_handler"),
            name="order_handler",
        )
        services.add_singleton(
            LoggerService,
            factory=lambda p: logger_factory("payment_handler"),
            name="payment_handler",
        )

        # Register handlers
        order_handler = OrderCreatedHandler(logger_factory("order_handler"))
        payment_handler = PaymentProcessedHandler(logger_factory("payment_handler"))
        services.add_instance(OrderCreatedHandler, order_handler)
        services.add_instance(PaymentProcessedHandler, payment_handler)

        # Create handler registry
        registry = EventHandlerRegistry(logger_factory=logger_factory)
        registry.register_handler(OrderCreatedEvent.event_type, order_handler)
        registry.register_handler(PaymentProcessedEvent.event_type, payment_handler)
        services.add_instance(EventHandlerRegistry, registry)

        # Configure middleware with custom options
        # This demonstrates the fluent configuration approach
        custom_retry_options = RetryOptions(
            max_retries=3,
            base_delay_ms=200,
            backoff_factor=1.5,
            retryable_exceptions=[RuntimeError, ConnectionError],
        )

        custom_circuit_breaker_options = CircuitBreakerOptions(
            failure_threshold=5, reset_timeout_seconds=10, half_open_success_threshold=2
        )

        # Configure event middleware using fluent builder pattern
        configure_event_middleware(
            services,
            registry,
            lambda builder: (
                # Configure order events with retry and metrics
                builder.add_retry(custom_retry_options, [OrderCreatedEvent.event_type])
                .add_metrics(event_types=[OrderCreatedEvent.event_type])
                # Configure payment events with circuit breaker
                .add_circuit_breaker(
                    custom_circuit_breaker_options, [PaymentProcessedEvent.event_type]
                )
                .add_metrics(event_types=[PaymentProcessedEvent.event_type])
            ),
        )

        # Create service provider
        # Ensure LoggerService is provided as required by DI-logging refactor
        logger = LoggerService(LoggingConfig())
        provider = ServiceProvider(logger, services)
        await provider.initialize()

        return cls(provider, registry, logger)

    def _create_test_events(self):
        """Create test events for the demo."""
        # Create order event
        order_event = OrderCreatedEvent(
            order_id="ORD-123", customer_id="CUST-456", total_amount=99.99
        )
        order_context = EventHandlerContext(event=order_event)

        # Create payment events
        payment_event = PaymentProcessedEvent(
            payment_id="PMT-789", order_id="ORD-123", amount=99.99, successful=True
        )
        payment_context = EventHandlerContext(event=payment_event)

        failed_payment_event = PaymentProcessedEvent(
            payment_id="PMT-999", order_id="ORD-123", amount=99.99, successful=False
        )
        failed_payment_context = EventHandlerContext(event=failed_payment_event)

        return (
            order_event,
            order_context,
            payment_event,
            payment_context,
            failed_payment_event,
            failed_payment_context,
        )

    async def _process_event(
        self,
        context: EventHandlerContext,
        handlers: list[EventHandler],
        middleware: list,
    ):
        """Process an event through handlers and middleware."""
        results = []

        for handler in handlers:
            from uno.core.events.handlers import MiddlewareChainBuilder

            chain_builder = MiddlewareChainBuilder(handler)
            processor = chain_builder.build_chain(middleware)
            result = await processor(context)
            results.append(result)

        return results

    async def _display_metrics(self, order_middleware, payment_middleware):
        """Display metrics from middleware components."""
        self.logger.info("\n=== Middleware Metrics ===")
        # Import here to avoid circular imports
        from uno.core.events.middleware import MetricsMiddleware

        for middleware in order_middleware + payment_middleware:
            if isinstance(middleware, MetricsMiddleware):
                for event_type, metrics in middleware.metrics.items():
                    self.logger.info(f"Event: {event_type}")
                    self.logger.info(f"  Count: {metrics.count}")
                    self.logger.info(f"  Success: {metrics.success_count}")
                    self.logger.info(f"  Failure: {metrics.failure_count}")
                    self.logger.info(f"  Success rate: {metrics.success_rate:.2f}%")
                    self.logger.info(
                        f"  Avg duration: {metrics.average_duration_ms:.2f}ms"
                    )

    async def run_demo(self) -> None:
        """Run a demonstration of event handling with middleware."""
        self.logger.info("Starting middleware demo...")

        # Create test events
        (
            order_event,
            order_context,
            payment_event,
            payment_context,
            failed_payment_event,
            failed_payment_context,
        ) = self._create_test_events()

        # Get handlers and middleware chains
        order_handlers = self.registry.get_handlers(order_event.event_type)
        order_middleware = self.registry.build_middleware_chain(order_event.event_type)
        payment_handlers = self.registry.get_handlers(payment_event.event_type)
        payment_middleware = self.registry.build_middleware_chain(
            payment_event.event_type
        )

        # Process order event (should retry and succeed)
        self.logger.info("=== Processing Order Event (with retry) ===")
        order_results = await self._process_event(
            order_context, order_handlers, order_middleware
        )
        for result in order_results:
            self.logger.info(
                f"Order result: {'Success' if result.is_success else 'Failure'}"
            )
            if not result.is_success:
                self.logger.error(f"Error: {result.error}")

        # Process successful payment event
        self.logger.info("\n=== Processing Successful Payment Event ===")
        payment_results = await self._process_event(
            payment_context, payment_handlers, payment_middleware
        )
        for result in payment_results:
            self.logger.info(
                f"Payment result: {'Success' if result.is_success else 'Failure'}"
            )
            if not result.is_success:
                self.logger.error(f"Error: {result.error}")

        # Process failed payment event
        self.logger.info("\n=== Processing Failed Payment Event ===")
        failed_results = await self._process_event(
            failed_payment_context, payment_handlers, payment_middleware
        )
        for result in failed_results:
            self.logger.info(
                f"Failed payment result: {'Success' if result.is_success else 'Failure'}"
            )
            if not result.is_success:
                self.logger.info(f"Expected error: {result.error}")

        # Process multiple failed payments to trigger circuit breaker
        self.logger.info("\n=== Triggering Circuit Breaker ===")
        # Number of attempts needed to trigger circuit breaker
        circuit_breaker_threshold = 6

        for i in range(circuit_breaker_threshold):
            self.logger.info(f"Payment attempt {i + 1}")
            results = await self._process_event(
                failed_payment_context, payment_handlers, payment_middleware
            )
            for result in results:
                if not result.is_success:
                    self.logger.info(f"Error: {result.error}")

        # Display middleware metrics
        await self._display_metrics(order_middleware, payment_middleware)

        self.logger.info("\nDemo complete!")


async def main() -> None:
    """Main entry point."""
    app = await Application.create()
    await app.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
