from __future__ import annotations

import typer

from clinstagram.backends.capabilities import Feature
from clinstagram.commands._dispatch import dispatch, make_subgroup, stage, strip_at

dm_app = make_subgroup("Manage direct messages")


@dm_app.command("inbox")
def inbox(
    ctx: typer.Context,
    unread: bool = typer.Option(False, "--unread", help="Show only unread threads"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max threads to return"),
):
    """List DM inbox threads."""
    dispatch(ctx, Feature.DM_INBOX, lambda b: b.dm_inbox(limit, unread))


@dm_app.command("thread")
def thread(
    ctx: typer.Context,
    thread_id: str = typer.Argument(..., help="Thread ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max messages to return"),
):
    """View messages in a DM thread."""
    dispatch(ctx, Feature.DM_THREAD, lambda b: b.dm_thread(thread_id, limit))


@dm_app.command("send")
def send(
    ctx: typer.Context,
    user: str = typer.Argument(..., help="Username to message (with or without @)"),
    message: str = typer.Argument(..., help="Message text"),
):
    """Send a text DM."""
    clean_user = strip_at(user)
    dispatch(ctx, Feature.DM_COLD_SEND, lambda b: b.dm_send(clean_user, message))


@dm_app.command("send-media")
def send_media(
    ctx: typer.Context,
    user: str = typer.Argument(..., help="Username to message (with or without @)"),
    media: str = typer.Argument(..., help="Media path or URL"),
):
    """Send a media DM (photo/video)."""
    clean_user = strip_at(user)
    dispatch(ctx, Feature.DM_SEND_MEDIA, lambda b: b.dm_send_media(
        clean_user, stage(media, ctx.obj["_backend_name"]),
    ))


@dm_app.command("search")
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
):
    """Search DM threads by keyword."""
    def _search(b):
        threads = b.dm_inbox(100, False)
        q = query.lower()
        return [t for t in threads if q in str(t).lower()]
    dispatch(ctx, Feature.DM_SEARCH, _search)
