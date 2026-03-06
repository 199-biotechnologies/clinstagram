from __future__ import annotations

from typing import Optional

import typer

from clinstagram.backends.capabilities import Feature
from clinstagram.commands._dispatch import dispatch, make_subgroup, stage

post_app = make_subgroup("Post photos, videos, reels, carousels")


@post_app.command("photo")
def photo(
    ctx: typer.Context,
    path: str = typer.Argument(..., help="Image path or URL"),
    caption: str = typer.Option("", "--caption", "-c", help="Post caption"),
    location: str = typer.Option("", "--location", "-l", help="Location ID"),
    tags: Optional[list[str]] = typer.Option(None, "--tags", "-t", help="User tags"),
):
    """Post a photo."""
    dispatch(ctx, Feature.POST_PHOTO, lambda b: b.post_photo(
        stage(path, ctx.obj["_backend_name"]), caption, location, tags,
    ))


@post_app.command("video")
def video(
    ctx: typer.Context,
    path: str = typer.Argument(..., help="Video path or URL"),
    caption: str = typer.Option("", "--caption", "-c", help="Post caption"),
    thumbnail: str = typer.Option("", "--thumbnail", help="Thumbnail path or URL"),
    location: str = typer.Option("", "--location", "-l", help="Location ID"),
):
    """Post a video."""
    dispatch(ctx, Feature.POST_VIDEO, lambda b: b.post_video(
        stage(path, ctx.obj["_backend_name"]), caption, thumbnail, location,
    ))


@post_app.command("reel")
def reel(
    ctx: typer.Context,
    path: str = typer.Argument(..., help="Video path or URL"),
    caption: str = typer.Option("", "--caption", "-c", help="Post caption"),
    thumbnail: str = typer.Option("", "--thumbnail", help="Thumbnail path or URL"),
    audio: str = typer.Option("", "--audio", help="Audio name"),
):
    """Post a reel."""
    dispatch(ctx, Feature.POST_REEL, lambda b: b.post_reel(
        stage(path, ctx.obj["_backend_name"]), caption, thumbnail, audio,
    ))


@post_app.command("carousel")
def carousel(
    ctx: typer.Context,
    paths: list[str] = typer.Argument(..., help="Image/video paths or URLs"),
    caption: str = typer.Option("", "--caption", "-c", help="Post caption"),
):
    """Post a carousel (multiple images/videos)."""
    dispatch(ctx, Feature.POST_CAROUSEL, lambda b: b.post_carousel(
        [stage(p, ctx.obj["_backend_name"]) for p in paths], caption,
    ))
