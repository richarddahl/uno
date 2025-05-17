"""Main CLI entry point for Uno framework."""
from __future__ import annotations

import click
from typing import Optional

from .commands import dead_letter

@click.group()
@click.version_option()
def cli() -> None:
    """Uno - A modern Python framework for building scalable applications."""
    pass

# Register command groups
dead_letter.add_commands(cli)

def main() -> None:
    """Entry point for the CLI."""
    cli()

if __name__ == "__main__":
    main()
