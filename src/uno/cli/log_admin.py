"""
CLI for Uno Logging Configuration Admin

Allows inspection and runtime update of logging configuration using LoggingConfigService.
"""

import typer
from uno.core.logging.config_service import LoggingConfigService
from uno.core.logging.factory import create_logger_factory
from uno.core.logging.logger import LoggingConfig

app = typer.Typer(help="Uno Logging Configuration Admin CLI")

class CLIContext:
    def __init__(self):
        # Use the DI factory for logger service
        factory = create_logger_factory()
        self.logger_service = factory.create("cli")
        self.config_service = LoggingConfigService(self.logger_service)

@app.callback()
def main(ctx: typer.Context):
    """Initialize CLI context with DI logger and config services."""
    ctx.obj = CLIContext()

@app.command()
def get_field(ctx: typer.Context, field: str):
    """Show the value of a specific logging config field."""
    config_service = ctx.obj.config_service
    config = config_service.get_config()
    value = getattr(config, field, None)
    if value is None:
        typer.echo(f"Field '{field}' not found in logging config.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"{field}: {value}")

@app.command()
def schema(ctx: typer.Context):
    """Show the logging config schema (fields, types, defaults)."""
    import json
    typer.echo(json.dumps(LoggingConfig.model_json_schema(), indent=2))

@app.command()
def restore_defaults(ctx: typer.Context):
    """Restore logging config to defaults (dev environment)."""
    from uno.core.logging.logger import Dev
    config_service = ctx.obj.config_service
    logger_service = ctx.obj.logger_service
    config = Dev()
    logger_service._config = config
    logger_service._configure_root_logger()
    typer.echo("Restored logging config to development defaults:")
    typer.echo(config.model_dump_json(indent=2))

@app.command()
def validate(ctx: typer.Context):
    """Validate the current logging config (prints errors if invalid)."""
    config_service = ctx.obj.config_service
    try:
        config = config_service.get_config()
        config.model_validate(config.model_dump())
        typer.echo("Logging config is valid.")
    except Exception as exc:
        typer.echo(f"Logging config is INVALID: {exc}", err=True)
        raise typer.Exit(code=2) from exc

@app.command()
def show(ctx: typer.Context):
    """Show the current logging configuration."""
    config_service = ctx.obj.config_service
    config = config_service.get_config()
    typer.echo(config.model_dump_json(indent=2))

@app.command()
def set(
    ctx: typer.Context,
    level: str | None = typer.Option(None, help="Set the log level (e.g. INFO, DEBUG, ERROR)"),
    json_format: bool = typer.Option(None, "--json-format/--no-json-format", help="Enable/disable JSON log output"),
    console_output: bool = typer.Option(None, "--console-output/--no-console-output", help="Enable/disable console output"),
    file_output: bool = typer.Option(None, "--file-output/--no-file-output", help="Enable/disable file output"),
    file_path: str | None = typer.Option(None, help="Set log file path"),
):
    """Update logging configuration at runtime."""
    config_service = ctx.obj.config_service
    update = {}
    if level is not None:
        update["LEVEL"] = level
    if json_format is not None:
        update["JSON_FORMAT"] = json_format
    if console_output is not None:
        update["CONSOLE_OUTPUT"] = console_output
    if file_output is not None:
        update["FILE_OUTPUT"] = file_output
    if file_path is not None:
        update["FILE_PATH"] = file_path
    if not update:
        typer.echo("No config fields provided to update.", err=True)
        raise typer.Exit(code=1)
    try:
        config = config_service.update_config(**update)
        typer.echo("Updated logging configuration:")
        typer.echo(config.model_dump_json(indent=2))
    except Exception as exc:
        typer.echo(f"Error updating logging config: {exc}", err=True)
        raise typer.Exit(code=2)

if __name__ == "__main__":
    app()
