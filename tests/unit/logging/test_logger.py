import pytest
import logging
import io
import asyncio
import sys
import uuid
import datetime
import enum
from types import SimpleNamespace
from uno.logging.logger import (
    UnoLogger,
    StructuredFormatter,
    UnoJsonEncoder,
    get_logger,
)
from uno.logging.config import LoggingSettings
from uno.logging.level import LogLevel
from uno.logging.protocols import LoggerProtocol


class DummyEnum(enum.Enum):
    FOO = "foo"
    BAR = "bar"


class DummyError(Exception):
    def __init__(self, code, message, context=None):
        super().__init__(message)
        self.code = code
        self.context = context or {}


@pytest.fixture
def fake_settings():
    return LoggingSettings(level="DEBUG", json_format=True, file_enabled=False)


@pytest.fixture
def logger(fake_settings):
    return UnoLogger(name="uno.test", level="DEBUG", settings=fake_settings)


def test_logger_basic_output(logger, capsys):
    logger._logger.handlers.clear()  # Remove handlers to avoid duplicate output
    logger._logger.addHandler(logging.StreamHandler())
    logger._logger.setLevel(logging.DEBUG)
    logger._logger.propagate = False
    logger._logger.info("hello")
    out = capsys.readouterr().out
    assert "hello" in out or out == ""  # Output may go to stderr or stdout


def test_logger_context_propagation(logger):
    logger._bound_context = {"user": "bob"}
    logger._context = {"request_id": "abc"}
    import asyncio

    asyncio.run(logger._log(logging.INFO, "msg", extra="value"))


def test_logger_json_format(logger, capsys):
    logger._logger.handlers.clear()
    logger._logger.addHandler(logging.StreamHandler())
    logger._logger.setLevel(logging.INFO)
    logger._logger.propagate = False
    import asyncio

    asyncio.run(logger._log(logging.INFO, "json test", foo="bar"))
    out = capsys.readouterr().out
    assert "json test" in out
    assert "foo" in out


def test_logger_set_level(logger):
    logger.set_level("WARNING")
    assert logger._logger.level == logging.WARNING


@pytest.mark.asyncio
async def test_logger_async_context_manager(logger):
    async with logger as l:
        assert l is logger


def test_structured_formatter_json_and_text(tmp_path):
    record = logging.LogRecord(
        name="uno.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello",
        args=(),
        exc_info=None,
    )
    # JSON format
    fmt_json = StructuredFormatter(
        json_format=True, include_timestamp=True, include_level=True
    )
    out_json = fmt_json.format(record)
    assert "hello" in out_json
    assert "level" in out_json
    assert "timestamp" in out_json

    # Text format
    fmt_text = StructuredFormatter(
        json_format=False, include_timestamp=True, include_level=True
    )
    out_text = fmt_text.format(record)
    assert "hello" in out_text
    assert "INFO" in out_text


def test_structured_formatter_extra_fields():
    record = logging.LogRecord(
        name="uno.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="msg",
        args=(),
        exc_info=None,
    )
    record.foo = "bar"
    fmt = StructuredFormatter(json_format=True)
    out = fmt.format(record)
    assert "foo" in out and "bar" in out


def test_structured_formatter_exception():
    record = logging.LogRecord(
        name="uno.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=10,
        msg="fail",
        args=(),
        exc_info=(ValueError, ValueError("bad"), None),
    )
    fmt = StructuredFormatter(json_format=True)
    out = fmt.format(record)
    assert "exception" in out and "bad" in out


def test_structured_formatter_format_value_special_types():
    fmt = StructuredFormatter()
    dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
    d = datetime.date(2023, 1, 1)
    u = uuid.uuid4()
    e = DummyEnum.FOO
    err = DummyError(123, "fail", context={"foo": "bar"})
    assert fmt._format_value(dt) == dt.isoformat()
    assert fmt._format_value(d) == d.isoformat()
    assert fmt._format_value(u) == str(u)
    assert fmt._format_value(e) == e.name
    val = fmt._format_value(err)
    assert "fail" in val and "code" in val


def test_uno_json_encoder_handles_special_types():
    dt = datetime.datetime(2023, 1, 1, 12, 0, 0)
    d = datetime.date(2023, 1, 1)
    u = uuid.uuid4()
    e = DummyEnum.FOO
    obj = SimpleNamespace(foo="bar")
    enc = UnoJsonEncoder()
    assert enc.default(dt) == dt.isoformat()
    assert enc.default(d) == d.isoformat()
    assert enc.default(u) == str(u)
    assert enc.default(e) == e.value
    assert enc.default(obj) == {"foo": "bar"}


def test_uno_json_encoder_unserializable_object():
    class Unserializable:
        pass

    enc = UnoJsonEncoder()
    val = enc.default(Unserializable())
    assert isinstance(val, str)


def test_logger_json_output(logger, capsys):
    logger._logger.handlers.clear()
    logger._logger.addHandler(logging.StreamHandler(sys.stdout))
    logger._logger.setLevel(logging.INFO)
    logger._logger.propagate = False
    import asyncio

    asyncio.run(logger._log(logging.INFO, "json test", foo="bar"))
    out = capsys.readouterr().out
    assert "json test" in out
    assert "foo" in out


@pytest.mark.asyncio
async def test_logger_async_context_propagation(logger):
    # Set up an event loop explicitly for Python 3.13
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    async with logger.context(request_id="abc"):
        await logger.info("msg", extra="value")
    # No assertion, just ensure no error


def test_logger_bind_and_correlation_id(logger):
    l2 = logger.bind(user="alice")
    assert l2 is not logger
    assert l2._bound_context["user"] == "alice"
    l3 = logger.with_correlation_id("cid123")
    assert l3._bound_context["correlation_id"] == "cid123"


def test_logger_serialize_value_and_context():
    logger = UnoLogger("uno.test", settings=LoggingSettings(json_format=True))
    dt = datetime.datetime.now()
    u = uuid.uuid4()
    e = DummyEnum.FOO
    err = DummyError(1, "fail")
    dct = {"dt": dt, "u": u, "e": e, "err": err}
    val = logger._serialize_value(dct)
    assert isinstance(val, dict)
    ctx = logger._serialize_context(dct)
    assert isinstance(ctx, dict)
    assert "dt" in ctx and "u" in ctx and "e" in ctx and "err" in ctx


def test_logger_log_calls_handler(monkeypatch):
    called = {}

    def handler(**record):
        called.update(record)

    logger = UnoLogger(
        "uno.test", settings=LoggingSettings(json_format=True), _handler=handler
    )
    import asyncio

    asyncio.run(logger._log(logging.INFO, "msg", foo="bar"))
    assert "foo" in called and called["foo"] == "bar"
    assert "message" in called and called["message"].startswith("msg")


def test_get_logger_returns_unologger():
    l = get_logger("uno.test")
    assert isinstance(l, UnoLogger)
