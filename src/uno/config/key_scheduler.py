# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# SPDX-Package-Name: uno framework
"""
Key rotation scheduler for the Uno configuration system.

This module provides a background service that automatically rotates
encryption keys based on configured policies.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, ClassVar, Coroutine

from uno.config.key_history import KeyHistory, get_key_history
from uno.config.key_policy import (
    KeyRotationPolicyProtocol,
    PolicyRegistry,
    RotationReason,
)
from uno.config.key_rotation import setup_key_rotation
from uno.config.secure import SecureValue

logger = logging.getLogger("uno.config.key_scheduler")


class KeyRotationScheduler:
    """Scheduler for automatic key rotation.

    This class runs as a background service, periodically checking key rotation
    policies and performing rotation when needed.
    """

    # Singleton pattern
    _instance: ClassVar[KeyRotationScheduler | None] = None

    @classmethod
    def get_instance(cls) -> KeyRotationScheduler:
        """Get the singleton instance.

        Returns:
            Singleton KeyRotationScheduler instance
        """
        if cls._instance is None:
            cls._instance = KeyRotationScheduler()
        return cls._instance

    def __init__(self) -> None:
        """Initialize the key rotation scheduler."""
        self._policies: list[KeyRotationPolicyProtocol] = []
        self._running = False
        self._task: asyncio.Task | None = None
        self._check_interval = 3600  # Default: check hourly
        self._key_provider: (
            Callable[[], Coroutine[Any, Any, tuple[str, bytes]]] | None
        ) = None
        self._notification_handlers: list[
            Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]
        ] = []
        self._history = get_key_history()

    def configure(
        self,
        check_interval: int = 3600,
        policies: list[KeyRotationPolicyProtocol] | None = None,
        key_provider: (
            Callable[[], Coroutine[Any, Any, tuple[str, bytes]]] | None
        ) = None,
    ) -> None:
        """Configure the scheduler.

        Args:
            check_interval: How often to check policies (in seconds)
            policies: List of policies to enforce
            key_provider: Async function that generates new keys
        """
        self._check_interval = check_interval

        if policies:
            self._policies = list(policies)

        if key_provider:
            self._key_provider = key_provider

    def add_policy(self, policy: KeyRotationPolicyProtocol) -> None:
        """Add a key rotation policy.

        Args:
            policy: The policy to add
        """
        if policy not in self._policies:
            self._policies.append(policy)
            logger.info(f"Added policy: {policy.name}")

    def remove_policy(self, policy: KeyRotationPolicyProtocol) -> None:
        """Remove a key rotation policy.

        Args:
            policy: The policy to remove
        """
        if policy in self._policies:
            self._policies.remove(policy)
            logger.info(f"Removed policy: {policy.name}")

    def add_notification_handler(
        self, handler: Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> None:
        """Add a notification handler for key rotation events.

        Args:
            handler: Async function that receives event type and details
        """
        if handler not in self._notification_handlers:
            self._notification_handlers.append(handler)

    def remove_notification_handler(
        self, handler: Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> None:
        """Remove a notification handler.

        Args:
            handler: The handler to remove
        """
        if handler in self._notification_handlers:
            self._notification_handlers.remove(handler)

    async def start(self) -> None:
        """Start the scheduler.

        This begins the background task that periodically checks
        policies and rotates keys when needed.
        """
        if self._running:
            logger.warning("Scheduler is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Key rotation scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler.

        This cancels the background task.
        """
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Key rotation scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop.

        This runs periodically, checking policies and rotating keys.
        """
        while self._running:
            try:
                logger.debug("Checking key rotation policies")
                await self._check_policies()

                # Wait until next check
                await asyncio.sleep(self._check_interval)

            except asyncio.CancelledError:
                # Allow clean cancellation
                break
            except Exception as e:
                logger.error(f"Error in key rotation scheduler: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(60)

    async def _check_policies(self) -> None:
        """Check all policies and rotate keys if needed."""
        if not self._policies:
            logger.debug("No policies configured")
            return

        # Get the current key version
        current_key_version = SecureValue._current_key_version
        if not current_key_version:
            logger.warning("No current key version, skipping policy check")
            return

        # Get key information for policy evaluation
        try:
            key_info = self._history.get_version_info(current_key_version)
        except Exception as e:
            logger.warning(f"Error getting key info: {e}")
            # Create basic info if not available
            key_info = {
                "creation_time": time.time(),
                "last_rotation_time": 0,
                "last_usage_time": 0,
                "last_check_time": time.time(),
                "usage_count": 0,
                "rotation_count": 0,
                "active": True,
            }

        # Update the check time
        await self._history.record_policy_check(
            current_key_version, "scheduler", False, {"check_time": time.time()}
        )

        # Check each policy
        for policy in self._policies:
            try:
                # Record this policy check
                policy_name = policy.name if hasattr(policy, "name") else str(policy)

                # Check if rotation is needed
                should_rotate = await policy.should_rotate(key_info)

                # Log the result
                await self._history.record_policy_check(
                    current_key_version, policy_name, should_rotate
                )

                if should_rotate:
                    logger.info(f"Policy {policy_name} triggered key rotation")
                    await self._rotate_key(policy_name)
                    return  # Exit after rotating once

            except Exception as e:
                logger.error(f"Error checking policy {policy}: {e}")

    async def _rotate_key(self, policy_name: str) -> None:
        """Rotate the encryption key.

        Args:
            policy_name: Name of the policy that triggered rotation
        """
        # Get the current key version
        current_key_version = SecureValue._current_key_version
        if not current_key_version:
            logger.error("No current key version, cannot rotate")
            return

        # Generate a new key
        new_key_version, new_key = await self._generate_key()

        # Set up rotation from old to new
        try:
            # Get the current key
            current_key = SecureValue._encryption_keys.get(current_key_version)
            if not current_key:
                logger.error("Current key not found, cannot rotate")
                return

            # Set up key rotation
            await setup_key_rotation(
                old_key=current_key,
                new_key=new_key,
                old_version=current_key_version,
                new_version=new_key_version,
            )

            # Record the rotation in history
            await self._history.record_key_rotated(
                new_key_version,
                RotationReason.SCHEDULED,
                previous_version=current_key_version,
                details={"policy": policy_name},
            )

            # Send notifications
            await self._send_notifications(
                "key_rotated",
                {
                    "new_version": new_key_version,
                    "previous_version": current_key_version,
                    "reason": RotationReason.SCHEDULED.value,
                    "policy": policy_name,
                    "timestamp": time.time(),
                },
            )

            logger.info(f"Key rotated from {current_key_version} to {new_key_version}")

        except Exception as e:
            logger.error(f"Error rotating key: {e}")

    async def _generate_key(self) -> tuple[str, bytes]:
        """Generate a new encryption key.

        Returns:
            Tuple of (version, key)
        """
        # Use custom provider if configured
        if self._key_provider:
            try:
                return await self._key_provider()
            except Exception as e:
                logger.error(f"Error using custom key provider: {e}")
                # Fall back to default implementation

        # Default implementation: generate random key with timestamp-based version
        import os
        import time

        # Generate a random 32-byte key
        key = os.urandom(32)

        # Generate a version string based on timestamp and random suffix
        timestamp = int(time.time())
        random_suffix = uuid.uuid4().hex[:6]
        version = f"v{timestamp}-{random_suffix}"

        return version, key

    async def _send_notifications(
        self, event_type: str, details: dict[str, Any]
    ) -> None:
        """Send notifications to registered handlers.

        Args:
            event_type: Type of event (key_rotated, etc.)
            details: Event details
        """
        if not self._notification_handlers:
            return

        # Create tasks for all handlers
        tasks = []
        for handler in self._notification_handlers:
            try:
                task = asyncio.create_task(handler(event_type, details))
                tasks.append(task)
            except Exception as e:
                logger.error(f"Error creating notification task: {e}")

        # Wait for all tasks to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# Singleton instance accessor
def get_rotation_scheduler() -> KeyRotationScheduler:
    """Get the key rotation scheduler singleton.

    Returns:
        KeyRotationScheduler singleton instance
    """
    return KeyRotationScheduler.get_instance()
