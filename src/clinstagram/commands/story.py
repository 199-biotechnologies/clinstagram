from __future__ import annotations

from typing import Optional

import typer

from clinstagram.backends.capabilities import Feature
from clinstagram.commands._dispatch import dispatch, make_subgroup, stage, strip_at

story_app = make_subgroup("Manage stories")


@story_app.command("list")
def list_stories(
    ctx: typer.Context,
    user: str = typer.Argument("", help="Username (omit for own stories)"),
):
    """List stories for a user (or yourself)."""
    clean_user = strip_at(user) if user else ""
    feature = Feature.STORY_VIEW_OTHERS if clean_user else Feature.STORY_LIST
    dispatch(ctx, feature, lambda b: b.story_list(clean_user))


@story_app.command("post-photo")
def post_photo(
    ctx: typer.Context,
    path: str = typer.Argument(..., help="Photo path or URL"),
    mention: Optional[list[str]] = typer.Option(None, "--mention", "-m", help="Mention users"),
    link: str = typer.Option("", "--link", help="Swipe-up link URL"),
):
    """Post a photo story."""
    mentions = [strip_at(m) for m in mention] if mention else None
    dispatch(ctx, Feature.STORY_POST, lambda b: b.story_post_photo(
        stage(path, ctx.obj["_backend_name"]), mentions, link,
    ))


@story_app.command("post-video")
def post_video(
    ctx: typer.Context,
    path: str = typer.Argument(..., help="Video path or URL"),
    mention: Optional[list[str]] = typer.Option(None, "--mention", "-m", help="Mention users"),
    link: str = typer.Option("", "--link", help="Swipe-up link URL"),
):
    """Post a video story."""
    mentions = [strip_at(m) for m in mention] if mention else None
    dispatch(ctx, Feature.STORY_POST, lambda b: b.story_post_video(
        stage(path, ctx.obj["_backend_name"]), mentions, link,
    ))


@story_app.command("viewers")
def viewers(
    ctx: typer.Context,
    story_id: str = typer.Argument(..., help="Story ID"),
):
    """List viewers of a story."""
    dispatch(ctx, Feature.STORY_VIEWERS, lambda b: b.story_viewers(story_id))
