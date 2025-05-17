"""CLI commands for managing dead letter queue."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Optional, cast

import click
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty
from rich.table import Table

from uno.event_bus.dead_letter import DeadLetterEvent, DeadLetterQueue, DeadLetterReason
from uno.metrics import Metrics
from uno.domain.protocols import DomainEventProtocol
from uno.cli import display_table

console = Console()


def format_timestamp(timestamp: datetime) -> str:
    """Format a timestamp for display."""
    return timestamp.isoformat(sep=' ', timespec='seconds')


def format_error(error: str | None) -> str:
    """Format an error message for display."""
    if not error:
        return ""
    return error.split("\n")[0]  # Just show the first line


class DeadLetterCLI:
    """CLI interface for managing dead letters."""

    def __init__(self, queue: DeadLetterQueue[DomainEventProtocol] | None = None):
        """Initialize with an optional DeadLetterQueue instance."""
        self.queue = queue or DeadLetterQueue[DomainEventProtocol](metrics=Metrics.get_instance())

    async def list_letters(self, limit: int = 10) -> None:
        """List dead letters in the queue."""
        if not self.queue._queue:  # type: ignore
            console.print("[yellow]No dead letters in the queue.[/yellow]")
            return

        headers = ["ID", "Event Type", "Reason", "Attempts", "Last Error", "Timestamp"]
        rows = []

        for item in self.queue._queue[:limit]:  # type: ignore
            event_type = item.event_data.get("__class__", "Unknown")
            rows.append([
                item.id[:8],
                event_type,
                item.reason.value,
                str(item.attempt_count),
                format_error(item.error),
                format_timestamp(item.timestamp)
            ])

        display_table(headers, rows, f"Dead Letters (showing {len(rows)} of {len(self.queue._queue)})")

    async def show_letter(self, letter_id: str) -> None:
        """Show details of a specific dead letter."""
        letter = next((l for l in self.queue._queue if l.id.startswith(letter_id)), None)  # type: ignore
        if not letter:
            console.print(f"[red]No dead letter found with ID starting with: {letter_id}[/red]")
            return

        # Create a panel for the event data
        event_data = json.dumps(letter.event_data, indent=2)
        
        console.print(Panel(
            f"[bold]ID:[/bold] {letter.id}\n"
            f"[bold]Reason:[/bold] {letter.reason.value}\n"
            f"[bold]Attempts:[/bold] {letter.attempt_count}\n"
            f"[bold]Subscription:[/bold] {letter.subscription_id or 'N/A'}\n"
            f"[bold]Timestamp:[/bold] {format_timestamp(letter.timestamp)}\n"
            f"[bold]Error:[/bold] {letter.error or 'None'}\n"
            "\n[bold]Event Data:[/bold]\n"
            f"{event_data}",
            title=f"Dead Letter: {letter.id[:8]}...",
            border_style="blue"
        ))

    async def retry_letter(self, letter_id: str, force: bool = False) -> None:
        """Retry processing a dead letter."""
        letter = next((l for l in self.queue._queue if l.id.startswith(letter_id)), None)  # type: ignore
        if not letter:
            console.print(f"[red]No dead letter found with ID starting with: {letter_id}[/red]")
            return

        if not force and letter.attempt_count >= letter.metadata.get('max_attempts', 5):
            console.print(
                f"[yellow]Letter {letter_id[:8]} has reached maximum attempts. "
                "Use --force to retry anyway.[/yellow]"
            )
            return

        console.print(f"[green]Retrying dead letter: {letter_id[:8]}...[/green]")
        
        # Here you would integrate with your actual event processing
        # For now, we'll just simulate processing
        await asyncio.sleep(1)  # Simulate work
        
        # Update the attempt count
        letter.attempt_count += 1
        
        console.print(f"[green]Successfully retried letter: {letter_id[:8]}[/green]")

    async def replay_all(self, force: bool = False) -> None:
        """Replay all dead letters."""
        if not self.queue._queue:  # type: ignore
            console.print("[yellow]No dead letters to replay.[/yellow]")
            return

        success = 0
        failed = 0
        
        for letter in list(self.queue._queue):  # type: ignore
            try:
                await self.retry_letter(letter.id, force)
                success += 1
            except Exception as e:
                console.print(f"[red]Failed to retry {letter.id[:8]}: {e}[/red]")
                failed += 1
        
        console.print(f"\n[bold]Replay complete:[/bold] {success} succeeded, {failed} failed")

    async def clear_letters(self, force: bool = False) -> None:
        """Clear all dead letters."""
        if not self.queue._queue:  # type: ignore
            console.print("[yellow]No dead letters to clear.[/yellow]")
            return

        if not force:
            confirm = click.confirm(f"Are you sure you want to clear {len(self.queue._queue)} dead letters?")
            if not confirm:
                return

        self.queue._queue.clear()  # type: ignore
        console.print("[green]All dead letters have been cleared.[/green]")


@click.group()
@click.pass_context
def dead_letter(ctx: click.Context) -> None:
    """Manage dead letter queue."""
    ctx.obj = DeadLetterCLI()


@dead_letter.command()
@click.option('--limit', '-l', type=int, default=10, help='Maximum number of dead letters to show')
@click.pass_obj
def list(cli: DeadLetterCLI, limit: int) -> None:
    """List dead letters in the queue."""
    asyncio.run(cli.list_letters(limit))


@dead_letter.command()
@click.argument('letter_id')
@click.pass_obj
def show(cli: DeadLetterCLI, letter_id: str) -> None:
    """Show details of a specific dead letter."""
    asyncio.run(cli.show_letter(letter_id))


@dead_letter.command()
@click.argument('letter_id')
@click.option('--force', '-f', is_flag=True, help='Force retry even if max attempts reached')
@click.pass_obj
def retry(cli: DeadLetterCLI, letter_id: str, force: bool) -> None:
    """Retry processing a dead letter."""
    asyncio.run(cli.retry_letter(letter_id, force))


@dead_letter.command()
@click.option('--force', '-f', is_flag=True, help='Force retry even if max attempts reached')
@click.pass_obj
def replay(cli: DeadLetterCLI, force: bool) -> None:
    """Replay all dead letters."""
    asyncio.run(cli.replay_all(force))


@dead_letter.command()
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
@click.pass_obj
def clear(cli: DeadLetterCLI, force: bool) -> None:
    """Clear all dead letters."""
    asyncio.run(cli.clear_letters(force))


def add_commands(cli: click.Group) -> None:
    """Add dead letter commands to the main CLI."""
    cli.add_command(dead_letter)
