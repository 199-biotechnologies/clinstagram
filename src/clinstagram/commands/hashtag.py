from __future__ import annotations

import typer

from clinstagram.backends.capabilities import Feature
from clinstagram.commands._dispatch import dispatch, make_subgroup

hashtag_app = make_subgroup("Browse hashtag feeds")


@hashtag_app.command("top")
def top(
    ctx: typer.Context,
    tag: str = typer.Argument(..., help="Hashtag to browse (without #)"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max posts to return"),
):
    """Browse top posts for a hashtag."""
    dispatch(ctx, Feature.HASHTAG_TOP, lambda b: b.hashtag_top(tag, limit))


@hashtag_app.command("recent")
def recent(
    ctx: typer.Context,
    tag: str = typer.Argument(..., help="Hashtag to browse (without #)"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max posts to return"),
):
    """Browse recent posts for a hashtag."""
    dispatch(ctx, Feature.HASHTAG_RECENT, lambda b: b.hashtag_recent(tag, limit))
