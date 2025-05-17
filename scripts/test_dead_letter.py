#!/usr/bin/env python3
"""Test script for DeadLetterQueue implementation."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel

# Add the project root to the Python path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from uno.event_bus.dead_letter import DeadLetterQueue, DeadLetterEvent, DeadLetterReason
from uno.metrics import Metrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestEvent(BaseModel):
    """Test event model."""
    id: str
    name: str
    timestamp: datetime = datetime.now(timezone.utc)
    data: dict[str, Any] = {}

async def main() -> None:
    """Test the DeadLetterQueue implementation."""
    # Initialize metrics and queue
    metrics = Metrics.get_instance()
    queue = DeadLetterQueue[TestEvent](metrics=metrics)
    
    # Add a handler that logs the dead-lettered event
    async def handle_dead_letter(event: DeadLetterEvent[TestEvent]) -> None:
        logger.info(
            "Processing dead letter event: %s (attempt %d/%d)",
            event.id,
            event.attempt_count,
            3  # max attempts
        )
        logger.info("Event data: %s", event.event_data)
        
        # Simulate processing failure on first attempt
        if event.attempt_count < 2:
            raise ValueError("Simulated processing error")
            
        logger.info("Successfully processed dead letter event: %s", event.id)
    
    # Register the handler
    queue.add_handler(handle_dead_letter)
    
    # Create a test event
    event = TestEvent(
        id="test-123",
        name="Test Event",
        data={"key": "value"}
    )
    
    # Add the event to the dead letter queue
    logger.info("Adding event to dead letter queue")
    await queue.add(
        event=event,
        reason=DeadLetterReason.HANDLER_FAILED,
        error=ValueError("Test error"),
        subscription_id="test-sub",
        attempt_count=1,
        custom_meta={"source": "test_script"}
    )
    
    # Process the queue with retries
    logger.info("Processing dead letter queue...")
    await queue.process(max_attempts=3, retry_delay=1.0)
    
    # Test with a different reason
    logger.info("\nTesting with DESERIALIZATION_FAILED reason")
    event2 = TestEvent(
        id="test-456",
        name="Deserialization Test",
        data={"corrupt": True}
    )
    
    await queue.add(
        event=event2,
        reason=DeadLetterReason.DESERIALIZATION_FAILED,
        error=TypeError("Could not deserialize JSON"),
        subscription_id="test-sub",
        attempt_count=1,
        custom_meta={"source": "test_script", "format": "JSON"}
    )
    
    await queue.process(max_attempts=3, retry_delay=1.0)
    
    # Verify metrics were recorded
    dlq_metrics = metrics.get_metrics().get("event_bus.dead_letter", {})
    logger.info("\nDead Letter Queue Metrics:")
    for key, value in dlq_metrics.items():
        logger.info(f"  {key}: {value}")
    
    # Test concurrent processing with multiple events
    logger.info("\nTesting concurrent processing")
    
    events = [
        TestEvent(id=f"concurrent-{i}", name=f"Concurrent Event {i}", data={"index": i})
        for i in range(5)
    ]
    
    # Add all events concurrently
    await asyncio.gather(
        *[
            queue.add(
                event=evt,
                reason=DeadLetterReason.VALIDATION_FAILED,
                error=ValueError(f"Validation error for event {evt.id}"),
                subscription_id="concurrent-sub",
                attempt_count=1
            )
            for evt in events
        ]
    )
    
    # Process all events concurrently
    logger.info("Processing multiple events concurrently...")
    await queue.process(max_attempts=2, retry_delay=0.5)
    
    logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(main())
