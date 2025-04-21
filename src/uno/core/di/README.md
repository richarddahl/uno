# Uno Framework Dependency Injection

This directory implements a comprehensive dependency injection system for the Uno framework, 
featuring scoped service resolution, interface-based contracts, and both sync and async context management.

## Key Features

- Singleton, Scoped, and Transient service lifetimes
- Protocol-based interface definitions for loose coupling
- Automatic dependency resolution
- Context managers for proper resource disposal
- Support for both synchronous and asynchronous operations

## Basic Usage

```python
# Register services
services = ServiceCollection()
services.add_singleton(Logger, ConsoleLogger)
services.add_scoped(Database, PostgresDatabase)
services.add_transient(EmailSender)

# Initialize the container
ServiceContainer.initialize(services)

# Anywhere in your code:
logger = ServiceContainer.resolve(Logger)
logger.info("DI system initialized")

# Using scoped services
with ServiceContainer.create_scope() as scope:
    db = scope.resolve(Database)
    # db is scoped to this context and will be properly disposed