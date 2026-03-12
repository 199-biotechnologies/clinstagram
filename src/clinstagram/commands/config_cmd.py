from __future__ import annotations

import typer

from clinstagram.commands._dispatch import make_subgroup, output_error, output_success
from clinstagram.config import ComplianceMode, save_config
from clinstagram.models import CLIError, ExitCode

config_app = make_subgroup("Manage configuration")


@config_app.command("show")
def show(ctx: typer.Context):
    """Print current configuration."""
    config = ctx.obj["config"]
    data = config.model_dump(mode="json")
    if not ctx.obj["json"]:
        for key, val in data.items():
            typer.echo(f"  {key}: {val}")
        return
    output_success(ctx, data)


@config_app.command("mode")
def set_mode(ctx: typer.Context, mode: ComplianceMode = typer.Argument(...)):
    """Set compliance mode (official-only, hybrid-safe, private-enabled)."""
    config = ctx.obj["config"]
    config.compliance_mode = mode
    save_config(config, ctx.obj.get("config_dir"))
    if not ctx.obj["json"]:
        typer.echo(f"Compliance mode set to: {mode.value}")
        return
    output_success(ctx, {"compliance_mode": mode.value})


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
        if not ctx.obj["json"]:
            typer.echo(f"Set {key} = {value}")
            return
        output_success(ctx, {"key": key, "value": value})
    else:
        output_error(
            ctx,
            CLIError(
                exit_code=ExitCode.USER_ERROR,
                error=f"Unknown config key: {key}",
                remediation="Run: clinstagram --json config show",
            ),
        )
