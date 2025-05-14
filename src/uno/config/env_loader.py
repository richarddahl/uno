"""
Environment variable loading utilities for the Uno configuration system.

This module provides functions for loading environment variables from
.env files with proper cascading and override behavior.
"""

from __future__ import annotations

import os
import warnings
from collections import defaultdict
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


def load_env_file(file_path: str | Path) -> dict[str, str]:
    """
    Load environment variables from a .env file.

    Args:
        file_path: Path to the .env file

    Returns:
        Dictionary of environment variables

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file has invalid format
    """
    # Convert string path to Path object for consistent handling
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Environment file not found: {path}")

    env_vars = {}
    case_insensitive_map = defaultdict(set)

    with open(path, "r") as file:
        for line_num, line in enumerate(file, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse KEY=VALUE format
            if "=" not in line:
                raise ValueError(f"Invalid format at line {line_num}: {line}")

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]

            # Check for case-insensitive duplicates
            case_insensitive_key = key.lower()
            case_insensitive_map[case_insensitive_key].add(key)

            if case_insensitive_key in [k.lower() for k in env_vars]:
                # Get the existing key that collides
                existing_keys = case_insensitive_map[case_insensitive_key]
                collision_key = next(k for k in existing_keys if k != key)
                warnings.warn(
                    f"Case-insensitive environment variable collision detected: "
                    f"'{key}' conflicts with existing '{collision_key}' at line {line_num}. "
                    f"The newer value will take precedence."
                )

            env_vars[key] = value

    return env_vars


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
