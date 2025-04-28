# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework: tests for Result monad combinators
import pytest
import asyncio
from uno.core.errors.result import Success, Failure, Result

def test_ensure_success():
    s = Success(42)
    # Passes predicate
    r1 = s.ensure(lambda x: x > 0, ValueError("must be positive"))
    assert r1.is_success
    # Fails predicate
    r2 = s.ensure(lambda x: x < 0, ValueError("must be negative"))
    assert r2.is_failure
    assert isinstance(r2.error, ValueError)
    assert str(r2.error) == "must be negative"

def test_ensure_failure():
    f = Failure(ValueError("fail"))
    r = f.ensure(lambda x: x > 0, ValueError("should not run"))
    assert r.is_failure
    assert r.error is f.error

def test_recover_success():
    s = Success(1)
    r = s.recover(lambda e: 999)
    assert r.is_success
    assert r.unwrap() == 1

def test_recover_failure():
    f = Failure(ValueError("fail"))
    r = f.recover(lambda e: 999)
    assert r.is_success
    assert r.unwrap() == 999

def test_map_async_success():
    async def plus_one(x: int) -> int:
        await asyncio.sleep(0)
        return x + 1
    s = Success(10)
    r = asyncio.run(s.map_async(plus_one))
    assert r.is_success
    assert r.unwrap() == 11

def test_map_async_failure():
    async def plus_one(x: int) -> int:
        await asyncio.sleep(0)
        return x + 1
    f = Failure(ValueError("fail"))
    r = asyncio.run(f.map_async(plus_one))
    assert r.is_failure

def test_flat_map_async_success():
    async def to_success(x: int) -> Result[int, Exception]:
        await asyncio.sleep(0)
        return Success(x * 2)
    s = Success(7)
    r = asyncio.run(s.flat_map_async(to_success))
    assert r.is_success
    assert r.unwrap() == 14

def test_flat_map_async_failure():
    async def to_success(x: int) -> Result[int, Exception]:
        await asyncio.sleep(0)
        return Success(x * 2)
    f = Failure(ValueError("fail"))
    r = asyncio.run(f.flat_map_async(to_success))
    assert r.is_failure

def test_map_async_exception():
    async def bad(x):
        raise RuntimeError("boom")
    s = Success(1)
    r = asyncio.run(s.map_async(bad))
    assert r.is_failure
    assert isinstance(r.error, RuntimeError)
    assert str(r.error) == "boom"

def test_flat_map_async_exception():
    async def bad(x):
        raise RuntimeError("flat boom")
    s = Success(2)
    r = asyncio.run(s.flat_map_async(bad))
    assert r.is_failure
    assert isinstance(r.error, RuntimeError)
    assert str(r.error) == "flat boom"
