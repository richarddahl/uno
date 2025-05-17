"""Integration tests for Dead Letter Queue CLI commands."""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from uno.cli.main import cli
from uno.event_bus.dead_letter import DeadLetterEvent, DeadLetterReason


@pytest.fixture
def cli_runner() -> CliRunner:
    """Fixture providing a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
async def mock_dead_letter_queue() -> AsyncGenerator[AsyncMock, None]:
    """Fixture providing a mock DeadLetterQueue."""
    with patch('uno.cli.commands.dead_letter.get_dead_letter_queue') as mock_get_dlq:
        mock_queue = AsyncMock()
        mock_get_dlq.return_value = mock_queue
        yield mock_queue


class TestDeadLetterCLI:
    """Test cases for Dead Letter Queue CLI commands."""

    async def test_list_dead_letters(self, cli_runner: CliRunner, mock_dead_letter_queue: AsyncMock) -> None:
        """Test listing dead letters."""
        # Arrange
        dead_letters = [
            DeadLetterEvent(
                event_data={"type": "test_event", "data": "test1"},
                event_type="test_event",
                reason=DeadLetterReason.HANDLER_ERROR,
                error_message="Test error",
            ),
            DeadLetterEvent(
                event_data={"type": "test_event", "data": "test2"},
                event_type="test_event",
                reason=DeadLetterReason.VALIDATION_ERROR,
                error_message="Validation failed",
            ),
        ]
        mock_dead_letter_queue._queue = dead_letters

        # Act
        result = cli_runner.invoke(cli, ["dead-letter", "list"])

        # Assert
        assert result.exit_code == 0
        assert "2 dead letter(s) found" in result.output
        assert "test_event" in result.output
        assert "HANDLER_ERROR" in result.output
        assert "VALIDATION_ERROR" in result.output

    async def test_show_dead_letter(self, cli_runner: CliRunner, mock_dead_letter_queue: AsyncMock) -> None:
        """Test showing details of a specific dead letter."""
        # Arrange
        dead_letter = DeadLetterEvent(
            event_data={"type": "test_event", "data": "test"},
            event_type="test_event",
            reason=DeadLetterReason.HANDLER_ERROR,
            error_message="Test error",
            subscription_id="test-sub",
            attempt_count=2,
        )
        mock_dead_letter_queue._queue = [dead_letter]

        # Act
        result = cli_runner.invoke(cli, ["dead-letter", "show", "0"])
        
        # Assert
        assert result.exit_code == 0
        assert "test_event" in result.output
        assert "HANDLER_ERROR" in result.output
        assert "test-sub" in result.output
        assert "Attempt: 2" in result.output

    async def test_retry_dead_letter(self, cli_runner: CliRunner, mock_dead_letter_queue: AsyncMock) -> None:
        """Test retrying a dead letter."""
        # Arrange
        dead_letter = DeadLetterEvent(
            event_data={"type": "test_event", "data": "test"},
            event_type="test_event",
            reason=DeadLetterReason.HANDLER_ERROR,
        )
        mock_dead_letter_queue._queue = [dead_letter]
        mock_dead_letter_queue.process.return_value = None

        # Act
        result = cli_runner.invoke(cli, ["dead-letter", "retry", "0"], input="y\n")

        # Assert
        assert result.exit_code == 0
        assert "Retrying dead letter 0" in result.output
        mock_dead_letter_queue.process.assert_awaited_once()

    async def test_replay_dead_letters(self, cli_runner: CliRunner, mock_dead_letter_queue: AsyncMock) -> None:
        """Test replaying dead letters."""
        # Arrange
        dead_letters = [
            DeadLetterEvent(
                event_data={"type": "test_event", "data": f"test{i}"},
                event_type="test_event",
                reason=DeadLetterReason.HANDLER_ERROR,
            )
            for i in range(3)
        ]
        mock_dead_letter_queue._queue = dead_letters
        mock_dead_letter_queue.replay_events.return_value = (3, 0)  # 3 successful, 0 failed

        # Act
        result = cli_runner.invoke(
            cli,
            ["dead-letter", "replay", "--max-concurrent", "2", "--batch-size", "3"],
            input="y\n"
        )

        # Assert
        assert result.exit_code == 0
        assert "Replaying 3 dead letters" in result.output
        assert "Successfully replayed 3 events (0 failed)" in result.output
        mock_dead_letter_queue.replay_events.assert_awaited_with(
            max_concurrent=2,
            batch_size=3,
            filter_fn=Any,
            progress_callback=Any,
            stop_event=Any,
        )

    async def test_clear_dead_letters(self, cli_runner: CliRunner, mock_dead_letter_queue: AsyncMock) -> None:
        """Test clearing dead letters."""
        # Arrange
        mock_dead_letter_queue._queue = ["dummy"] * 3
        mock_dead_letter_queue.clear.return_value = 3

        # Act
        result = cli_runner.invoke(cli, ["dead-letter", "clear"], input="y\n")

        # Assert
        assert result.exit_code == 0
        assert "Cleared 3 dead letters" in result.output
        mock_dead_letter_queue.clear.assert_awaited_once()

    async def test_replay_with_filter(self, cli_runner: CliRunner, mock_dead_letter_queue: AsyncMock) -> None:
        """Test replaying with event type filter."""
        # Arrange
        mock_dead_letter_queue.replay_events.return_value = (1, 0)

        # Act
        result = cli_runner.invoke(
            cli,
            ["dead-letter", "replay", "--event-type", "test_event"],
            input="y\n"
        )

        # Assert
        assert result.exit_code == 0
        assert "Replaying dead letters of type: test_event" in result.output
        _, kwargs = mock_dead_letter_queue.replay_events.call_args
        assert kwargs["filter_fn"] is not None

    async def test_replay_dry_run(self, cli_runner: CliRunner, mock_dead_letter_queue: AsyncMock) -> None:
        """Test replay dry run."""
        # Act
        result = cli_runner.invoke(
            cli,
            ["dead-letter", "replay", "--dry-run"],
        )

        # Assert
        assert result.exit_code == 0
        assert "Dry run" in result.output
        mock_dead_letter_queue.replay_events.assert_not_called()

    async def test_replay_cancellation(self, cli_runner: CliRunner, mock_dead_letter_queue: AsyncMock) -> None:
        """Test replay cancellation."""
        # Arrange
        async def mock_replay(**kwargs: Any) -> tuple[int, int]:
            raise asyncio.CancelledError("Test cancellation")
            
        mock_dead_letter_queue.replay_events.side_effect = mock_replay

        # Act
        result = cli_runner.invoke(cli, ["dead-letter", "replay"])

        # Assert
        assert result.exit_code == 1
        assert "Replay cancelled" in result.output

    async def test_replay_progress(self, cli_runner: CliRunner, mock_dead_letter_queue: AsyncMock) -> None:
        """Test replay progress reporting."""
        # Arrange
        async def mock_replay(progress_callback: Any, **kwargs: Any) -> tuple[int, int]:
            for i in range(1, 4):
                progress_callback(i, 3)
                await asyncio.sleep(0.1)
            return (3, 0)
            
        mock_dead_letter_queue.replay_events.side_effect = mock_replay

        # Act
        result = cli_runner.invoke(cli, ["dead-letter", "replay"])

        # Assert
        assert result.exit_code == 0
        assert "Progress: 1/3" in result.output
        assert "Progress: 2/3" in result.output
        assert "Progress: 3/3" in result.output
