# Why Two PostgresEventStore Registrations

The `di.py` module contains two instances of PostgresEventStore registration for different scenarios:

1. **Primary Registration**: For when the user explicitly configures PostgreSQL (`event_store_type == "postgres"`)
   - This is the intended path when the user explicitly wants to use PostgreSQL
   - It performs validation checks like ensuring a connection string is provided

2. **Fallback Registration**: For when an unsupported event store type is specified (`else` clause)
   - It was previously defaulting to PostgreSQL with a warning message when unknown configurations were provided
   - We've updated this to fall back to InMemoryEventStore instead, which is more appropriate for unknown configuration types
   - This improves the system's ability to handle unexpected configurations

This pattern allows for graceful behavior with explicit user configuration, while providing sensible defaults for unexpected cases. By updating the fallback to use InMemoryEventStore instead of PostgreSQL, we've made the system more resilient and aligned with the principle of least surprise.
