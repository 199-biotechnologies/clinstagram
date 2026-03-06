from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from clinstagram.auth.keychain import SecretsStore
from clinstagram.commands._dispatch import make_subgroup

console = Console()
auth_app = make_subgroup("Manage authentication (Graph & Private)")


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
def login(
    ctx: typer.Context,
    username: str = typer.Option(..., "--username", "-u", prompt=True, help="Instagram username, email, or phone number"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Instagram password (prompted if needed)"),
    totp_seed: str = typer.Option("", "--totp-seed", help="TOTP seed for 2FA (base32)"),
    proxy: str = typer.Option("", "--proxy", help="Proxy URL (recommended for private API)"),
    locale: str = typer.Option("", "--locale", help="Locale (e.g. en_GB, pt_BR). Auto-detected if omitted"),
    timezone: str = typer.Option("", "--timezone", help="Timezone offset in seconds (e.g. 0). Auto-detected if omitted"),
    delay_min: int = typer.Option(1, "--delay-min", help="Min delay between actions (seconds)"),
    delay_max: int = typer.Option(3, "--delay-max", help="Max delay between actions (seconds)"),
):
    """Login via Private API (instagrapi). Accepts username, email, or phone."""
    from clinstagram.auth.private_login import LoginConfig, login_private

    account = ctx.obj["account"]
    secrets = _get_secrets(ctx)

    # Check for existing session
    existing_session = secrets.get(account, "private_session") or ""
    
    # Prompt for password if not provided AND no session exists
    effective_password = password
    if not effective_password and not existing_session:
        effective_password = typer.prompt("Instagram password", hide_input=True)

    # Warn about missing proxy
    effective_proxy = proxy or ctx.obj.get("proxy", "")
    if not effective_proxy and not ctx.obj["json"]:
        console.print("[yellow]Warning:[/yellow] No proxy set. Instagram may flag your IP.")
        console.print("  Use --proxy or set proxy in config.toml for safety.")

    config = LoginConfig(
        username=username,
        password=effective_password or "",
        totp_seed=totp_seed,
        proxy=effective_proxy,
        locale=locale,
        timezone=timezone,
        delay_range=[delay_min, delay_max],
    )

    result = login_private(config, existing_session=existing_session)

    if result.success:
        # Store session in keychain
        secrets.set(account, "private_session", result.session_json)

        if ctx.obj["json"]:
            typer.echo(json.dumps({
                "status": "success",
                "username": result.username,
                "backend": "private",
                "relogin": result.relogin,
            }))
        else:
            label = "Re-authenticated" if result.relogin else "Logged in"
            console.print(f"[green]{label}[/green] as [bold]{result.username}[/bold] (private API)")
    else:
        error_data = {
            "status": "error",
            "error": result.error,
            "challenge_required": result.challenge_required,
        }
        if ctx.obj["json"]:
            typer.echo(json.dumps(error_data), err=True)
        else:
            console.print(f"[red]Login failed:[/red] {result.error}")
            if result.challenge_required:
                console.print("[yellow]Tip:[/yellow] Run login again — Instagram will send a verification code.")
        raise typer.Exit(code=2)


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
