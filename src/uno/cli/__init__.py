"""
Command-line interface for Uno framework.

This module provides command-line tools for managing various aspects of the Uno framework,
including event bus management, dead letter queue operations, and system monitoring.
"""

from typing import Optional

import click
from rich.console import Console
from rich.table import Table

console = Console()

def display_table(headers: list[str], rows: list[list[str]], title: Optional[str] = None) -> None:
    """Display tabular data in the console.
    
    Args:
        headers: List of column headers
        rows: List of rows, where each row is a list of strings
        title: Optional table title
    """
    table = Table(title=title, show_header=True, header_style="bold magenta")
    
    # Add columns
    for header in headers:
        table.add_column(header, overflow="fold")
    
    # Add rows
    for row in rows:
        table.add_row(*row)
    
    console.print(table)
