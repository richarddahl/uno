"""
Integration tests for the complete event flow including middleware and error handling.

This test validates the entire event system from publishing to handling, including:
- Factory pattern and dependency injection
- Event middleware execution
- Error handling with the Result monad
- Event publishing with both sync and async handlers
"""

import asyncio
import datetime
import uuid
from typing import Any, ClassVar

from pydantic import ConfigDict

import pytest

from uno.core.errors.result import Failure, Result, Success
from uno.core.events.events import (
    DomainEvent,
    EventBus,
    EventHandler,
    EventPriority,
    EventPublisher,
    InMemoryEventStore,
    get_event_bus,
    get_event_publisher,
    get_event_store,
    get_logger_service,
    set_event_bus,
    set_event_publisher,
    set_event_store,
    set_logger_service,
)
from uno.core.events.handlers import EventHandlerContext, LoggingMiddleware
from uno.core.events.middleware import (
    CircuitBreakerMiddleware,
    EventHandlerMiddleware,
    RetryMiddleware,
)
from uno.core.events.middleware_factory import EventHandlerMiddlewareFactory
from uno.core.logging.logger import LoggerService, LoggingConfig


# Test events
class TestEvent(DomainEvent):
    """Test event for integration testing."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    event_type: ClassVar[str] = "test_event"
    data: str = ""
    
    def __init__(
        self,
        data: str = "",
        *,
        event_id: str = "",
        aggregate_id: str = "",
        aggregate_type: str = "test_aggregate",
        timestamp: datetime.datetime | None = None,
        version: int = 1,
        topic: str | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        event_id = event_id or str(uuid.uuid4())
        aggregate_id = aggregate_id or str(uuid.uuid4())
        super().__init__(
            event_id=event_id,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            timestamp=timestamp,
            version=version,
            topic=topic,
            correlation_id=correlation_id,
            causation_id=causation_id,
            metadata=metadata or {},
        )
        self.data = data


class ErrorEvent(DomainEvent):
    """Event that triggers errors during handling."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    event_type: ClassVar[str] = "error_event"
    error_type: str = ""
    
    def __init__(
        self,
        error_type: str = "",
        *,
        event_id: str = "",
        aggregate_id: str = "",
        aggregate_type: str = "test_aggregate",
        timestamp: datetime.datetime | None = None,
        version: int = 1,
        topic: str | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        event_id = event_id or str(uuid.uuid4())
        aggregate_id = aggregate_id or str(uuid.uuid4())
        super().__init__(
            event_id=event_id,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            timestamp=timestamp,
            version=version,
            topic=topic,
            correlation_id=correlation_id,
            causation_id=causation_id,
            metadata=metadata or {},
        )
        self.error_type = error_type


# Test handlers
class TestEventHandler(EventHandler[TestEvent]):
    """Handler for TestEvent."""
    
    def __init__(self):
        """Initialize the handler."""
        super().__init__(TestEvent)
        self.processed_events: list[str] = []
    
    async def handle(self, event: TestEvent) -> dict[str, Any]:
        """Handle the test event."""
        self.processed_events.append(event.data)
        return {"status": "processed", "data": event.data}


class SyncTestEventHandler(EventHandler[TestEvent]):
    """Synchronous handler for TestEvent."""
    
    def __init__(self):
        """Initialize the handler."""
        super().__init__(TestEvent)
        self.processed_events: list[str] = []
    
    def handle(self, event: TestEvent) -> dict[str, Any]:
        """Handle the test event synchronously."""
        self.processed_events.append(event.data)
        return {"status": "processed", "data": event.data}


class ErrorEventHandler(EventHandler[ErrorEvent]):
    """Handler for ErrorEvent that throws exceptions based on error_type."""
    
    def __init__(self):
        """Initialize the handler."""
        super().__init__(ErrorEvent)
        self.successful_events: list[str] = []
        self.failed_events: list[str] = []
    
    async def handle(self, event: ErrorEvent) -> dict[str, Any]:
        """Handle or throw an exception based on error_type."""
        if event.error_type == "transient":
            # This will be retried by RetryMiddleware
            self.failed_events.append(event.error_type)
            raise ValueError("Transient error occurred")
        elif event.error_type == "permanent":
            # This should be caught by CircuitBreakerMiddleware
            self.failed_events.append(event.error_type)
            raise RuntimeError("Permanent error occurred")
        elif event.error_type == "timeout":
            # Simulate a timeout
            self.failed_events.append(event.error_type)
            await asyncio.sleep(0.1)  # Short sleep to simulate delay
            raise TimeoutError("Operation timed out")
        else:
            # No error, process normally
            self.successful_events.append(event.error_type)
            return {"status": "processed", "error_type": event.error_type}


# Test middleware
class CountingMiddleware(EventHandlerMiddleware):
    """Middleware that counts the number of events processed."""
    
    def __init__(self):
        """Initialize the middleware."""
        self.pre_count = 0
        self.post_count = 0
        self.error_count = 0
    
    async def pre_handle(self, context: EventHandlerContext) -> Result[None, Exception]:
        """Count before handling."""
        self.pre_count += 1
        return Success(None)
    
    async def post_handle(
        self, context: EventHandlerContext, result: Result[Any, Exception]
    ) -> Result[Any, Exception]:
        """Count after successful handling."""
        if result.is_success():
            self.post_count += 1
        return result
    
    async def on_error(
        self, context: EventHandlerContext, error: Exception
    ) -> Result[Any, Exception]:
        """Count on error."""
        self.error_count += 1
        return Failure(error)


# Test fixtures
@pytest.fixture
def reset_event_system():
    """Reset the event system between tests."""
    # Store original components
    orig_logger = get_logger_service()
    orig_bus = get_event_bus()
    orig_store = get_event_store()
    orig_publisher = get_event_publisher()
    
    # Create test logger
    test_logger = LoggerService(LoggingConfig(level="DEBUG"))
    set_logger_service(test_logger)
    
    yield
    
    # Restore original components
    set_logger_service(orig_logger)
    set_event_bus(orig_bus)
    set_event_store(orig_store)
    set_event_publisher(orig_publisher)


@pytest.fixture
def event_handler():
    """Create a test event handler."""
    return TestEventHandler()


@pytest.fixture
def sync_event_handler():
    """Create a synchronous test event handler."""
    return SyncTestEventHandler()


@pytest.fixture
def error_event_handler():
    """Create an error event handler."""
    return ErrorEventHandler()


@pytest.fixture
def counting_middleware():
    """Create a counting middleware."""
    return CountingMiddleware()


@pytest.fixture
def middleware_factory(counting_middleware):
    """Create middleware factory with default middlewares."""
    logger = get_logger_service()
    factory = EventHandlerMiddlewareFactory(logger)
    
    # Add test middleware
    factory.add_middleware(counting_middleware)
    
    # Add standard middlewares
    factory.add_middleware(LoggingMiddleware(logger))
    factory.add_middleware(RetryMiddleware(max_retries=2, logger=logger))
    factory.add_middleware(CircuitBreakerMiddleware(failure_threshold=3, logger=logger))
    
    return factory


@pytest.fixture
def event_bus_with_middleware(reset_event_system, middleware_factory):
    """Create an event bus with middleware."""
    bus = EventBus(get_logger_service())
    
    # Replace default bus
    set_event_bus(bus)
    
    return bus


@pytest.fixture
def event_store(reset_event_system):
    """Create an in-memory event store."""
    store = InMemoryEventStore(get_logger_service())
    
    # Replace default store
    set_event_store(store)
    
    return store


@pytest.fixture
def event_publisher(reset_event_system, event_bus_with_middleware, event_store):
    """Create an event publisher with the test bus and store."""
    publisher = EventPublisher(
        event_bus_with_middleware,
        event_store,
        get_logger_service()
    )
    
    # Replace default publisher
    set_event_publisher(publisher)
    
    return publisher


# Tests
@pytest.mark.asyncio
async def test_publish_and_handle_event(
    event_publisher, event_bus_with_middleware, event_handler
):
    """Test publishing and handling an event end-to-end."""
    # Register the handler
    event_bus_with_middleware.subscribe(event_handler)
    
    # Create and publish an event
    event = TestEvent(data="test_data_1")
    result = await event_publisher.publish(event)
    
    # Check that publishing succeeded
    assert result.is_success()
    
    # Check that the handler processed the event
    assert "test_data_1" in event_handler.processed_events


@pytest.mark.asyncio
async def test_publish_many_events(
    event_publisher, event_bus_with_middleware, event_handler
):
    """Test publishing multiple events at once."""
    # Register the handler
    event_bus_with_middleware.subscribe(event_handler)
    
    # Create and publish multiple events
    events = [
        TestEvent(data="batch_1"),
        TestEvent(data="batch_2"),
        TestEvent(data="batch_3"),
    ]
    
    result = await event_publisher.publish_many(events)
    
    # Check that publishing succeeded
    assert result.is_success()
    
    # Check that all events were processed
    for event in events:
        assert event.data in event_handler.processed_events


@pytest.mark.asyncio
async def test_sync_and_async_handlers(
    event_publisher, event_bus_with_middleware, event_handler, sync_event_handler
):
    """Test that both sync and async handlers work with the same event."""
    # Register both handlers
    event_bus_with_middleware.subscribe(event_handler)
    event_bus_with_middleware.subscribe(sync_event_handler)
    
    # Create and publish an event
    event = TestEvent(data="both_handlers")
    result = await event_publisher.publish(event)
    
    # Check that publishing succeeded
    assert result.is_success()
    
    # Check that both handlers processed the event
    assert "both_handlers" in event_handler.processed_events
    assert "both_handlers" in sync_event_handler.processed_events


@pytest.mark.asyncio
async def test_middleware_execution(
    event_publisher, event_bus_with_middleware, event_handler, counting_middleware
):
    """Test that middleware is executed during event handling."""
    # Register the handler
    event_bus_with_middleware.subscribe(event_handler)
    
    # Initial counts should be zero
    assert counting_middleware.pre_count == 0
    assert counting_middleware.post_count == 0
    assert counting_middleware.error_count == 0
    
    # Create and publish an event
    event = TestEvent(data="middleware_test")
    result = await event_publisher.publish(event)
    assert result.is_success()
    
    # Check that middleware was executed
    assert counting_middleware.pre_count == 1
    assert counting_middleware.post_count == 1
    assert counting_middleware.error_count == 0


@pytest.mark.asyncio
async def test_error_handling(
    event_publisher, event_bus_with_middleware, error_event_handler, counting_middleware
):
    """Test error handling during event processing."""
    # Register the handler
    event_bus_with_middleware.subscribe(error_event_handler)
    
    # Create and publish events that will cause different types of errors
    events = [
        ErrorEvent(error_type="none"),     # No error
        ErrorEvent(error_type="transient"),  # Transient error (retryable)
        ErrorEvent(error_type="permanent"),  # Permanent error 
    ]
    
    # Publish events
    for event in events:
        publish_result = await event_publisher.publish(event)
        
        # The result should still be successful because errors are handled
        assert publish_result.is_success()
    
    # Check handler state
    assert "none" in error_event_handler.successful_events
    assert "transient" in error_event_handler.failed_events
    assert "permanent" in error_event_handler.failed_events
    
    # Check middleware counts
    # Pre-handle should be called for all events
    expected_events_count = 3
    assert counting_middleware.pre_count == expected_events_count
    
    # Post-handle should be called only for successful events
    expected_success_count = 1
    assert counting_middleware.post_count == expected_success_count
    
    # Error-handle should be called for failed events
    # The transient error is retried, so it might be counted multiple times
    expected_min_errors = 2
    assert counting_middleware.error_count >= expected_min_errors


@pytest.mark.asyncio
async def test_event_store_persistence(
    event_publisher, event_store
):
    """Test that events are persisted to the event store."""
    # Create and publish an event
    event = TestEvent(data="persist_test")
    result = await event_publisher.publish(event)
    
    # Check that publishing succeeded
    assert result.is_success()
    
    # Check that the event was persisted
    events_result = await event_store.get_events()
    assert events_result.is_success()
    
    stored_events = events_result.value
    assert len(stored_events) >= 1
    
    # Find our event
    found = False
    for stored_event in stored_events:
        if isinstance(stored_event, TestEvent) and stored_event.data == "persist_test":
            found = True
            break
    
    assert found, "The published event was not found in the event store"


@pytest.mark.asyncio
async def test_event_store_filtering(
    event_publisher, event_store
):
    """Test filtering events from the event store."""
    # Create a unique aggregate ID for this test
    aggregate_id = str(uuid.uuid4())
    
    # Create and publish events with the same aggregate ID
    events = [
        TestEvent(data="filter_1", aggregate_id=aggregate_id, version=1),
        TestEvent(data="filter_2", aggregate_id=aggregate_id, version=2),
        TestEvent(data="filter_3", aggregate_id=aggregate_id, version=3),
    ]
    
    for event in events:
        publish_result = await event_publisher.publish(event)
        assert publish_result.is_success()
    
    # Query events with filtering
    result = await event_store.get_events(
        aggregate_id=aggregate_id,
        since_version=2
    )
    
    assert result.is_success()
    filtered_events = result.value
    
    # Should only have events with version >= 2
    expected_filtered_events = 2
    assert len(filtered_events) == expected_filtered_events
    
    # Verify the correct events were returned
    event_data = {event.data for event in filtered_events}
    assert "filter_2" in event_data
    assert "filter_3" in event_data
    assert "filter_1" not in event_data


@pytest.mark.asyncio
async def test_di_factories(reset_event_system):
    """Test that the DI factory functions work correctly."""
    # Get default instances
    logger1 = get_logger_service()
    bus1 = get_event_bus()
    store1 = get_event_store()
    publisher1 = get_event_publisher()
    
    # Getting again should return the same instances
    logger2 = get_logger_service()
    bus2 = get_event_bus()
    store2 = get_event_store()
    publisher2 = get_event_publisher()
    
    assert logger1 is logger2
    assert bus1 is bus2
    assert store1 is store2
    assert publisher1 is publisher2
    
    # Setting a new instance should replace the default
    new_logger = LoggerService(LoggingConfig(level="ERROR"))
    set_logger_service(new_logger)
    
    assert get_logger_service() is new_logger
    assert get_logger_service() is not logger1


@pytest.mark.asyncio
async def test_handler_priority(
    event_publisher, event_bus_with_middleware, reset_event_system
):
    """Test that handlers are executed in priority order."""
    execution_order = []
    
    # Create handlers with different priorities
    class HighPriorityHandler(EventHandler[TestEvent]):
        def __init__(self):
            super().__init__(TestEvent)
        
        async def handle(self, event: TestEvent):
            execution_order.append("high")
            return {"priority": "high"}
    
    class NormalPriorityHandler(EventHandler[TestEvent]):
        def __init__(self):
            super().__init__(TestEvent)
        
        async def handle(self, event: TestEvent):
            execution_order.append("normal")
            return {"priority": "normal"}
    
    class LowPriorityHandler(EventHandler[TestEvent]):
        def __init__(self):
            super().__init__(TestEvent)
        
        async def handle(self, event: TestEvent):
            execution_order.append("low")
            return {"priority": "low"}
    
    # Register handlers with different priorities
    event_bus_with_middleware.subscribe(
        LowPriorityHandler(), priority=EventPriority.LOW
    )
    event_bus_with_middleware.subscribe(
        NormalPriorityHandler(), priority=EventPriority.NORMAL
    )
    event_bus_with_middleware.subscribe(
        HighPriorityHandler(), priority=EventPriority.HIGH
    )
    
    # Publish an event
    event = TestEvent(data="priority_test")
    result = await event_publisher.publish(event)
    assert result.is_success()
    
    # Check that handlers were executed in the correct order
    assert execution_order == ["high", "normal", "low"]


@pytest.mark.asyncio
async def test_topic_based_routing(
    event_publisher, event_bus_with_middleware, reset_event_system
):
    """Test that events are routed to handlers based on topic patterns."""
    received_topics = []
    
    # Define a handler that tracks which topics it receives
    class TopicHandler(EventHandler[TestEvent]):
        def __init__(self):
            super().__init__(TestEvent)
        
        async def handle(self, event: TestEvent):
            received_topics.append(event.topic)
            return {"topic": event.topic}
    
    # Register the handler with a topic pattern
    handler = TopicHandler()
    event_bus_with_middleware.subscribe(
        handler, topic_pattern=r"test\..+"
    )
    
    # Publish events with different topics
    events = [
        TestEvent(data="topic1", topic="test.command"),
        TestEvent(data="topic2", topic="test.query"),
        TestEvent(data="topic3", topic="other.event"),  # Shouldn't match
    ]
    
    for event in events:
        result = await event_publisher.publish(event)
        assert result.is_success()
    
    # Check that only matching topics were received
    expected_topics_count = 2
    assert len(received_topics) == expected_topics_count
    assert "test.command" in received_topics
    assert "test.query" in received_topics
    assert "other.event" not in received_topics


@pytest.mark.asyncio
async def test_add_and_publish_pending(
    event_publisher, event_bus_with_middleware, event_handler
):
    """Test adding events to the publisher and then publishing them later."""
    # Register the handler
    event_bus_with_middleware.subscribe(event_handler)
    
    # Add events to the publisher
    events = [
        TestEvent(data="pending_1"),
        TestEvent(data="pending_2"),
        TestEvent(data="pending_3"),
    ]
    
    for event in events:
        event_publisher.add(event)
    
    # No events should be processed yet
    for event in events:
        assert event.data not in event_handler.processed_events
    
    # Publish pending events
    result = await event_publisher.publish_pending()
    
    # Check that publishing succeeded
    assert result.is_success()
    
    # Check that all events were processed
    for event in events:
        assert event.data in event_handler.processed_events


@pytest.mark.asyncio
async def test_circuit_breaker_middleware(
    event_publisher, event_bus_with_middleware, error_event_handler, reset_event_system
):
    """Test that CircuitBreakerMiddleware prevents cascading failures."""
    # Create a custom middleware factory with a lower threshold
    logger = get_logger_service()
    factory = EventHandlerMiddlewareFactory(logger)
    
    # Add circuit breaker with threshold of 2 failures
    circuit_breaker = CircuitBreakerMiddleware(failure_threshold=2, logger=logger)
    factory.add_middleware(circuit_breaker)
    
    # Create a new event bus with the custom middleware
    bus = EventBus(logger)
    set_event_bus(bus)
    
    # Register the handler
    bus.subscribe(error_event_handler)
    
    # Create and publish events that will fail
    events = [
        ErrorEvent(error_type="permanent"),  # First failure
        ErrorEvent(error_type="permanent"),  # Second failure
        ErrorEvent(error_type="permanent"),  # Circuit should be open now
        ErrorEvent(error_type="permanent"),  # Should be rejected by circuit breaker
    ]
    
    # Publish the first three events to trip the circuit breaker
    for event in events[:3]:
        result = await event_publisher.publish(event)
        assert result.is_success()  # Overall publish should succeed
    
    # After the threshold, the circuit should be open
    assert circuit_breaker.is_circuit_open()
    
    # Publish one more event - it should be rejected by the circuit breaker
    result = await event_publisher.publish(events[3])
    
    # The overall publish should still succeed (circuit breaker handled it)
    assert result.is_success()
    
    # But the event should not have been processed by the handler
    expected_failed_events = 3  # Only the first 3
    assert len(error_event_handler.failed_events) == expected_failed_events
