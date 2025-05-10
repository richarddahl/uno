# LoggerService Migration Scripts

This directory contains scripts for migrating from the legacy `LoggerService` to the new `LoggerProtocol` and `get_logger` based logging system in the Uno framework.

## Available Scripts

### 1. `migrate_logger_service.py`

Automatically replaces `LoggerService` with `LoggerProtocol` and `get_logger` in the codebase.

Usage:

```bash
./migrate_logger_service.py
```

This script performs the following changes:

- Updates import statements
- Updates type annotations
- Replaces constructor calls

### 2. `update_di_logger_config.py`

Updates DI container configurations to use `LoggerProtocol` instead of `LoggerService`.

Usage:

```bash
./update_di_logger_config.py
```

This script performs the following changes:

- Updates `container.register` calls to use `LoggerProtocol`
- Updates lambda functions that return `LoggerService`
- Updates factory method return type annotations

### 3. `verify_logger_migration.py`

Checks for any remaining references to `LoggerService` in the codebase.

Usage:

```bash
./verify_logger_migration.py
```

### 4. `check_di_logger_config.py`

Validates that all DI container configurations use `LoggerProtocol` instead of `LoggerService`.

Usage:

```bash
./check_di_logger_config.py
```

## Migration Process

Follow these steps to migrate your codebase:

1. **Run the migration script**:

   ```bash
   ./migrate_logger_service.py
   ```

2. **Update DI container configurations**:

   ```bash
   ./update_di_logger_config.py
   ```

3. **Verify the migration**:

   ```bash
   ./verify_logger_migration.py
   ```

4. **Check DI container configurations**:

   ```bash
   ./check_di_logger_config.py
   ```

5. **Run the tests**:

   ```bash
   cd /Users/richarddahl/Code/uno
   hatch run test:testV
   ```

## Manual Intervention

The following cases might require manual intervention:

1. Custom implementations of `LoggerService`
2. Complex DI container configurations
3. Factory methods that create `LoggerService` instances with custom logic

For more details, see the migration guide at `docs/logging/migration_guide.md`.
