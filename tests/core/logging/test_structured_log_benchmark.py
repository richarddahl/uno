# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
"""
Performance/benchmark tests in this file are only run if explicitly selected with '-m performance' or '-m benchmark'.
The marker/skip logic is now centralized in tests/conftest.py.

Benchmark for structured_log throughput in a simulated event handler loop.

Performance/benchmark tests in this file are only run if explicitly selected.
Add '-m performance' to your pytest command to include them:
    hatch run test:testV -m performance
Otherwise, these tests will be skipped by default.
"""

import asyncio
import pytest
from uno.infrastructure.logging.config_service import LoggingConfigService
from uno.infrastructure.logging.logger import LoggerService, LoggingConfig
from tests.core.logging.suppress_output import suppress_stdout_stderr


@pytest.fixture
def logger_service() -> LoggerService:
    config = LoggingConfig(CONSOLE_OUTPUT=False)
    logger_service = LoggerService(config)
    asyncio.run(logger_service.initialize())
    yield logger_service
    asyncio.run(logger_service.dispose())


@pytest.mark.performance
def test_structured_log_event_handler_benchmark(
    benchmark, logger_service: LoggerService
) -> None:
    event_context = {"event_type": "FakeEvent", "aggregate_id": "abc123", "version": 1}

    def log_structured_messages() -> None:
        with suppress_stdout_stderr():
            for _ in range(1000):
                logger_service.structured_log(
                    "info",
                    "Event handled",
                    name="bench.event_handler",
                    context=event_context,
                )

    benchmark(log_structured_messages)


@pytest.mark.performance
def test_structured_log_complex_context_benchmark(
    benchmark, logger_service: LoggerService
) -> None:
    complex_context = {
        "event_type": "FakeEvent",
        "aggregate_id": "abc123",
        "version": 1,
        "payload": {
            "foo": "bar",
            "numbers": list(range(100)),
            "nested": {"a": 1, "b": 2},
        },
        "user": {"id": "user-xyz", "roles": ["admin", "user"]},
        "meta": {"ip": "127.0.0.1", "trace_id": "xyz-123"},
    }

    def log_complex_messages() -> None:
        with suppress_stdout_stderr():
            for _ in range(1000):
                logger_service.structured_log(
                    "info",
                    "Event handled with complex context",
                    name="bench.complex_context",
                    context=complex_context,
                )

    benchmark(log_complex_messages)


@pytest.mark.performance
def test_structured_log_concurrent_benchmark(
    benchmark, logger_service: LoggerService
) -> None:
    event_context = {"event_type": "FakeEvent", "aggregate_id": "abc123", "version": 1}

    async def log_structured_messages_async() -> None:
        async def log_task() -> None:
            with suppress_stdout_stderr():
                for _ in range(250):
                    logger_service.structured_log(
                        "info",
                        "Event handled (async)",
                        name="bench.concurrent",
                        context=event_context,
                    )

        await asyncio.gather(*(log_task() for _ in range(4)))

    benchmark(lambda: asyncio.run(log_structured_messages_async()))
