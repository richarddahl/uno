# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Tests for EventHandlerRegistry with strict DI-injected LoggerService.
Verifies that handler registration, logging, and error context propagation work as expected.
"""
from __future__ import annotations

import pytest
from uno.core.errors.base import ErrorContext
from uno.core.errors.result import Failure, Success
from uno.core.events.base_event import DomainEvent
from uno.core.events.bus import InMemoryEventBus
from uno.core.events.context import EventHandlerContext
from uno.core.events.handlers import EventHandler, EventHandlerRegistry, EventHandlerDecorator
from uno.core.logging.logger import LoggerService, LoggingConfig
from typing import Any


class FakeLoggerService(LoggerService):
    def __init__(self) -> None:
        super().__init__(LoggingConfig(CONSOLE_OUTPUT=False))
        self.logs: list[tuple[str, str, dict[str, Any]]] = []

    def structured_log(self, level: str, msg: str, **kwargs: Any) -> None:
        self.logs.append((level, msg, kwargs))

class DummyHandler(EventHandler):
    async def handle(self, context: ErrorContext) -> Success[str, Exception]:
        return Success("ok")

@pytest.mark.asyncio
async def test_registry_registers_and_logs() -> None:
    logger = FakeLoggerService()
    registry = EventHandlerRegistry(logger)
    handler = DummyHandler()
    registry.register_handler("TestEvent", handler)
    # Should log registration
    assert any("Registered handler" in m for _, m, _ in logger.logs)
    # Should retrieve handler
    handlers = registry.get_handlers("TestEvent")
    assert handler in handlers

from uno.core.events.bus import InMemoryEventBus
from uno.core.events.base_event import DomainEvent
from uno.core.events.context import EventHandlerContext
from uno.core.errors.result import Failure

class FakeEvent(DomainEvent):
    event_type = "FailEvent"

@pytest.mark.asyncio
async def test_registry_error_logging() -> None:
    class FailingHandler(EventHandler):
        async def handle(self, context: EventHandlerContext) -> Failure[str, Exception]:
            raise ValueError("fail!")
    logger = FakeLoggerService()
    handler = FailingHandler()
    # Subscribe via AsyncEventHandlerAdapter to ensure bus can call it
    from uno.core.async_utils import AsyncEventHandlerAdapter
    bus = InMemoryEventBus(logger)
    bus.subscribe("FailEvent", AsyncEventHandlerAdapter(handler, logger))
    event = FakeEvent()
    await bus.publish(event)
    # Should log error
    assert any(
        "fail!" in str(msg)
        or any("fail!" in str(val) for val in kwargs.values())
        for _, msg, kwargs in logger.logs
    )
