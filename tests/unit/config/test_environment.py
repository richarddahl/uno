"""Tests for environment handling and .env file loading."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from uno.config import Environment
from uno.config.env_loader import (
    find_env_files,
    get_env_value,
    load_env_file,
    load_env_files,
)
from uno.config.env_cache import env_cache


class TestEnvLoader:
    """Test environment variable loading utilities."""

    def test_find_env_files(self, temp_env_files: tuple[Path, Path, Path]) -> None:
        """Test finding environment files."""
        base_dir = temp_env_files[0].parent

        # Test development environment
        dev_files = find_env_files(Environment.DEVELOPMENT, base_dir)
        assert len(dev_files) == 3
        assert ".env" in str(dev_files[0])
        assert ".env.development" in str(dev_files[1])
        assert ".env.local" in str(dev_files[2])

        # Create production env file
        prod_env = base_dir / ".env.production"
        prod_env.write_text("# Production environment\n")

        try:
            # Test production environment (should exclude .env.local)
            prod_files = find_env_files(Environment.PRODUCTION, base_dir)
            assert len(prod_files) == 2
            assert ".env" in str(prod_files[0])
            assert ".env.production" in str(prod_files[1])
            assert ".env.local" not in str(" ".join(str(f) for f in prod_files))
        finally:
            # Clean up
            prod_env.unlink(missing_ok=True)

    def test_load_env_file(self, env_dir: Path) -> None:
        """Test loading individual env file."""
        # Create test env file
        env_file = env_dir / ".env.test"
        env_content = """
        # Comment
        SIMPLE=value
        QUOTED_SINGLE='single quoted'
        QUOTED_DOUBLE="double quoted"
        WITH_SPACE= value with space 
        
        # Another comment
        ANOTHER=value
        """
        env_file.write_text(env_content)

        # Load the file
        env_vars = load_env_file(env_file)

        # Check parsing
        assert env_vars["SIMPLE"] == "value"
        assert env_vars["QUOTED_SINGLE"] == "single quoted"
        assert env_vars["QUOTED_DOUBLE"] == "double quoted"
        assert env_vars["WITH_SPACE"] == "value with space"
        assert env_vars["ANOTHER"] == "value"

        # Test file not found
        with pytest.raises(FileNotFoundError):
            load_env_file(env_dir / "nonexistent.env")

    def test_load_env_files(
        self, temp_env_files: tuple[Path, Path, Path], save_env_vars
    ) -> None:
        """Test loading environment variables from multiple files."""
        base_dir = temp_env_files[0].parent

        # Clear relevant environment variables
        for var in ["BASE_SETTING", "DEV_SETTING", "LOCAL_SETTING", "OVERRIDE_SETTING"]:
            os.environ.pop(var, None)

        # Load development environment
        env_vars = load_env_files(Environment.DEVELOPMENT, base_dir)

        # Check correct values with proper priority
        assert env_vars["BASE_SETTING"] == "base_value"
        assert env_vars["DEV_SETTING"] == "dev_value"
        assert env_vars["LOCAL_SETTING"] == "local_value"
        assert env_vars["OVERRIDE_SETTING"] == "local_override"  # Highest priority

        # Check values are set in actual environment
        assert os.environ["BASE_SETTING"] == "base_value"
        assert os.environ["OVERRIDE_SETTING"] == "local_override"

    def test_environment_caching(self, env_dir: Path, save_env_vars) -> None:
        """Test environment variable caching."""
        # Set test variables
        os.environ["CACHED_VAR"] = "original"

        # Get from cache - first time should cache
        value1 = env_cache.get_env_var("CACHED_VAR")
        assert value1 == "original"

        # Change the real environment variable
        os.environ["CACHED_VAR"] = "changed"

        # Get again - should return cached value
        value2 = env_cache.get_env_var("CACHED_VAR")
        assert value2 == "original"  # Still has cached value

        # Clear cache
        env_cache.clear()

        # Now should get updated value
        value3 = env_cache.get_env_var("CACHED_VAR")
        assert value3 == "changed"
