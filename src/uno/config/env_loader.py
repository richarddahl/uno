# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Environment variable loading utilities for the Uno configuration system.

This module provides functions for loading environment variables from
.env files with proper cascading and override behavior.
"""

from __future__ import annotations

import os
import asyncio
from pathlib import Path

from uno.config.environment import Environment
from uno.config.env_cache import env_cache


def find_env_files(env: Environment, base_dir: Path | None = None) -> list[Path]:
    """Find all applicable .env files for the given environment.

    This searches for both the base .env file and the environment-specific
    file, with preference given to the environment-specific file for
    conflicting variables.

    Args:
        env: The environment to load for
        base_dir: Optional base directory to search in (defaults to current dir)

    Returns:
        List of .env file paths, in priority order (least to most)
    """
    base_dir = base_dir or Path.cwd()

    # Base .env file is lowest priority
    base_env = base_dir / ".env"

    # Environment-specific .env file
    env_specific = base_dir / f".env.{env.value}"

    # Local development/testing overrides - only for non-production
    local_env = base_dir / ".env.local"

    # Build the list of files with proper priority order
    files = []

    if base_env.exists():
        files.append(base_env)

    if env_specific.exists():
        files.append(env_specific)

    # Local should be highest priority but only for development/testing
    # Explicitly skip .env.local for production for security reasons
    if local_env.exists() and env != Environment.PRODUCTION:
        files.append(local_env)

    return files


def load_env_file(file_path: Path) -> dict[str, str]:
    """Load environment variables from a file, using cache.

    Args:
        file_path: Path to the .env file

    Returns:
        Dictionary of environment variables
    """
    # Use the singleton env_cache instance directly
    return env_cache.get_env_file_content(file_path)


def load_dotenv(
    dotenv_path: str | Path | None = None, override: bool = False
) -> dict[str, str]:
    """
    Load environment variables from .env file and optionally set them in the environment.

    Args:
        dotenv_path: Path to the .env file. If None, searches in current and parent directories
        override: Whether to override existing environment variables

    Returns:
        Dictionary of loaded environment variables
    """
    # Find .env file if not specified
    if dotenv_path is None:
        current_dir = Path.cwd()
        for directory in [current_dir] + list(current_dir.parents):
            potential_path = directory / ".env"
            if potential_path.exists():
                dotenv_path = potential_path
                break

        if dotenv_path is None:
            return {}

    # Ensure dotenv_path is a Path object
    if isinstance(dotenv_path, str):
        dotenv_path = Path(dotenv_path)

    env_vars = load_env_file(dotenv_path)

    # Set variables in environment if requested
    if override:
        for key, value in env_vars.items():
            os.environ[key] = value
    else:
        # Only set variables that don't exist
        for key, value in env_vars.items():
            if key not in os.environ:
                os.environ[key] = value

    return env_vars


async def async_load_env_files(
    env: Environment = Environment.DEVELOPMENT,
    base_dir: Path | None = None,
    override: bool = True,
) -> dict[str, str]:
    """Asynchronously load environment variables from .env files.

    Args:
        env: The environment to load for
        base_dir: Optional base directory to search in
        override: Whether to override existing environment variables

    Returns:
        Dictionary of loaded environment variables
    """
    env_files = find_env_files(env, base_dir)

    # For custom env files that might be passed for testing, add them explicitly
    if base_dir:
        quoted_env = base_dir / ".env.quoted"
        if quoted_env.exists() and quoted_env not in env_files:
            env_files.append(quoted_env)

    # Load all files concurrently - properly create tasks
    tasks = []
    for env_file in env_files:
        # Create proper Task objects instead of just coroutines
        task = asyncio.create_task(_async_load_env_file(env_file, override))
        tasks.append(task)

    # Wait for all files to load
    results = await asyncio.gather(*tasks)

    # Merge results in priority order (later files override earlier ones)
    final_vars: dict[str, str] = {}
    for result in results:
        final_vars.update(result)

    # Set variables in environment
    if override:
        for key, value in final_vars.items():
            os.environ[key] = value

    return final_vars


async def _async_load_env_file(env_file: Path, override: bool) -> dict[str, str]:
    """Helper to load a single env file asynchronously."""
    # Run file I/O in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    env_vars = await loop.run_in_executor(None, load_env_file, env_file)

    # Set variables in environment if requested
    if override:
        for key, value in env_vars.items():
            os.environ[key] = value

    return env_vars


def load_env_files(
    env: Environment = Environment.DEVELOPMENT,
    base_dir: Path | None = None,
    override: bool = True,
) -> dict[str, str]:
    """Load environment variables from .env files.

    Args:
        env: The environment to load for
        base_dir: Optional base directory to search in
        override: Whether to override existing environment variables

    Returns:
        Dictionary of loaded environment variables
    """
    # Simple synchronous implementation to avoid event loop issues
    env_files = find_env_files(env, base_dir)

    # For custom env files that might be passed for testing
    if base_dir:
        quoted_env = base_dir / ".env.quoted"
        if quoted_env.exists() and quoted_env not in env_files:
            env_files.append(quoted_env)

    # Load all files sequentially - avoid async complexity
    final_vars: dict[str, str] = {}
    for env_file in env_files:
        env_vars = load_env_file(env_file)
        final_vars.update(env_vars)

    # Set variables in environment if requested
    if override:
        for key, value in final_vars.items():
            os.environ[key] = value

    return final_vars


def get_env_value(
    key: str, default: str | None = None, env: Environment = Environment.DEVELOPMENT
) -> str | None:
    """Get an environment variable with proper .env file fallbacks.

    Args:
        key: Environment variable name
        default: Default value if not found
        env: Environment to load from

    Returns:
        Environment variable value or default if not found
    """
    # Check if already in environment (using cache)
    value = env_cache.get_env_var(key)
    if value is not None:
        return value

    # Load from .env files
    env_vars = load_env_files(env, override=False)
    return env_vars.get(key, default)
