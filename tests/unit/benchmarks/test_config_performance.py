# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Performance benchmarks for the configuration system.

This module measures the performance of various aspects of the configuration 
system including loading, caching, and environment variable resolution.
"""

import os
import tempfile
import time
import asyncio
from pathlib import Path
from typing import Any
import pytest

from uno.config import (
    Config,
    Environment,
    SecureField,
    SecureValueHandling,
    load_settings,
    get_config,
)
from uno.config.env_cache import env_cache
from uno.config.env_loader import load_env_files, get_env_value, async_load_env_files


@pytest.fixture
def temp_env_dir():
    """Create a temporary directory for environment files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        yield temp_path


@pytest.fixture
def env_vars():
    """Save and restore environment variables."""
    saved_vars = os.environ.copy()
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(saved_vars)


@pytest.fixture(autouse=True)
def clear_env_cache():
    """Clear the environment cache before and after each test."""
    env_cache.clear()
    yield
    env_cache.clear()


@pytest.fixture
def large_env_file(temp_env_dir):
    """Create a large environment file for testing."""
    env_file = temp_env_dir / ".env"
    with open(env_file, "w") as f:
        # Generate 1000 environment variables
        for i in range(1000):
            f.write(f"ENV_VAR_{i}=value_{i}\n")
    return env_file


@pytest.fixture
def very_large_env_file(temp_env_dir):
    """Create a very large environment file for testing."""
    env_file = temp_env_dir / ".env"
    with open(env_file, "w") as f:
        # Generate 10,000 environment variables
        for i in range(10000):
            f.write(f"ENV_VAR_{i}=value_{i}\n")
    return env_file


class SmallConfig(Config):
    """A small configuration class for benchmark testing."""
    debug: bool = False
    log_level: str = "INFO"
    port: int = 8000


class MediumConfig(Config):
    """A medium-sized configuration class for benchmark testing."""
    debug: bool = False
    log_level: str = "INFO"
    port: int = 8000
    host: str = "localhost"
    app_name: str = "benchmark"
    timeout: int = 30
    max_connections: int = 100
    retry_count: int = 3
    secure_key: str = SecureField(default="secret")
    # Add 10 more fields
    value_1: str = "value_1"
    value_2: int = 2
    value_3: float = 3.0
    value_4: bool = True
    value_5: list[str] = ["a", "b", "c"]
    value_6: dict[str, Any] = {"key": "value"}
    value_7: str = "value_7"
    value_8: int = 8
    value_9: float = 9.0
    value_10: bool = False


class LargeConfig(Config):
    """A large configuration class for benchmark testing."""
    # Include all fields from medium config
    debug: bool = False
    log_level: str = "INFO"
    port: int = 8000
    host: str = "localhost"
    app_name: str = "benchmark"
    timeout: int = 30
    max_connections: int = 100
    retry_count: int = 3
    secure_key: str = SecureField(default="secret")
    value_1: str = "value_1"
    value_2: int = 2
    value_3: float = 3.0
    value_4: bool = True
    value_5: list[str] = ["a", "b", "c"]
    value_6: dict[str, Any] = {"key": "value"}
    value_7: str = "value_7"
    value_8: int = 8
    value_9: float = 9.0
    value_10: bool = False
    
    # Add 40 more fields for a total of 50
    # This simulates a large configuration class with many settings
    large_1: str = "large_1"
    large_2: int = 2
    large_3: float = 3.0
    large_4: bool = True
    large_5: list[str] = ["a", "b", "c"]
    large_6: dict[str, Any] = {"key": "value"}
    large_7: str = "large_7"
    large_8: int = 8
    large_9: float = 9.0
    large_10: bool = False
    # ... and so on for 40 fields
    large_11: str = "large_11"
    large_12: int = 12
    large_13: float = 13.0
    large_14: bool = True
    large_15: str = "large_15"
    large_16: int = 16
    large_17: float = 17.0
    large_18: bool = False
    large_19: str = "large_19"
    large_20: int = 20
    large_21: float = 21.0
    large_22: bool = True
    large_23: str = "large_23"
    large_24: int = 24
    large_25: float = 25.0
    large_26: bool = False
    large_27: str = "large_27"
    large_28: int = 28
    large_29: float = 29.0
    large_30: bool = True
    large_31: str = "large_31"
    large_32: int = 32
    large_33: float = 33.0
    large_34: bool = False
    large_35: str = "large_35"
    large_36: int = 36
    large_37: float = 37.0
    large_38: bool = True
    large_39: str = "large_39"
    large_40: int = 40


def time_execution(func, *args, **kwargs):
    """Measure execution time of a function."""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    return result, end_time - start_time


async def async_time_execution(func, *args, **kwargs):
    """Measure execution time of an async function."""
    start_time = time.time()
    result = await func(*args, **kwargs)
    end_time = time.time()
    return result, end_time - start_time


# Basic configuration loading benchmarks
@pytest.mark.asyncio
async def test_benchmark_load_small_config():
    """Benchmark loading a small configuration class."""
    # Measure time to load
    _, duration = await async_time_execution(load_settings, SmallConfig)
    print(f"\nTime to load small config: {duration:.6f} seconds")
    
    # Assert reasonable performance (adjust thresholds as needed)
    assert duration < 0.1, f"Loading small config took too long: {duration:.6f} seconds"


@pytest.mark.asyncio
async def test_benchmark_load_medium_config():
    """Benchmark loading a medium configuration class."""
    # Measure time to load
    _, duration = await async_time_execution(load_settings, MediumConfig)
    print(f"\nTime to load medium config: {duration:.6f} seconds")
    
    # Assert reasonable performance (adjust thresholds as needed)
    assert duration < 0.2, f"Loading medium config took too long: {duration:.6f} seconds"


@pytest.mark.asyncio
async def test_benchmark_load_large_config():
    """Benchmark loading a large configuration class."""
    # Measure time to load
    _, duration = await async_time_execution(load_settings, LargeConfig)
    print(f"\nTime to load large config: {duration:.6f} seconds")
    
    # Assert reasonable performance (adjust thresholds as needed)
    assert duration < 0.5, f"Loading large config took too long: {duration:.6f} seconds"


# Caching benchmarks
@pytest.mark.asyncio
async def test_benchmark_config_cache():
    """Benchmark the configuration cache."""
    # First load (uncached)
    _, first_duration = await async_time_execution(get_config, MediumConfig)
    print(f"\nTime for first (uncached) load: {first_duration:.6f} seconds")
    
    # Second load (cached)
    _, second_duration = await async_time_execution(get_config, MediumConfig)
    print(f"Time for second (cached) load: {second_duration:.6f} seconds")
    
    # Cache should provide significant speedup
    assert second_duration < first_duration / 2, "Caching did not provide expected speedup"
    
    # Absolute performance threshold for cached load
    assert second_duration < 0.01, f"Cached config load took too long: {second_duration:.6f} seconds"


# Environment file loading benchmarks
@pytest.mark.asyncio
async def test_benchmark_env_file_loading(large_env_file, env_vars):
    """Benchmark loading a large environment file."""
    # Switch to the directory with the env file
    os.chdir(large_env_file.parent)
    
    # Measure time for sync loading (first time)
    _, sync_first_duration = time_execution(
        load_env_files, Environment.DEVELOPMENT
    )
    print(f"\nTime for first sync env file load: {sync_first_duration:.6f} seconds")
    
    # Measure time for sync loading (second time, with cache)
    _, sync_second_duration = time_execution(
        load_env_files, Environment.DEVELOPMENT
    )
    print(f"Time for second sync env file load: {sync_second_duration:.6f} seconds")
    
    # Clear cache to test async loading
    env_cache.clear()
    
    # Measure time for async loading (first time)
    _, async_first_duration = await async_time_execution(
        async_load_env_files, Environment.DEVELOPMENT
    )
    print(f"Time for first async env file load: {async_first_duration:.6f} seconds")
    
    # Measure time for async loading (second time, with cache)
    _, async_second_duration = await async_time_execution(
        async_load_env_files, Environment.DEVELOPMENT
    )
    print(f"Time for second async env file load: {async_second_duration:.6f} seconds")
    
    # Cache should provide speedup
    assert sync_second_duration < sync_first_duration, "Sync caching did not provide speedup"
    assert async_second_duration < async_first_duration, "Async caching did not provide speedup"
    
    # Async should be faster or comparable to sync for IO-bound operations
    # (may not always be true due to overhead, so this is a soft assertion)
    print(f"Async/sync ratio: {async_first_duration / sync_first_duration:.2f}x")


# Environment variable lookup benchmarks
@pytest.mark.asyncio
async def test_benchmark_env_var_lookup(env_vars):
    """Benchmark environment variable lookups."""
    # Set a test environment variable
    os.environ["TEST_LOOKUP_VAR"] = "value"
    
    # Measure time for direct os.environ lookup
    def direct_lookup():
        return os.environ.get("TEST_LOOKUP_VAR")
    
    _, direct_duration = time_execution(direct_lookup)
    print(f"\nTime for direct os.environ lookup: {direct_duration:.8f} seconds")
    
    # Measure time for first cached lookup
    _, first_cached_duration = time_execution(get_env_value, "TEST_LOOKUP_VAR")
    print(f"Time for first cached env var lookup: {first_cached_duration:.8f} seconds")
    
    # Measure time for subsequent cached lookup
    _, second_cached_duration = time_execution(get_env_value, "TEST_LOOKUP_VAR")
    print(f"Time for subsequent cached env var lookup: {second_cached_duration:.8f} seconds")
    
    # Cached lookup should eventually be faster than direct lookup
    # but first lookup might be slower due to cache initialization
    assert second_cached_duration < first_cached_duration * 1.5, "Cached lookup not faster"


# Environment variable resolution benchmark
@pytest.mark.asyncio
async def test_benchmark_env_resolution(env_vars):
    """Benchmark environment variable resolution in configs."""
    # Create 100 environment variables to test resolution performance
    for i in range(100):
        os.environ[f"TEST_VAR_{i}"] = f"value_{i}"
    
    # Create a config class that can resolve these variables
    class EnvResolutionConfig(Config):
        # Add 100 fields that match the environment variables
        locals().update({f"test_var_{i}": f"default_{i}" for i in range(100)})
    
    # Measure time to load and resolve all environment variables
    _, duration = await async_time_execution(load_settings, EnvResolutionConfig)
    print(f"\nTime to resolve 100 environment variables: {duration:.6f} seconds")
    
    # Ensure we resolved the values correctly (spot check)
    config = await load_settings(EnvResolutionConfig)
    assert config.test_var_0 == "value_0"
    assert config.test_var_99 == "value_99"
    
    # Assert reasonable performance
    assert duration < 0.1, f"Environment variable resolution took too long: {duration:.6f} seconds"


# Very large environment file benchmark
@pytest.mark.asyncio
async def test_benchmark_very_large_env_file(very_large_env_file, env_vars):
    """Benchmark loading a very large environment file (stress test)."""
    # This test is tagged slow because it's a stress test
    os.chdir(very_large_env_file.parent)
    
    # Measure time for sync loading
    _, sync_duration = time_execution(
        load_env_files, Environment.DEVELOPMENT
    )
    print(f"\nTime to load very large env file (sync): {sync_duration:.6f} seconds")
    
    # Clear cache
    env_cache.clear()
    
    # Measure time for async loading
    _, async_duration = await async_time_execution(
        async_load_env_files, Environment.DEVELOPMENT
    )
    print(f"Time to load very large env file (async): {async_duration:.6f} seconds")
    
    # Just log the performance, don't assert as this is a stress test
    # The important thing is that it completes without errors
