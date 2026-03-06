from __future__ import annotations

import json

import typer

from clinstagram.config import ComplianceMode, save_config

config_app = typer.Typer(help="Manage configuration")


@config_app.command("show")
def show(ctx: typer.Context):
    """Print current configuration."""
    config = ctx.obj["config"]
    data = config.model_dump(mode="json")
    if ctx.obj["json"]:
        typer.echo(json.dumps(data, indent=2))
    else:
        for key, val in data.items():
            typer.echo(f"  {key}: {val}")


@config_app.command("mode")
def set_mode(ctx: typer.Context, mode: ComplianceMode = typer.Argument(...)):
    """Set compliance mode (official-only, hybrid-safe, private-enabled)."""
    config = ctx.obj["config"]
    config.compliance_mode = mode
    save_config(config, ctx.obj.get("config_dir"))
    typer.echo(f"Compliance mode set to: {mode.value}")


@config_app.command("set")
def set_value(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="Config key"),
    value: str = typer.Argument(..., help="New value"),
):
    """Set a configuration value."""
    config = ctx.obj["config"]
    if hasattr(config, key):
        setattr(config, key, value)
        save_config(config, ctx.obj.get("config_dir"))
        typer.echo(f"Set {key} = {value}")
    else:
        typer.echo(f"Unknown config key: {key}", err=True)
        raise typer.Exit(code=1)
