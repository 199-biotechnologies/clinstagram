from __future__ import annotations

import typer

from clinstagram.backends.capabilities import Feature
from clinstagram.commands._dispatch import _require_growth, dispatch, make_subgroup, strip_at
from clinstagram.models import CLIError, ExitCode

followers_app = make_subgroup("Manage followers")


@followers_app.command("list")
def list_followers(
    ctx: typer.Context,
    limit: int = typer.Option(100, "--limit", "-n", help="Max followers to return"),
):
    """List your followers."""
    dispatch(ctx, Feature.FOLLOWERS_LIST, lambda b: b.followers_list(limit))


@followers_app.command("following")
def following(
    ctx: typer.Context,
    limit: int = typer.Option(100, "--limit", "-n", help="Max accounts to return"),
):
    """List accounts you follow."""
    dispatch(ctx, Feature.FOLLOWERS_FOLLOWING, lambda b: b.followers_following(limit))


@followers_app.command("follow")
def follow(
    ctx: typer.Context,
    user: str = typer.Argument(..., help="Username to follow (with or without @)"),
):
    """Follow a user. Requires --enable-growth-actions."""
    _require_growth(ctx)
    dispatch(ctx, Feature.FOLLOW, lambda b: b.follow(strip_at(user)))


@followers_app.command("unfollow")
def unfollow(
    ctx: typer.Context,
    user: str = typer.Argument(..., help="Username to unfollow (with or without @)"),
):
    """Unfollow a user. Requires --enable-growth-actions."""
    _require_growth(ctx)
    dispatch(ctx, Feature.UNFOLLOW, lambda b: b.unfollow(strip_at(user)))
