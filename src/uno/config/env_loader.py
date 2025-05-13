"""
Environment variable loading utilities for the Uno configuration system.

This module provides functions for loading environment variables from
.env files with proper cascading and override behavior.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv
from uno.config.base import Environment


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
    env_files = find_env_files(env, base_dir)

    # For custom env files that might be passed for testing, add them explicitly
    if base_dir:
        quoted_env = base_dir / ".env.quoted"
        if quoted_env.exists() and quoted_env not in env_files:
            env_files.append(quoted_env)

    # Track which variables we've loaded
    loaded_vars: set[str] = set()
    result: dict[str, str] = {}

    # Load each file in priority order
    for env_file in env_files:
        # Load without overriding environment
        load_dotenv(env_file, override=override)

        # Also build a return dictionary of what was loaded
        with env_file.open() as f:
            for line in f:
                line_ = line.strip()

                # Skip comments and empty lines
                if not line_ or line_.startswith("#"):
                    continue

                # Parse KEY=VALUE format
                if "=" in line_:
                    key, value = line_.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if (value.startswith('"') and value.endswith('"')) or (
                        value.startswith("'") and value.endswith("'")
                    ):
                        value = value[1:-1]

                    # Only add if we haven't loaded this variable or if overriding
                    if key not in loaded_vars or override:
                        result[key] = value
                        loaded_vars.add(key)
                        # Also ensure it's in the environment
                        os.environ[key] = value

    return result


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
    # Check if already in environment
    value = os.environ.get(key)
    if value is not None:
        return value

    # Load from .env files
    env_vars = load_env_files(env, override=False)
    return env_vars.get(key, default)
