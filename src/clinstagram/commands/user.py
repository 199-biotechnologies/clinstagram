from __future__ import annotations

import typer

from clinstagram.backends.capabilities import Feature
from clinstagram.commands._dispatch import dispatch, make_subgroup, strip_at

user_app = make_subgroup("User lookup and search")


@user_app.command("info")
def info(
    ctx: typer.Context,
    username: str = typer.Argument(..., help="Username to look up (with or without @)"),
):
    """Get detailed info for a user."""
    dispatch(ctx, Feature.USER_INFO, lambda b: b.user_info(strip_at(username)))


@user_app.command("search")
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
):
    """Search for users by name or username."""
    dispatch(ctx, Feature.USER_SEARCH, lambda b: b.user_search(query))
