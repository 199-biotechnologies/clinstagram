from __future__ import annotations

import typer
from typing import Optional

from clinstagram.backends.capabilities import Feature
from clinstagram.commands._dispatch import dispatch, make_subgroup

saved_app = make_subgroup("Saved posts & collections (private API)")


@saved_app.command("list")
def list_saved(
    ctx: typer.Context,
    collection: str = typer.Option(
        "",
        "--collection",
        "-c",
        help="Saved collection name (e.g. 'Recipes'). Omit for all saved posts.",
    ),
    videos_only: bool = typer.Option(
        True,
        "--videos-only/--all-media",
        help="Only list videos + albums (default) or every saved item including photos.",
    ),
    limit: int = typer.Option(
        50, "--limit", "-n", help="Max items to return."
    ),
):
    """List media in a saved collection (default: all your saved posts).

    media_type values: 1=photo, 2=video, 8=album/carousel.
    """
    media_types = [2, 8] if videos_only else None
    dispatch(
        ctx,
        Feature.SAVED_LIST,
        lambda b: b.saved_list(
            collection=collection, media_types=media_types, amount=limit
        ),
    )


@saved_app.command("download")
def download_saved(
    ctx: typer.Context,
    output: str = typer.Option(
        "",
        "--output",
        "-o",
        help="Output directory (default: current working directory).",
    ),
    collection: str = typer.Option(
        "",
        "--collection",
        "-c",
        help="Saved collection name. Omit for all saved posts.",
    ),
    videos_only: bool = typer.Option(
        True,
        "--videos-only/--all-media",
        help="Download videos + albums (default) or every saved item including photos.",
    ),
    limit: int = typer.Option(
        50, "--limit", "-n", help="Max items to process."
    ),
):
    """Download videos (and albums) from a saved collection.

    By default this grabs every video + carousel in your saved posts. Use
    --all-media to also pull photos. Returns a manifest of all files written.
    """
    media_types = [2, 8] if videos_only else None
    dispatch(
        ctx,
        Feature.SAVED_DOWNLOAD,
        lambda b: b.saved_download(
            output_dir=output,
            collection=collection,
            media_types=media_types,
            amount=limit,
        ),
    )
