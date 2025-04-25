"""
CLI for Uno Logging Configuration Admin

Allows inspection and runtime update of logging configuration using LoggingConfigService.
"""

import typer

from uno.core.logging.config_service import LoggingConfigService
from uno.core.logging.logger import LoggerService, LoggingConfig

app = typer.Typer(help="Uno Logging Configuration Admin CLI")

@app.command()
def get_field(field: str):
    """Show the value of a specific logging config field."""
    logger_service = LoggerService(LoggingConfig())
    config_service = LoggingConfigService(logger_service)
    config = config_service.get_config()
    value = getattr(config, field, None)
    if value is None:
        typer.echo(f"Field '{field}' not found in logging config.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"{field}: {value}")

@app.command()
def schema():
    """Show the logging config schema (fields, types, defaults)."""
    import json

    from uno.core.logging.logger import LoggingConfig
    typer.echo(json.dumps(LoggingConfig.model_json_schema(), indent=2))

@app.command()
def restore_defaults():
    """Restore logging config to defaults (dev environment)."""
    logger_service = LoggerService(LoggingConfig())
    from uno.core.logging.logger import Dev
    config_service = LoggingConfigService(logger_service)
    config = Dev()
    logger_service._config = config
    logger_service._configure_root_logger()
    typer.echo("Restored logging config to development defaults:")
    typer.echo(config.model_dump_json(indent=2))

@app.command()
def validate():
    """Validate the current logging config (prints errors if invalid)."""
    logger_service = LoggerService(LoggingConfig())
    config_service = LoggingConfigService(logger_service)
    try:
        config = config_service.get_config()
        config.model_validate(config.model_dump())
        typer.echo("Logging config is valid.")
    except Exception as exc:
        typer.echo(f"Logging config is INVALID: {exc}", err=True)
        raise typer.Exit(code=2)

@app.command()
def show():
    """Show the current logging configuration."""
    logger_service = LoggerService(LoggingConfig())
    config_service = LoggingConfigService(logger_service)
    config = config_service.get_config()
    typer.echo(config.model_dump_json(indent=2))

@app.command()
def set(
    level: str | None = typer.Option(None, help="Set the log level (e.g. INFO, DEBUG, ERROR)"),
    json_format: bool = typer.Option(None, "--json-format/--no-json-format", help="Enable/disable JSON log output"),
    console_output: bool = typer.Option(None, "--console-output/--no-console-output", help="Enable/disable console output"),
    file_output: bool = typer.Option(None, "--file-output/--no-file-output", help="Enable/disable file output"),
    file_path: str | None = typer.Option(None, help="Set log file path"),
):
    """Update logging configuration at runtime."""
    logger_service = LoggerService(LoggingConfig())
    config_service = LoggingConfigService(logger_service)
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
