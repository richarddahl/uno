"""Base configuration classes for Uno applications.

This module provides the foundational Config class that all configuration
classes in the Uno framework should inherit from.
"""

from typing import Any, ClassVar, TypeVar
from pathlib import Path
import tempfile

from pydantic import BaseModel, Field, create_model
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings

from uno.config.secure import SecureValue, SecureValueHandling
from uno.config.environment import Environment
from uno.config.env_loader import load_env_files

T = TypeVar("T")


class Config(BaseSettings):
    """Base class for all configuration settings in Uno applications.

    All configuration classes should inherit from this class to ensure
    consistent behavior and features.
    """

    # Class variable to track secure fields across all Config subclasses
    _secure_fields: ClassVar[set[str]] = set()

    model_config = {
        "env_nested_delimiter": "__",
        "extra": "ignore",
        "validate_assignment": True,
    }

    def __init__(self, **data: Any) -> None:
        """Initialize a Config instance and process secure fields.

        Args:
            **data: Initial field values
        """
        super().__init__(**data)

        # Detect secure fields every time (works for dynamic classes)
        secure_fields: set[str] = set()
        for field_name, field_info in type(self).model_fields.items():
            if (
                field_info.json_schema_extra
                and field_info.json_schema_extra.get("secure") is True
            ):
                secure_fields.add(field_name)
        # Set on the class, not the instance!
        type(self)._secure_fields = secure_fields

        # Wrap secure fields as SecureValue if not already
        for field_name in type(self)._secure_fields:
            value = getattr(self, field_name, None)
            if isinstance(value, SecureValue):
                continue
            field_info = type(self).model_fields.get(field_name)
            if not field_info or not field_info.json_schema_extra:
                continue
            handling_value = field_info.json_schema_extra.get("handling")
            if not handling_value:
                continue
            try:
                handling = SecureValueHandling(handling_value)
                setattr(self, field_name, SecureValue(value, handling=handling))
            except Exception:
                pass

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        """Dump model as dict, masking SecureValue fields."""
        data = super().model_dump(*args, **kwargs)
        for field in type(self)._secure_fields:
            if field in data and isinstance(data[field], SecureValue):
                data[field] = str(data[field])
        return data

    def model_dump_json(self, *args, **kwargs) -> str:
        """Dump model as JSON, masking SecureValue fields."""
        import json

        data = self.model_dump(*args, **kwargs)
        return json.dumps(data)

    async def _load_env_settings(self, env: Environment) -> None:
        """Load environment-specific settings from .env files.

        Args:
            env: The environment to load settings for
        """
        from uno.config.env_loader import load_env_files

        # Try to use the directory of the file where the config class is defined
        try:
            base_dir = Path(__file__).parent
        except Exception:
            base_dir = Path(tempfile.gettempdir())

        # Always pass a safe base_dir to avoid FileNotFoundError
        env_vars = load_env_files(env=env, base_dir=base_dir, override=True)

        # The values will be automatically loaded from environment by Pydantic
        # Since we've set override=True, they're already in os.environ
        # No need to manually update fields - Pydantic BaseSettings handles this
