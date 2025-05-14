import pytest
import asyncio
import threading
from uno.errors.base import UnoError, ErrorCategory, ErrorSeverity, get_error_context


# --- Fake error subclasses for testing ---
class FakeAppError(UnoError):
    def __init__(self, message: str, context: dict[str, object] | None = None):
        super().__init__(
            code="FAKE_APP_ERROR",
            message=message,
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.ERROR,
            context=context,
        )


class FakeValidationError(UnoError):
    def __init__(self, message: str, context: dict[str, object] | None = None):
        super().__init__(
            code="FAKE_VALIDATION_ERROR",
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            context=context,
        )


# --- Tests ---
def test_unoerror_cannot_be_instantiated():
    with pytest.raises(TypeError):
        UnoError("CODE", "msg", ErrorCategory.INTERNAL, ErrorSeverity.ERROR)


def test_fake_error_subclass_instantiation():
    err = FakeAppError("something went wrong")
    assert err.code == "FAKE_APP_ERROR"
    assert err.message == "something went wrong"
    assert err.category == ErrorCategory.INTERNAL
    assert err.severity == ErrorSeverity.ERROR
    assert isinstance(err.context, dict)
    assert err.timestamp is not None


def test_with_context_merges_context():
    err = FakeAppError("fail", {"a": 1})
    err2 = err.with_context({"b": 2})
    assert err2.context["a"] == 1
    assert err2.context["b"] == 2
    assert err is not err2


def test_wrap_preserves_original_exception():
    try:
        raise ValueError("bad value")
    except ValueError as e:
        wrapped = FakeAppError.wrap(
            e, "FAKE_WRAP", "wrapped", ErrorCategory.API, ErrorSeverity.ERROR
        )
    assert wrapped.code == "FAKE_WRAP"
    assert wrapped.category == ErrorCategory.API
    assert wrapped.severity == ErrorSeverity.ERROR
    assert wrapped.context["original_exception"] == "ValueError"
    assert wrapped.__cause__.__class__ is ValueError


def test_to_dict_and_str():
    err = FakeValidationError("invalid", {"foo": "bar"})
    d = err.to_dict()
    assert d["code"] == "FAKE_VALIDATION_ERROR"
    assert d["message"] == "invalid"
    assert d["category"] == "VALIDATION"
    assert d["severity"] == "WARNING"
    assert d["context"]["foo"] == "bar"
    assert "timestamp" in d
    s = str(err)
    assert s.startswith("FAKE_VALIDATION_ERROR")


def test_get_error_context():
    ctx = get_error_context()
    assert "file_name" in ctx
    assert "line_number" in ctx
    assert "function_name" in ctx
    assert "timestamp" in ctx


@pytest.mark.asyncio
async def test_async_error_context_propagation():
    async def raise_and_catch():
        try:
            raise FakeAppError("async fail", {"async": True})
        except FakeAppError as e:
            return e

    err = await raise_and_catch()
    assert err.message == "async fail"
    assert err.context["async"] is True


@pytest.mark.asyncio
async def test_async_wrap_error():
    async def inner():
        raise ValueError("bad async")

    async def outer():
        try:
            await inner()
        except Exception as e:
            return FakeAppError.wrap(
                e,
                "ASYNC_WRAP",
                "wrapped async",
                ErrorCategory.EVENT,
                ErrorSeverity.ERROR,
            )

    err = await outer()
    assert err.code == "ASYNC_WRAP"
    assert err.context["original_exception"] == "ValueError"


def test_threaded_error_context_propagation():
    result = {}

    def thread_func():
        try:
            raise FakeValidationError("thread fail", {"thread": True})
        except FakeValidationError as e:
            result["err"] = e

    t = threading.Thread(target=thread_func)
    t.start()
    t.join()
    err = result["err"]
    assert err.message == "thread fail"
    assert err.context["thread"] is True


def test_error_context_merging_async_thread():
    # Simulate error context merging across async and thread
    result = {}

    async def async_func():
        return FakeAppError("async", {"a": 1})

    def thread_func():
        try:
            err = asyncio.run(async_func())
            result["err"] = FakeAppError(
                err.message, context={"thread": 2, **err.context}
            )
        except Exception as e:
            result["exception"] = e

    t = threading.Thread(target=thread_func)
    t.start()
    t.join()
    if "exception" in result:
        raise result["exception"]
    err = result["err"]
    assert err.context["a"] == 1
    assert err.context["thread"] == 2
