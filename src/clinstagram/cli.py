from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import typer

from clinstagram import __version__
from clinstagram.config import BackendType, load_config

app = typer.Typer(
    name="clinstagram",
    help="Hybrid Instagram CLI for OpenClaw — Graph API + Private API",
    no_args_is_help=True,
    context_settings={"allow_interspersed_args": True},
)


def _version_callback(value: bool):
    if value:
        typer.echo(f"clinstagram {__version__}")
        raise typer.Exit()


def _resolve_config_dir() -> Optional[Path]:
    env = os.environ.get("CLINSTAGRAM_CONFIG_DIR")
    return Path(env) if env else None


@app.callback()
def main(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    account: str = typer.Option("default", "--account", help="Account name"),
    backend: BackendType = typer.Option(BackendType.AUTO, "--backend", help="Force backend"),
    proxy: Optional[str] = typer.Option(None, "--proxy", help="Proxy URL for private API"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen"),
    verbose: bool = typer.Option(False, "--verbose", help="Debug logging"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable color output"),
    enable_growth: bool = typer.Option(
        False, "--enable-growth-actions", help="Unlock follow/unfollow"
    ),
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True
    ),
):
    config_dir = _resolve_config_dir()
    if not json_output and not sys.stdout.isatty():
        json_output = True
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output
    ctx.obj["account"] = account
    ctx.obj["backend"] = backend
    ctx.obj["proxy"] = proxy
    ctx.obj["dry_run"] = dry_run
    ctx.obj["verbose"] = verbose
    ctx.obj["no_color"] = no_color
    ctx.obj["enable_growth"] = enable_growth
    ctx.obj["config_dir"] = config_dir
    ctx.obj["config"] = load_config(config_dir)
    # Use memory-backed secrets when config dir is overridden (tests/CI)
    if config_dir is not None:
        from clinstagram.auth.keychain import SecretsStore

        ctx.obj["secrets"] = SecretsStore(backend="memory")


# Register command groups
from clinstagram.commands.auth import auth_app  # noqa: E402
from clinstagram.commands.config_cmd import config_app  # noqa: E402

app.add_typer(auth_app, name="auth")
app.add_typer(config_app, name="config")


# Placeholder groups for future phases
def _make_placeholder(group_help: str) -> typer.Typer:
    sub = typer.Typer(help=group_help)

    @sub.command("help")
    def _placeholder(ctx: typer.Context):
        """Coming in a future phase."""
        typer.echo("Commands for this group are not yet implemented.")

    return sub


for _name, _help in [
    ("post", "Post photos, videos, reels"),
    ("dm", "Manage direct messages"),
    ("story", "Manage stories"),
    ("comments", "Manage comments"),
    ("analytics", "View analytics"),
    ("followers", "Manage followers"),
    ("user", "User lookup"),
]:
    app.add_typer(_make_placeholder(_help), name=_name)
