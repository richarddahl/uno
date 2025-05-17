"""Performance benchmarks for Dead Letter Queue event replay functionality."""
from __future__ import annotations

import asyncio
import time
from typing import Any, Callable

import pytest
from rich.console import Console
from rich.table import Table

from uno.event_bus.dead_letter import DeadLetterEvent, DeadLetterQueue, DeadLetterReason
from uno.event_bus.event import Event

# Constants for benchmark configuration
EVENT_COUNTS = [100, 1_000, 10_000]  # Number of events to test
CONCURRENCY_LEVELS = [1, 4, 8]        # Concurrent workers to test
BATCH_SIZES = [10, 100, 1_000]        # Batch sizes to test


class TestEvent(Event):
    """Test event for benchmarking."""
    
    def __init__(self, data: str) -> None:
        """Initialize with test data."""
        self.data = data
        super().__init__()


async def create_test_events(
    count: int,
    reason: DeadLetterReason = DeadLetterReason.HANDLER_ERROR
) -> list[DeadLetterEvent]:
    """Create test dead letter events."""
    return [
        DeadLetterEvent(
            event_data=TestEvent(f"test_{i}"),
            event_type="test_event",
            reason=reason,
            error_message=f"Error {i}",
            attempt_count=1,
        )
        for i in range(count)
    ]


class EventReplayBenchmark:
    """Benchmark suite for event replay functionality."""
    
    def __init__(self) -> None:
        """Initialize the benchmark suite."""
        self.console = Console()
        self.results: list[dict[str, Any]] = []
    
    async def run_benchmark(
        self,
        event_counts: list[int] = None,
        concurrency_levels: list[int] = None,
        batch_sizes: list[int] = None,
    ) -> None:
        """Run the benchmark with the given parameters."""
        event_counts = event_counts or EVENT_COUNTS
        concurrency_levels = concurrency_levels or CONCURRENCY_LEVELS
        batch_sizes = batch_sizes or BATCH_SIZES
        
        self.console.print("\n[bold blue]Starting Event Replay Benchmark[/]\n")
        
        for count in event_counts:
            for concurrency in concurrency_levels:
                for batch_size in batch_sizes:
                    if batch_size > count:
                        continue
                        
                    await self._run_single_benchmark(
                        event_count=count,
                        concurrency=concurrency,
                        batch_size=batch_size,
                    )
        
        self._print_results()
    
    async def _run_single_benchmark(
        self,
        event_count: int,
        concurrency: int,
        batch_size: int,
    ) -> None:
        """Run a single benchmark iteration."""
        # Create test events
        events = await create_test_events(event_count)
        
        # Create a test dead letter queue
        dlq = DeadLetterQueue[TestEvent]()
        await dlq._clear()  # Clear any existing events
        
        # Add events to the queue
        for event in events:
            await dlq.add(event.event_data, event.reason, Exception(event.error_message))
        
        # Warm-up run
        await dlq.replay_events(
            max_concurrent=concurrency,
            batch_size=batch_size,
            dry_run=True
        )
        
        # Run the benchmark
        start_time = time.monotonic()
        
        success, failed = await dlq.replay_events(
            max_concurrent=concurrency,
            batch_size=batch_size,
        )
        
        duration = time.monotonic() - start_time
        events_per_second = event_count / duration if duration > 0 else 0
        
        # Store results
        result = {
            "events": event_count,
            "concurrency": concurrency,
            "batch_size": batch_size,
            "duration": duration,
            "events_per_second": events_per_second,
            "success": success,
            "failed": failed,
        }
        
        self.results.append(result)
        
        self.console.print(
            f"Events: {event_count:6,d} | "
            f"Concurrency: {concurrency:2d} | "
            f"Batch: {batch_size:4d} | "
            f"Time: {duration:.3f}s | "
            f"Rate: {events_per_second:,.0f} events/s"
        )
    
    def _print_results(self) -> None:
        """Print the benchmark results in a formatted table."""
        if not self.results:
            return
        
        # Sort by events, then concurrency, then batch size
        sorted_results = sorted(
            self.results,
            key=lambda x: (x["events"], x["concurrency"], x["batch_size"])
        )
        
        table = Table(title="Event Replay Benchmark Results", show_header=True, header_style="bold magenta")
        
        # Add columns
        table.add_column("Events", justify="right")
        table.add_column("Concurrency", justify="center")
        table.add_column("Batch Size", justify="right")
        table.add_column("Duration (s)", justify="right")
        table.add_column("Events/s", justify="right")
        table.add_column("Success", justify="right")
        table.add_column("Failed", justify="right")
        
        # Add rows
        for result in sorted_results:
            table.add_row(
                f"{result['events']:,}",
                str(result["concurrency"]),
                f"{result['batch_size']:,}",
                f"{result['duration']:.3f}",
                f"{result['events_per_second']:,.0f}",
                f"{result['success']:,}",
                f"{result['failed']:,}",
            )
        
        self.console.print("\n" + "=" * 80)
        self.console.print("[bold green]Benchmark Complete[/]")
        self.console.print("=" * 80 + "\n")
        self.console.print(table)
        
        # Print summary
        fastest = max(self.results, key=lambda x: x["events_per_second"])
        self.console.print(
            "\n[bold]Fastest Configuration:[/]\n"
            f"• {fastest['events']:,} events with {fastest['concurrency']} workers "
            f"and batch size {fastest['batch_size']:,}\n"
            f"• {fastest['events_per_second']:,.0f} events/second\n"
        )


@pytest.mark.benchmark
async def test_event_replay_benchmark() -> None:
    """Run the event replay benchmark."""
    benchmark = EventReplayBenchmark()
    await benchmark.run_benchmark(
        event_counts=[100, 1_000],  # Reduced for CI/CD
        concurrency_levels=[1, 4],   # Reduced for CI/CD
        batch_sizes=[10, 100],       # Reduced for CI/CD
    )


if __name__ == "__main__":
    # Run the benchmark directly with: python -m benchmarks.event_replay_benchmark
    import sys
    import asyncio
    
    benchmark = EventReplayBenchmark()
    
    # Use command line args if provided, else use defaults
    if len(sys.argv) > 1:
        event_counts = [int(x) for x in sys.argv[1].split(",")]
        concurrency_levels = [int(x) for x in sys.argv[2].split(",")]
        batch_sizes = [int(x) for x in sys.argv[3].split(",")]
        asyncio.run(benchmark.run_benchmark(event_counts, concurrency_levels, batch_sizes))
    else:
        asyncio.run(benchmark.run_benchmark())
