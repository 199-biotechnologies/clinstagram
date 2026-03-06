import typer
from typing import Optional
from enum import Enum
from rich.console import Console

console = Console()
app = typer.Typer(help="Hybrid Instagram CLI for OpenClaw (Graph + Private API)")

class Backend(str, Enum):
    AUTO = "auto"
    GRAPH = "graph"
    PRIVATE = "private"

@app.callback()
def main(
    ctx: typer.Context,
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
    account: str = typer.Option("default", "--account", help="Account name"),
    backend: Backend = typer.Option(Backend.AUTO, "--backend", help="Force specific backend"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen"),
    verbose: bool = typer.Option(False, "--verbose", help="Debug logging")
):
    """
    Clinstagram: Hybrid Instagram CLI for OpenClaw.
    Automatically routes between official Meta Graph API and Private API (instagrapi).
    """
    ctx.obj = {
        "json": json,
        "account": account,
        "backend": backend,
        "dry_run": dry_run,
        "verbose": verbose
    }

# Command Groups (Phase 1 placeholders)
auth_app = typer.Typer(help="Manage authentication (Graph & Private)")
app.add_typer(auth_app, name="auth")

post_app = typer.Typer(help="Post photos, videos, and reels")
app.add_typer(post_app, name="post")

dm_app = typer.Typer(help="Manage direct messages")
app.add_typer(dm_app, name="dm")

@auth_app.command("status")
def auth_status(ctx: typer.Context):
    """Show authentication status for the current account."""
    typer.echo(f"Checking status for account: {ctx.obj['account']}...")

if __name__ == "__main__":
    app()
