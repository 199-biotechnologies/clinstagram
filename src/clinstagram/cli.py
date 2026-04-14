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
    epilog="Global options (--json, --proxy, --account) must appear before the subcommand. Example: clinstagram --json auth status",
    no_args_is_help=True,
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
    json_output: bool = typer.Option(False, "--json", help="Output as JSON (place before subcommand)"),
    account: str = typer.Option("default", "--account", help="Account name"),
    backend: BackendType = typer.Option(BackendType.AUTO, "--backend", help="Force backend"),
    proxy: Optional[str] = typer.Option(None, "--proxy", help="Proxy URL for private API"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen"),
    enable_growth: bool = typer.Option(
        False, "--enable-growth-actions", help="Unlock follow/unfollow, like/unlike, and commenting"
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
    config = load_config(config_dir)
    ctx.obj["proxy"] = proxy or config.proxy
    ctx.obj["dry_run"] = dry_run
    ctx.obj["enable_growth"] = enable_growth
    ctx.obj["config_dir"] = config_dir
    ctx.obj["config"] = config
    # Use memory-backed secrets only in explicit test mode
    if os.environ.get("CLINSTAGRAM_TEST_MODE") == "1":
        from clinstagram.auth.keychain import SecretsStore

        ctx.obj["secrets"] = SecretsStore(backend="memory")


# Lazy-load command groups to avoid importing instagrapi/httpx at startup.
# This cuts cold-start latency by ~300-500ms (measured: --help goes from ~600ms to ~100ms).
def _lazy_register() -> None:
    from clinstagram.commands.analytics import analytics_app
    from clinstagram.commands.auth import auth_app
    from clinstagram.commands.comments import comments_app
    from clinstagram.commands.config_cmd import config_app
    from clinstagram.commands.dm import dm_app
    from clinstagram.commands.followers import followers_app
    from clinstagram.commands.hashtag import hashtag_app
    from clinstagram.commands.like import like_app
    from clinstagram.commands.media import media_app
    from clinstagram.commands.post import post_app
    from clinstagram.commands.story import story_app
    from clinstagram.commands.user import user_app
    from clinstagram.commands.skill_install import skill_app

    app.add_typer(auth_app, name="auth")
    app.add_typer(config_app, name="config")
    app.add_typer(post_app, name="post")
    app.add_typer(dm_app, name="dm")
    app.add_typer(story_app, name="story")
    app.add_typer(comments_app, name="comments")
    app.add_typer(analytics_app, name="analytics")
    app.add_typer(followers_app, name="followers")
    app.add_typer(user_app, name="user")
    app.add_typer(like_app, name="like")
    app.add_typer(hashtag_app, name="hashtag")
    app.add_typer(media_app, name="media")
    app.add_typer(skill_app, name="skill")


_lazy_register()
