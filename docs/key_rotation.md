# Key Rotation in Uno

## Overview

The Uno framework provides a robust key rotation system for securing sensitive configuration values. Key rotation is an essential security practice that helps protect encrypted data by periodically changing the encryption keys. This limits the amount of data encrypted with any single key, reducing the impact of potential key compromise.

The key rotation system in Uno includes:

1. **Policy-based rotation** - Configure when keys should be rotated based on time, usage, or custom conditions
2. **Automated scheduling** - Schedule automatic key rotation with configurable policies
3. **Comprehensive audit trail** - Track all key events including creation, rotation, and usage
4. **Custom key providers** - Integrate with external key management systems

## Basic Key Rotation

The simplest way to perform key rotation is to use the `setup_key_rotation` function, which manages the transition from an old key to a new key:

```python
from uno.config import setup_key_rotation

# Rotate from old key to new key
await setup_key_rotation(
    old_key="your-old-master-key",
    new_key="your-new-master-key",
    old_version="v1",
    new_version="v2"
)
```

This function:

1. Registers both old and new keys
2. Sets the new key as the current one for new encryptions
3. Records the rotation in the key history

## Rotating Secure Values

After setting up a new key, you can rotate specific `SecureValue` instances to use the new key:

```python
from uno.config import rotate_secure_values, RotationReason

# Collect all secure values that need rotation
secure_values = [config.api_key, config.database_password, config.token]

# Rotate all values to the new key
await rotate_secure_values(
    values=secure_values,
    new_key_version="v2",
    parallel=True,  # Process in parallel for better performance
    reason=RotationReason.MANUAL  # Record reason for audit
)
```

## Automated Key Rotation

For production systems, automated key rotation is recommended. The Uno framework provides a scheduler that can automatically rotate keys based on policies:

```python
from uno.config import schedule_key_rotation

# Set up automated rotation every 90 days
await schedule_key_rotation(
    check_interval_seconds=3600,  # Check policies hourly
    time_based_max_days=90.0,     # Rotate keys every 90 days
    usage_based_max_uses=1000000  # Also rotate after 1 million uses
)
```

### Custom Key Rotation Policies

You can create custom rotation policies by combining existing ones or implementing entirely new ones:

```python
from uno.config import (
    TimeBasedRotationPolicy,
    UsageBasedRotationPolicy,
    CompositeRotationPolicy,
    get_rotation_scheduler
)

# Create a policy that rotates keys after 30 days OR 500,000 uses
time_policy = TimeBasedRotationPolicy(max_age_days=30.0)
usage_policy = UsageBasedRotationPolicy(max_uses=500000)
composite_policy = CompositeRotationPolicy(
    policies=[time_policy, usage_policy],
    require_all=False  # OR logic - any policy can trigger rotation
)

# Get the scheduler and configure it
scheduler = get_rotation_scheduler()
scheduler.configure(
    check_interval=3600,  # Check hourly
    policies=[composite_policy]
)

# Start the scheduler
await scheduler.start()
```

### Scheduled Rotation Policy

For compliance scenarios that require rotation on specific dates or times:

```python
from uno.config import ScheduledRotationPolicy, get_rotation_scheduler

# Create a policy that rotates keys on the first day of each month at 2 AM
monthly_policy = ScheduledRotationPolicy(
    schedule_type="monthly",
    day_of_month=1,
    hour=2,
    minute=0
)

# Configure the scheduler
scheduler = get_rotation_scheduler()
scheduler.configure(
    check_interval=3600,
    policies=[monthly_policy]
)

# Start the scheduler
await scheduler.start()
```

## Key Rotation Notifications

You can register notification handlers to be informed when key rotation occurs:

```python
from uno.config import get_rotation_scheduler

# Define a notification handler
async def key_rotation_handler(event_type: str, details: dict) -> None:
    if event_type == "key_rotated":
        print(f"Key rotated from {details['previous_version']} to {details['new_version']}")
        # Send notification email, log to security system, etc.

# Register the handler with the scheduler
scheduler = get_rotation_scheduler()
scheduler.add_notification_handler(key_rotation_handler)
```

## Using Custom Key Providers

For integration with external key management systems, you can provide a custom key generation function:

```python
from uno.config import get_rotation_scheduler
import os

# Define a custom key provider
async def aws_kms_key_provider() -> tuple[str, bytes]:
    # In a real implementation, this would call AWS KMS
    # to generate or retrieve a key
    import boto3
    
    # Generate a key using AWS KMS
    kms = boto3.client('kms')
    response = await kms.generate_data_key(
        KeyId='alias/my-key',
        KeySpec='AES_256'
    )
    
    # Create a version identifier
    import uuid
    version = f"kms-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    
    # Return the version and key
    return version, response['Plaintext']

# Configure the scheduler with the custom provider
scheduler = get_rotation_scheduler()
scheduler.configure(
    key_provider=aws_kms_key_provider
)
```

## Key History and Auditing

Uno maintains a comprehensive history of all key-related events, which is useful for auditing and compliance:

```python
from uno.config import get_key_history

# Get the key history tracker
history = get_key_history()

# Configure history storage
history.configure(
    storage_path="/secure/path/to/key_history",
    persist=True,  # Save history to disk
    max_events=10000  # Keep the 10,000 most recent events in memory
)

# Get all rotation events for a specific key
rotation_events = history.get_events(
    key_version="v2",
    event_type="rotation",
    limit=100
)

# Get version-specific information
v2_info = history.get_version_info("v2")
print(f"Key v2 created: {datetime.fromtimestamp(v2_info['creation_time'])}")
print(f"Key v2 usage count: {v2_info['usage_count']}")

# Get all active keys
active_keys = history.get_active_key_versions()
```

## Best Practices

1. **Rotation Frequency**: Rotate keys every 90 days (or as required by your compliance requirements)
2. **Automated Rotation**: Use scheduled, automated rotation for production systems
3. **Monitoring**: Set up notification handlers to alert security teams of rotation events
4. **Secure Storage**: Store key history securely with appropriate access controls
5. **Policy Combination**: Use composite policies that consider both time and usage
6. **External Key Management**: For highest security, integrate with an external key management service

## Troubleshooting

If you encounter issues with key rotation, check the following:

1. **Key History**: Review the key history to see if there are any errors during rotation
2. **Verify Policies**: Ensure policies are configured correctly and appropriate for your needs
3. **Check Scheduler**: Make sure the scheduler is running and checking policies at the expected interval
4. **Monitor Usage**: Very high usage counts might indicate excessive encryption operations
