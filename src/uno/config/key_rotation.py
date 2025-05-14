"""
Key rotation utilities for the Uno configuration system.

This module provides tools for rotating encryption keys across multiple
secure configuration values.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Iterable, TypeVar, Generic

from uno.config.secure import SecureValue

T = TypeVar("T")
logger = logging.getLogger("uno.config.key_rotation")


async def rotate_secure_values(
    values: Iterable[SecureValue[T]],
    new_key_version: str,
    parallel: bool = True,
    batch_size: int = 50,
) -> None:
    """
    Rotate multiple secure values to a new encryption key version.

    Args:
        values: Iterable of SecureValue instances to rotate
        new_key_version: Key version to rotate to
        parallel: If True, performs rotation in parallel (default)
        batch_size: Number of values to process in parallel (when parallel=True)
    """
    if not values:
        logger.info("No values to rotate")
        return

    value_list = list(values)
    logger.info(
        f"Rotating {len(value_list)} secure values to key version {new_key_version}"
    )

    if parallel:
        # Process in batches to avoid overwhelming the system
        total_rotated = 0
        for i in range(0, len(value_list), batch_size):
            batch = value_list[i : i + batch_size]
            tasks = [value.rotate_key(new_key_version) for value in batch]
            await asyncio.gather(*tasks)
            total_rotated += len(batch)
            logger.info(f"Rotated {total_rotated}/{len(value_list)} values")
    else:
        # Process sequentially
        for i, value in enumerate(value_list):
            await value.rotate_key(new_key_version)
            if (i + 1) % 10 == 0 or i + 1 == len(value_list):
                logger.info(f"Rotated {i + 1}/{len(value_list)} values")

    logger.info(
        f"Successfully rotated {len(value_list)} secure values to key version {new_key_version}"
    )


async def setup_key_rotation(
    old_key: str | bytes,
    new_key: str | bytes,
    old_version: str = "v1",
    new_version: str = "v2",
) -> None:
    """
    Set up key rotation by registering both old and new keys, then setting the new one as current.

    Args:
        old_key: The current/old master key
        new_key: The new master key to rotate to
        old_version: Version identifier for the old key (default: "v1")
        new_version: Version identifier for the new key (default: "v2")
    """
    # Register the old key first (if not already registered)
    await SecureValue.setup_encryption(
        master_key=old_key,
        key_version=old_version,
    )

    # Register the new key
    await SecureValue.setup_encryption(
        master_key=new_key,
        key_version=new_version,
    )

    # Set the new key as current for any new encryptions
    await SecureValue.set_current_key_version(new_version)

    logger.info(
        f"Key rotation setup complete. New encryptions will use key version {new_version}"
    )
