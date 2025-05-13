"""Tests for environment variable loading utilities."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from uno.config import Environment
from uno.config.env_loader import find_env_files, get_env_value, load_env_files


class TestEnvLoader:
    """Test environment variable loading."""

    def test_find_env_files(self, temp_env_files: tuple[Path, Path, Path]) -> None:
        """Test finding environment files."""
        base_dir = temp_env_files[0].parent

        # Test development environment
        files = find_env_files(Environment.DEVELOPMENT, base_dir)
        assert len(files) == 3
        assert ".env" in str(files[0])
        assert ".env.development" in str(files[1])
        assert ".env.local" in str(files[2])

        # Create a production-specific env file to ensure it's found
        prod_env = base_dir / ".env.production"
        with open(prod_env, "w") as f:
            f.write("# Production environment settings\n")

        try:
            # Test production environment (should exclude .env.local)
            files = find_env_files(Environment.PRODUCTION, base_dir)
            assert len(files) == 2
            assert ".env" in str(files[0])
            assert ".env.production" in str(files[1])
            assert ".env.local" not in str(" ".join(str(f) for f in files))
        finally:
            # Clean up
            prod_env.unlink(missing_ok=True)

        # Test with a non-existent directory
        empty_dir = base_dir / "empty"
        empty_dir.mkdir(exist_ok=True)
        files = find_env_files(Environment.DEVELOPMENT, empty_dir)
        assert len(files) == 0

    def test_load_env_files(self, temp_env_files: tuple[Path, Path, Path]) -> None:
        """Test loading environment variables from files."""
        base_dir = temp_env_files[0].parent

        # Clear any existing environment variables that might interfere
        os.environ.pop("BASE_SETTING", None)
        os.environ.pop("DEV_SETTING", None)
        os.environ.pop("LOCAL_SETTING", None)
        os.environ.pop("OVERRIDE_SETTING", None)

        # Load development environment
        env_vars = load_env_files(Environment.DEVELOPMENT, base_dir)

        # Should have all variables with correct priority (local overrides others)
        assert env_vars["BASE_SETTING"] == "base_value"
        assert env_vars["DEV_SETTING"] == "dev_value"
        assert env_vars["LOCAL_SETTING"] == "local_value"
        assert env_vars["OVERRIDE_SETTING"] == "local_override"

        # Check that they're also in the actual environment
        assert os.environ["BASE_SETTING"] == "base_value"
        assert os.environ["DEV_SETTING"] == "dev_value"
        assert os.environ["LOCAL_SETTING"] == "local_value"
        assert os.environ["OVERRIDE_SETTING"] == "local_override"

    def test_get_env_value(self, temp_env_files: tuple[Path, Path, Path]) -> None:
        """Test getting environment values with .env fallbacks."""
        # Clear any existing value
        os.environ.pop("TEST_ENV_VALUE", None)

        # Should fallback to .env files
        value = get_env_value("BASE_SETTING")
        assert value == "base_value"

        # Should handle missing keys with default
        value = get_env_value("MISSING_KEY", default="default_value")
        assert value == "default_value"

        # Should prioritize actual environment variables
        os.environ["OVERRIDE_SETTING"] = "direct_override"
        value = get_env_value("OVERRIDE_SETTING")
        assert value == "direct_override"

        # Clean up
        os.environ.pop("OVERRIDE_SETTING", None)

    def test_load_env_files_with_quotes(
        self, temp_env_files: tuple[Path, Path, Path]
    ) -> None:
        """Test loading environment variables with quoted values."""
        # Create a temp file with quoted values
        quoted_env = Path(temp_env_files[0].parent) / ".env.quoted"
        with open(quoted_env, "w") as f:
            f.write("QUOTED_SINGLE='single quoted value'\n")
            f.write('QUOTED_DOUBLE="double quoted value"\n')
            f.write("UNQUOTED=plain value\n")

        try:
            # Load the env files
            env_vars = load_env_files(Environment.DEVELOPMENT, quoted_env.parent)

            # Quotes should be removed
            assert env_vars["QUOTED_SINGLE"] == "single quoted value"
            assert env_vars["QUOTED_DOUBLE"] == "double quoted value"
            assert env_vars["UNQUOTED"] == "plain value"
        finally:
            # Clean up
            quoted_env.unlink(missing_ok=True)
