# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Key rotation utilities for the Uno configuration system.

This module provides tools for rotating encryption keys across multiple
secure configuration values.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Iterable, TypeVar

from uno.config.secure import SecureValue
from uno.config.errors import SecureValueError, CONFIG_SECURE_KEY_ERROR
from uno.config.key_history import get_key_history
from uno.config.key_policy import RotationReason

T = TypeVar("T")
logger = logging.getLogger("uno.config.key_rotation")


async def rotate_secure_values(
    values: Iterable[SecureValue[T]],
    new_key_version: str,
    parallel: bool = True,
    batch_size: int = 50,
    reason: RotationReason = RotationReason.MANUAL,
) -> None:
    """
    Rotate multiple secure values to a new encryption key version.

    Args:
        values: Iterable of SecureValue instances to rotate
        new_key_version: Key version to rotate to
        parallel: If True, performs rotation in parallel (default)
        batch_size: Number of values to process in parallel (when parallel=True)
        reason: Reason for the rotation
    """
    if not values:
        logger.info("No values to rotate")
        return

    value_list = list(values)
    logger.info(
        f"Rotating {len(value_list)} secure values to key version {new_key_version}"
    )

    # Get key history instance for tracking
    key_history = get_key_history()

    # First, record the rotation in history
    current_key_version = SecureValue._current_key_version
    await key_history.record_key_rotated(
        new_key_version,
        reason,
        previous_version=current_key_version,
        details={"value_count": len(value_list)},
    )

    if parallel:
        # Process in batches to avoid overwhelming the system
        total_rotated = 0
        for i in range(0, len(value_list), batch_size):
            batch = value_list[i : i + batch_size]
            # Create rotation tasks
            tasks = []
            for value in batch:
                # We need to wrap the sync rotate_key method in an async task
                tasks.append(asyncio.create_task(_rotate_value(value, new_key_version)))
            await asyncio.gather(*tasks)
            total_rotated += len(batch)
            logger.info(f"Rotated {total_rotated}/{len(value_list)} values")
    else:
        # Process sequentially
        for i, value in enumerate(value_list):
            await _rotate_value(value, new_key_version)
            if (i + 1) % 10 == 0 or i + 1 == len(value_list):
                logger.info(f"Rotated {i + 1}/{len(value_list)} values")

    logger.info(
        f"Successfully rotated {len(value_list)} secure values to key version {new_key_version}"
    )


async def _rotate_value(value: SecureValue[T], new_key_version: str) -> None:
    """
    Helper function to rotate a single secure value.

    Args:
        value: The secure value to rotate
        new_key_version: The new key version to use
    """
    try:
        # Properly await the async rotate_key method
        await value.rotate_key(new_key_version)

        # Record usage of the key
        key_history = get_key_history()
        await key_history.record_key_used(
            new_key_version, "encrypt", {"rotation": True}
        )
    except Exception as e:
        logger.error(f"Failed to rotate value: {e}")
        raise SecureValueError(
            f"Failed to rotate secure value: {e}",
            code=CONFIG_SECURE_KEY_ERROR,
        ) from e


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
    # Get key history for tracking
    key_history = get_key_history()

    # Register the old key first (if not already registered)
    if old_version not in SecureValue._encryption_keys:
        await SecureValue.setup_encryption(
            master_key=old_key,
            key_version=old_version,
        )

        # Record the key in history if it's new
        await key_history.record_key_created(old_version, {"method": "manual_setup"})

    # Register the new key
    await SecureValue.setup_encryption(
        master_key=new_key,
        key_version=new_version,
    )

    # Record the new key creation
    await key_history.record_key_created(new_version, {"method": "key_rotation"})

    # Set the new key as current for any new encryptions
    await SecureValue.set_current_key_version(new_version)

    # Record the rotation
    await key_history.record_key_rotated(
        new_version,
        RotationReason.MANUAL,
        previous_version=old_version,
        details={"method": "manual"},
    )

    logger.info(
        f"Key rotation setup complete. New encryptions will use key version {new_version}"
    )


async def schedule_key_rotation(
    check_interval_seconds: int = 3600,
    time_based_max_days: float = 90.0,
    usage_based_max_uses: int | None = None,
) -> None:
    """
    Set up scheduled key rotation with standard policies.

    This is a convenience function that configures the scheduler with
    common policies for periodic rotation.

    Args:
        check_interval_seconds: How often to check policies (default: hourly)
        time_based_max_days: Maximum age of keys in days (default: 90)
        usage_based_max_uses: Maximum number of key uses (default: None - disabled)
    """
    from uno.config.key_policy import (
        TimeBasedRotationPolicy,
        UsageBasedRotationPolicy,
        CompositeRotationPolicy,
    )
    from uno.config.key_scheduler import get_rotation_scheduler

    # Create policies
    policies = []

    # Always add time-based policy
    time_policy = TimeBasedRotationPolicy(max_age_days=time_based_max_days)
    policies.append(time_policy)

    # Add usage-based policy if configured
    if usage_based_max_uses is not None and usage_based_max_uses > 0:
        usage_policy = UsageBasedRotationPolicy(max_uses=usage_based_max_uses)
        policies.append(usage_policy)

    # Create the scheduler
    scheduler = get_rotation_scheduler()

    # Configure with our policies
    scheduler.configure(check_interval=check_interval_seconds, policies=policies)

    # Start the scheduler
    await scheduler.start()

    logger.info(
        f"Scheduled key rotation started. Keys will be checked every {check_interval_seconds} seconds "
        f"and rotated after {time_based_max_days} days"
    )
