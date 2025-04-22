# Uno Framework Dependency Injection

This directory implements a comprehensive dependency injection system for the Uno framework, 
featuring scoped service resolution, interface-based contracts, and both sync and async context management.

## Terminology Note

> **Note:** In this documentation, the term "service" refers to any class or object managed by the dependency injection (DI) container, such as repositories, loggers, or domain services. This usage is standard in DI frameworks. In contrast, in Domain-Driven Design (DDD), a "domain service" is a specific pattern for encapsulating domain logic that doesn't naturally fit within an Entity or Value Object. If you are building DDD-style applications, be mindful of this distinction: "service" in the DI context is a broader term and may include both domain and infrastructure-level components.

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