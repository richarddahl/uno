# Uno CLI - Dead Letter Queue Management

The Uno CLI provides command-line tools for managing the Dead Letter Queue (DLQ) in the Uno event system.

## Installation

After installing the `uno` package, the CLI will be available as the `uno` command:

```bash
pip install -e .
```

## Available Commands

### List Dead Letters

List all dead letters in the queue:

```bash
uno dead-letter list [--limit N]
```

Options:
- `--limit`, `-l`: Maximum number of dead letters to show (default: 10)

### Show Dead Letter Details

Show detailed information about a specific dead letter:

```bash
uno dead-letter show <letter_id>
```

### Retry a Dead Letter

Retry processing a specific dead letter:

```bash
uno dead-letter retry <letter_id> [--force]
```

Options:
- `--force`, `-f`: Force retry even if max attempts reached

### Replay All Dead Letters

Retry processing all dead letters in the queue:

```bash
uno dead-letter replay [--force]
```

Options:
- `--force`, `-f`: Force retry even if max attempts reached

### Clear All Dead Letters

Remove all dead letters from the queue:

```bash
uno dead-letter clear [--force]
```

Options:
- `--force`, `-f`: Skip confirmation prompt

## Examples

1. List the 5 most recent dead letters:
   ```bash
   uno dead-letter list --limit 5
   ```

2. Show details of a specific dead letter:
   ```bash
   uno dead-letter show abc123
   ```

3. Retry a failed event:
   ```bash
   uno dead-letter retry abc123
   ```

4. Replay all dead letters:
   ```bash
   uno dead-letter replay
   ```

5. Clear all dead letters without confirmation:
   ```bash
   uno dead-letter clear --force
   ```

## Error Handling

- If a dead letter cannot be processed, it will remain in the queue with an incremented attempt count
- Dead letters that exceed the maximum number of attempts will be skipped unless `--force` is used
- All operations are logged for auditing purposes

## Integration

The CLI integrates with the `unometrics` system to provide metrics about dead letter operations. You can monitor these metrics to track the health of your event processing system.
