from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from clinstagram.auth.keychain import SecretsStore

console = Console()
auth_app = typer.Typer(help="Manage authentication (Graph & Private)")


def _get_secrets(ctx: typer.Context) -> SecretsStore:
    if "secrets" in ctx.obj:
        return ctx.obj["secrets"]
    return SecretsStore(backend="keyring")


@auth_app.command("status")
def status(ctx: typer.Context):
    """Show authentication status for the current account."""
    account = ctx.obj["account"]
    config = ctx.obj["config"]
    secrets = _get_secrets(ctx)

    backends = {}
    for name in ["graph_ig", "graph_fb", "private"]:
        backends[name] = secrets.has_backend(account, name)

    result = {
        "account": account,
        "compliance_mode": config.compliance_mode.value,
        "backends": backends,
    }

    if ctx.obj["json"]:
        typer.echo(json.dumps(result, indent=2))
    else:
        table = Table(title=f"Auth Status: {account}")
        table.add_column("Backend", style="cyan")
        table.add_column("Status", style="green")
        for name, active in backends.items():
            table.add_row(name, "Active" if active else "Not configured")
        console.print(table)
        console.print(f"Compliance mode: [bold]{config.compliance_mode.value}[/bold]")


@auth_app.command("connect-ig")
def connect_ig(ctx: typer.Context):
    """Connect via Instagram Login (OAuth). Enables posting, comments, analytics."""
    typer.echo("Instagram Login OAuth flow — coming in Phase 2.")
    raise typer.Exit(code=1)


@auth_app.command("connect-fb")
def connect_fb(ctx: typer.Context):
    """Connect via Facebook Login (OAuth + Page). Enables DMs, webhooks."""
    typer.echo("Facebook Login OAuth flow — coming in Phase 2.")
    raise typer.Exit(code=1)


@auth_app.command("login")
def login(ctx: typer.Context):
    """Login via Private API (instagrapi). Username/password/2FA."""
    typer.echo("Private API login flow — coming in Phase 2.")
    raise typer.Exit(code=1)


@auth_app.command("probe")
def probe(ctx: typer.Context):
    """Test all backends and report available features."""
    account = ctx.obj["account"]
    secrets = _get_secrets(ctx)
    result = {"account": account, "backends": {}}
    for name in ["graph_ig", "graph_fb", "private"]:
        result["backends"][name] = {"active": secrets.has_backend(account, name)}
    if ctx.obj["json"]:
        typer.echo(json.dumps(result, indent=2))
    else:
        for name, info in result["backends"].items():
            s = "Active" if info["active"] else "Not configured"
            typer.echo(f"  {name}: {s}")


@auth_app.command("logout")
def logout(
    ctx: typer.Context,
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clear stored sessions for the current account."""
    if not confirm:
        typer.confirm("Clear all stored sessions?", abort=True)
    account = ctx.obj["account"]
    secrets = _get_secrets(ctx)
    for name in ["graph_ig_token", "graph_fb_token", "private_session"]:
        secrets.delete(account, name)
    typer.echo(f"Cleared sessions for account: {account}")
