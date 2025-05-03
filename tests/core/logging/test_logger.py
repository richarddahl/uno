# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT

import asyncio
import logging

import pytest

from uno.infrastructure.logging.logger import (
    LoggerService,
    LoggingConfig,
)


@pytest.fixture
def logger_service():
    service = LoggerService(LoggingConfig(CONSOLE_OUTPUT=True))
    asyncio.run(service.initialize())
    yield service
    asyncio.run(service.dispose())


def test_singleton_logger(logger_service):
    logger1 = logger_service.get_logger()
    logger2 = logger_service.get_logger()
    assert logger1 is logger2


def test_named_logger_singleton(logger_service):
    logger_a1 = logger_service.get_logger("a")
    logger_a2 = logger_service.get_logger("a")
    logger_b = logger_service.get_logger("b")
    assert logger_a1 is logger_a2
    assert logger_a1 is not logger_b


def test_logger_has_correct_type(logger_service):
    logger = logger_service.get_logger()
    assert isinstance(logger, logging.Logger)


def test_logging_output_to_stream_with_caplog(logger_service, caplog):
    logger = logger_service.get_logger("pytest.test")
    with caplog.at_level(logging.INFO, logger="pytest.test"):
        logger.info("hello world")
    assert any("hello world" in message for message in caplog.messages)


def test_logging_output_with_caplog(logger_service, caplog):
    logger = logger_service.get_logger("pytest.test")
    with caplog.at_level(logging.INFO, logger="pytest.test"):
        logger.info("hello world")
    assert any("hello world" in m for m in caplog.messages)


def test_logger_level_and_format(logger_service):
    logger = logger_service.get_logger("test2")
    assert logger.level == logging.NOTSET  # child loggers default to NOTSET
    root_logger = logging.getLogger()
    assert root_logger.level in (logging.INFO, logging.DEBUG, logging.WARNING)


def test_logger_thread_safety(logger_service):
    import threading

    results = []

    def getlog():
        results.append(logger_service.get_logger("thread"))

    threads = [threading.Thread(target=getlog) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(logger_instance is results[0] for logger_instance in results)


def test_logger_multiple_names(logger_service):
    names = ["uno", "uno.db", "uno.api"]
    loggers = [logger_service.get_logger(n) for n in names]
    for i, logger in enumerate(loggers):
        for j, logger2 in enumerate(loggers):
            if i == j:
                assert logger is logger2
            else:
                assert logger is not logger2


def test_logger_reconfiguration():
    service = LoggerService(LoggingConfig(CONSOLE_OUTPUT=False))
    import asyncio

    asyncio.run(service.initialize())
    logger = service.get_logger("uno")
    old_config = service._config
    new_config = LoggingConfig(LEVEL="DEBUG", CONSOLE_OUTPUT=False)
    asyncio.run(service.dispose())
    service._config = new_config
    asyncio.run(service.initialize())
    logger2 = service.get_logger("uno")
    assert logger is logger2
    # Restore old config
    asyncio.run(service.dispose())
    service._config = old_config
    asyncio.run(service.initialize())


def test_dynamic_reload_log_level(logger_service, caplog, capsys):
    # Default INFO, so DEBUG is not shown
    logger = logger_service.get_logger("uno.reload")
    with caplog.at_level(logging.INFO, logger="uno.reload"):
        logger.debug("should not appear")
        logger.info("should appear")
    assert "should appear" in caplog.text
    assert "should not appear" not in caplog.text
    # Dynamically set to DEBUG
    from uno.infrastructure.logging.config_service import LoggingConfigService

    config_service = LoggingConfigService(logger_service)
    config_service.set_level("DEBUG")
    # After dynamic reload, pytest caplog may not capture logs due to handler replacement.
    # So check both caplog.records and captured stdout.
    with caplog.at_level(logging.DEBUG, logger="uno.reload"):
        logger.debug("should appear after reload")
    found = any("should appear after reload" in r.getMessage() for r in caplog.records)
    if not found:
        captured = capsys.readouterr().out
        found = "should appear after reload" in captured
    assert found, "DEBUG log after reload should appear in caplog or stdout"


def test_dynamic_reload_format(monkeypatch, tmp_path):
    # Test that changing FORMAT updates output immediately
    from uno.infrastructure.logging.logger import LoggerService, LoggingConfig

    log_file = tmp_path / "logfmt.txt"
    config = LoggingConfig(
        FILE_OUTPUT=True,
        FILE_PATH=str(log_file),
        FORMAT="%(levelname)s|%(message)s",
        CONSOLE_OUTPUT=False,
    )
    logger_service = LoggerService(config)
    import asyncio

    asyncio.run(logger_service.initialize())
    logger = logger_service.get_logger("uno.reloadfmt")
    logger.info("format1")
    # Change format
    from uno.infrastructure.logging.config_service import LoggingConfigService

    config_service = LoggingConfigService(logger_service)
    config_service.update_config(FORMAT="%(message)s")
    logger.info("format2")
    # Flush file handler
    for handler in logger.handlers:
        handler.flush()
    with open(log_file) as f:
        lines = f.readlines()
    assert "INFO|format1" in lines[0]
    assert "format2" in lines[1]
    assert "|" not in lines[1]


def test_dynamic_reload_no_duplicate_handlers(logger_service):
    logger = logger_service.get_logger("uno.duphandlers")
    from uno.infrastructure.logging.config_service import LoggingConfigService

    config_service = LoggingConfigService(logger_service)
    config_service.set_level("DEBUG")
    config_service.set_level("INFO")
    config_service.set_level("WARNING")
    # After reload, count all StreamHandlers (should be 1)
    stream_handlers = [
        h for h in logger.handlers if isinstance(h, logging.StreamHandler)
    ]
    assert len(stream_handlers) == 1, (
        f"Expected 1 StreamHandler, found {len(stream_handlers)}"
    )


import pytest


def test_with_context_injects_fields(logger_service, caplog):
    logger = logger_service.with_context("uno.ctx", user_id=42, session="abc")
    with caplog.at_level(logging.INFO, logger="uno.ctx"):
        logger.info("hello context")
    record = next(r for r in caplog.records if r.name == "uno.ctx")
    context = getattr(record, "context", {})
    assert context.get("user_id") == 42
    assert context.get("session") == "abc"
    assert "hello context" in caplog.text


def test_with_context_merges_extra(logger_service, caplog):
    logger = logger_service.with_context("uno.ctx.merge", foo="bar")
    with caplog.at_level(logging.INFO, logger="uno.ctx.merge"):
        logger.info("msg", extra={"context": {"baz": 123}})
    record = next(r for r in caplog.records if r.name == "uno.ctx.merge")
    context = getattr(record, "context", {})
    assert context.get("foo") == "bar"
    assert context.get("baz") == 123


def test_get_child_logger_returns_dotted_name(logger_service):
    parent = "uno.parent"
    child = "sub"
    logger = logger_service.get_child_logger(parent, child)
    assert logger.name == f"{parent}.{child}"
    # Should be the same as get_logger with the full name
    logger2 = logger_service.get_logger(f"{parent}.{child}")
    assert logger is logger2


@pytest.mark.asyncio
async def test_structured_log_basic(logger_service, caplog):
    with caplog.at_level(logging.INFO):
        logger_service.structured_log("info", "Structured hello", foo="bar", user=123)
    assert any("Structured hello" in m for m in caplog.messages)
    # Context fields should be present in record
    assert any(
        "foo" in str(r.__dict__.get("context", {}))
        and "user" in str(r.__dict__.get("context", {}))
        for r in caplog.records
    )


@pytest.mark.asyncio
async def test_structured_log_error_and_trace_context(logger_service, caplog):
    with caplog.at_level(logging.ERROR):
        logger_service.structured_log(
            "error",
            "Something failed",
            error_context={"error_code": "E123", "detail": "Oops"},
            trace_context={"correlation_id": "abc", "trace_id": "xyz"},
        )
    record = caplog.records[-1]
    context = record.__dict__.get("context", {})
    assert context.get("error_code") == "E123"
    assert context.get("detail") == "Oops"
    assert context.get("correlation_id") == "abc"
    assert context.get("trace_id") == "xyz"


@pytest.mark.asyncio
async def test_structured_log_with_exc_info(logger_service, caplog):
    try:
        1 / 0
    except Exception as exc:
        with caplog.at_level(logging.ERROR):
            logger_service.structured_log("error", "ZeroDiv", exc_info=exc)
    record = caplog.records[-1]
    assert record.exc_info
    assert "ZeroDiv" in caplog.text
    assert "ZeroDivisionError" in caplog.text


@pytest.mark.asyncio
async def test_structured_log_json_output(tmp_path, monkeypatch):
    import json

    from uno.infrastructure.logging.logger import LoggingConfig

    # Set up JSON log config with file output
    log_file = tmp_path / "log.json"
    config = LoggingConfig(
        JSON_FORMAT=True,
        FILE_OUTPUT=True,
        FILE_PATH=str(log_file),
        CONSOLE_OUTPUT=False,
    )
    logger_service = LoggerService(config)
    import asyncio

    await asyncio.sleep(0)  # ensure event loop
    await logger_service.initialize()
    logger_service.structured_log(
        "info", "JsonTest", foo="bar", trace_context={"trace_id": "tid"}
    )
    # Flush file handler
    for handler in logging.getLogger().handlers:
        handler.flush()
    # Read log file and check JSON
    with open(log_file) as f:
        lines = f.readlines()
    assert lines
    log_obj = json.loads(lines[0])
    assert log_obj["message"] == "JsonTest"
    assert log_obj["foo"] == "bar"
    assert log_obj["trace_id"] == "tid"


@pytest.mark.asyncio
async def test_structured_log_invalid_level(logger_service):
    with pytest.raises(ValueError):
        logger_service.structured_log("notalevel", "bad")


@pytest.mark.asyncio
async def test_structured_log_empty_context(logger_service, caplog):
    with caplog.at_level(logging.INFO):
        logger_service.structured_log("info", "NoCtx")
    assert any("NoCtx" in m for m in caplog.messages)


def test_new_trace_context_generates_uuid(logger_service):
    import uuid

    ctx = logger_service.new_trace_context()
    assert "correlation_id" in ctx
    # Should be a valid UUID4
    uuid_obj = uuid.UUID(ctx["correlation_id"])
    assert uuid_obj.version == 4


def test_trace_scope_sets_correlation_id(logger_service, caplog):
    with caplog.at_level(logging.INFO):
        with logger_service.trace_scope(logger_service) as trace_ctx:
            logger_service.structured_log("info", "inside scope")
        # The last record should have the correlation_id
        record = caplog.records[-1]
        context = getattr(record, "context", {})
        assert "correlation_id" in context
        assert context["correlation_id"] == trace_ctx["correlation_id"]


def test_trace_scope_with_custom_correlation_id(logger_service, caplog):
    custom_id = "custom-id-1234"
    with caplog.at_level(logging.INFO):
        with logger_service.trace_scope(logger_service, correlation_id=custom_id):
            logger_service.structured_log("info", "with custom id")
        record = caplog.records[-1]
        context = getattr(record, "context", {})
        assert context["correlation_id"] == custom_id


def test_trace_scope_nested_contexts(logger_service, caplog):
    outer_id = "outer-id-1"
    inner_id = "inner-id-2"
    with caplog.at_level(logging.INFO):
        with logger_service.trace_scope(logger_service, correlation_id=outer_id):
            logger_service.structured_log("info", "outer")
            with logger_service.trace_scope(logger_service, correlation_id=inner_id):
                logger_service.structured_log("info", "inner")
            logger_service.structured_log("info", "outer-again")
    # Find the three records
    outer = next(r for r in caplog.records if r.getMessage() == "outer")
    inner = next(r for r in caplog.records if r.getMessage() == "inner")
    outer_again = next(r for r in caplog.records if r.getMessage() == "outer-again")
    assert getattr(outer, "context", {})["correlation_id"] == outer_id
    assert getattr(inner, "context", {})["correlation_id"] == inner_id
    assert getattr(outer_again, "context", {})["correlation_id"] == outer_id
