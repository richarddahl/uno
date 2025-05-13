"""
Uno CLI Entrypoint (Scaffold)

Provides code generation, diagnostics, and admin commands for Uno projects.
"""

import typer

# NOTE: log_admin is no longer re-exported from uno.cli to avoid circular imports.
# Please import from uno.cli.log_admin directly in tests and code.

app = typer.Typer(help="Uno CLI: codegen, diagnostics, and admin tools.")


@app.command()
def generate_aggregate(name: str) -> None:
    """Generate a new aggregate class in examples/app/domain/NAME.py."""
    from pathlib import Path

    domain_dir = Path(__file__).parent.parent / "examples" / "app" / "domain"
    file_path = domain_dir / f"{name.lower()}.py"
    if file_path.exists():
        typer.secho(f"File {file_path} already exists!", fg=typer.colors.RED)
        raise typer.Exit(1)
    code = f'''"""
Aggregate: {name}
"""
from uno.domain.aggregate import AggregateRoot
from uno.events.base import DomainEvent

class {name}(AggregateRoot):
    """Aggregate root for {name}."""
    # Add fields and methods here
    pass
'''
    file_path.write_text(code)
    typer.secho(f"Aggregate scaffolded: {file_path}", fg=typer.colors.GREEN)


@app.command()
def generate_event(name: str) -> None:
    """Generate a new event class in examples/app/domain/NAME_event.py."""
    from pathlib import Path

    domain_dir = Path(__file__).parent.parent / "examples" / "app" / "domain"
    file_path = domain_dir / f"{name.lower()}_event.py"
    if file_path.exists():
        typer.secho(f"File {file_path} already exists!", fg=typer.colors.RED)
        raise typer.Exit(1)
    code = f'''"""
Domain Event: {name}
"""
from uno.events.base import DomainEvent

class {name}(DomainEvent):
    """Domain event for {name}."""
    # Add event fields here
    pass
'''
    file_path.write_text(code)
    typer.secho(f"Event scaffolded: {file_path}", fg=typer.colors.GREEN)


@app.command()
def logging_config_show(ctx: typer.Context) -> None:
    """Show current Uno logging configuration."""
    try:
        from uno.logging.config_service import LoggingConfigService
        from uno.logging.factory import create_logger_factory

        factory = create_logger_factory()
        logger_service = factory.create("cli")
        config_service = LoggingConfigService(logger_service)
        config = config_service.get_config()
        typer.echo("Current Uno Logging Config:")
        for k, v in config.model_dump().items():
            typer.echo(f"  {k}: {v}")
    except Exception as e:
        typer.secho(f"Could not load logging config: {e}", fg=typer.colors.RED)


if __name__ == "__main__":
    app()
