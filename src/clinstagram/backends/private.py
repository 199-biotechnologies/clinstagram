from __future__ import annotations

from pathlib import Path
from typing import Any

from clinstagram.backends.base import Backend


class PrivateAPIError(Exception):
    """Raised when an instagrapi operation fails."""

    pass


def _user_to_dict(user: Any) -> dict:
    """Convert an instagrapi User model to a plain dict."""
    return {
        "pk": str(user.pk),
        "username": user.username,
        "full_name": user.full_name,
        "profile_pic_url": str(user.profile_pic_url) if user.profile_pic_url else None,
        "is_private": user.is_private,
    }


def _media_to_dict(media: Any) -> dict:
    """Convert an instagrapi Media model to a plain dict."""
    return {
        "id": str(media.pk),
        "code": media.code,
        "media_type": media.media_type,
        "caption": media.caption_text if hasattr(media, "caption_text") else "",
        "timestamp": str(media.taken_at) if media.taken_at else None,
        "like_count": getattr(media, "like_count", 0),
        "comment_count": getattr(media, "comment_count", 0),
    }


def _comment_to_dict(comment: Any) -> dict:
    """Convert an instagrapi Comment model to a plain dict."""
    return {
        "id": str(comment.pk),
        "text": comment.text,
        "user": _user_to_dict(comment.user) if comment.user else None,
        "timestamp": str(comment.created_at_utc) if comment.created_at_utc else None,
    }


def _story_to_dict(story: Any) -> dict:
    """Convert an instagrapi Story model to a plain dict."""
    return {
        "id": str(story.pk),
        "media_type": story.media_type,
        "video_url": str(story.video_url) if story.video_url else None,
        "thumbnail_url": str(story.thumbnail_url) if story.thumbnail_url else None,
        "timestamp": str(story.taken_at) if story.taken_at else None,
    }


def _thread_to_dict(thread: Any) -> dict:
    """Convert an instagrapi DirectThread model to a plain dict."""
    return {
        "thread_id": str(thread.id),
        "thread_title": thread.thread_title,
        "users": [_user_to_dict(u) for u in (thread.users or [])],
        "last_activity_at": str(thread.last_activity_at) if thread.last_activity_at else None,
    }


def _message_to_dict(msg: Any) -> dict:
    """Convert an instagrapi DirectMessage model to a plain dict."""
    return {
        "id": str(msg.id),
        "text": msg.text or "",
        "user_id": str(msg.user_id) if msg.user_id else None,
        "timestamp": str(msg.timestamp) if msg.timestamp else None,
        "item_type": getattr(msg, "item_type", None),
    }


def _wrap_error(fn_name: str, exc: Exception) -> PrivateAPIError:
    """Wrap an instagrapi exception with context."""
    return PrivateAPIError(f"{fn_name} failed: {exc}")


class PrivateBackend(Backend):
    """Instagram Private API backend via instagrapi."""

    def __init__(self, client: Any):
        """
        Parameters
        ----------
        client : instagrapi.Client
            An already-authenticated instagrapi Client instance.
        """
        self._cl = client

    @property
    def name(self) -> str:
        return "private"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _user_id_from_username(self, username: str) -> str:
        try:
            info = self._cl.user_info_by_username(username)
            return str(info.pk)
        except Exception as exc:
            raise _wrap_error("user_id_from_username", exc)

    # ------------------------------------------------------------------
    # Posting
    # ------------------------------------------------------------------

    def post_photo(
        self, media: str, caption: str = "", location: str = "", tags: list[str] | None = None
    ) -> dict:
        try:
            kwargs: dict[str, Any] = {"path": Path(media), "caption": caption}
            result = self._cl.photo_upload(**kwargs)
            return _media_to_dict(result)
        except Exception as exc:
            raise _wrap_error("post_photo", exc)

    def post_video(
        self, media: str, caption: str = "", thumbnail: str = "", location: str = ""
    ) -> dict:
        try:
            kwargs: dict[str, Any] = {"path": Path(media), "caption": caption}
            if thumbnail:
                kwargs["thumbnail"] = Path(thumbnail)
            result = self._cl.video_upload(**kwargs)
            return _media_to_dict(result)
        except Exception as exc:
            raise _wrap_error("post_video", exc)

    def post_reel(
        self, media: str, caption: str = "", thumbnail: str = "", audio: str = ""
    ) -> dict:
        try:
            kwargs: dict[str, Any] = {"path": Path(media), "caption": caption}
            if thumbnail:
                kwargs["thumbnail"] = Path(thumbnail)
            result = self._cl.clip_upload(**kwargs)
            return _media_to_dict(result)
        except Exception as exc:
            raise _wrap_error("post_reel", exc)

    def post_carousel(self, media_list: list[str], caption: str = "") -> dict:
        try:
            paths = [Path(m) for m in media_list]
            result = self._cl.album_upload(paths, caption=caption)
            return _media_to_dict(result)
        except Exception as exc:
            raise _wrap_error("post_carousel", exc)

    # ------------------------------------------------------------------
    # DMs
    # ------------------------------------------------------------------

    def dm_inbox(self, limit: int = 20, unread_only: bool = False) -> list[dict]:
        try:
            threads = self._cl.direct_threads(amount=limit)
            results = [_thread_to_dict(t) for t in threads]
            return results
        except Exception as exc:
            raise _wrap_error("dm_inbox", exc)

    def dm_thread(self, thread_id: str, limit: int = 20) -> list[dict]:
        try:
            messages = self._cl.direct_messages(thread_id, amount=limit)
            return [_message_to_dict(m) for m in messages]
        except Exception as exc:
            raise _wrap_error("dm_thread", exc)

    def dm_send(self, user: str, message: str) -> dict:
        try:
            user_ids = [int(self._user_id_from_username(user))]
            result = self._cl.direct_send(message, user_ids=user_ids)
            return {"message_id": str(result.id) if result else None, "status": "sent"}
        except PrivateAPIError:
            raise
        except Exception as exc:
            raise _wrap_error("dm_send", exc)

    def dm_send_media(self, user: str, media: str) -> dict:
        try:
            user_ids = [int(self._user_id_from_username(user))]
            path = Path(media)
            suffix = path.suffix.lower()
            if suffix in (".mp4", ".mov", ".avi"):
                result = self._cl.direct_send_video(path, user_ids=user_ids)
            else:
                result = self._cl.direct_send_photo(path, user_ids=user_ids)
            return {"message_id": str(result.id) if result else None, "status": "sent"}
        except PrivateAPIError:
            raise
        except Exception as exc:
            raise _wrap_error("dm_send_media", exc)

    # ------------------------------------------------------------------
    # Stories
    # ------------------------------------------------------------------

    def story_list(self, user: str = "") -> list[dict]:
        try:
            if user:
                user_id = int(self._user_id_from_username(user))
                stories = self._cl.user_stories(user_id)
            else:
                user_id = self._cl.user_id
                stories = self._cl.user_stories(user_id)
            return [_story_to_dict(s) for s in stories]
        except PrivateAPIError:
            raise
        except Exception as exc:
            raise _wrap_error("story_list", exc)

    def story_post_photo(
        self, media: str, mentions: list[str] | None = None, link: str = ""
    ) -> dict:
        try:
            kwargs: dict[str, Any] = {"path": Path(media)}
            if mentions:
                from instagrapi.types import StoryMention

                mention_objects = []
                for m in mentions:
                    uid = int(self._user_id_from_username(m))
                    mention_objects.append(
                        StoryMention(user=self._cl.user_info(uid), x=0.5, y=0.5, width=0.3, height=0.05)
                    )
                kwargs["mentions"] = mention_objects
            if link:
                from instagrapi.types import StoryLink

                kwargs["links"] = [StoryLink(webUri=link)]
            result = self._cl.photo_upload_to_story(**kwargs)
            return _story_to_dict(result)
        except PrivateAPIError:
            raise
        except Exception as exc:
            raise _wrap_error("story_post_photo", exc)

    def story_post_video(
        self, media: str, mentions: list[str] | None = None, link: str = ""
    ) -> dict:
        try:
            kwargs: dict[str, Any] = {"path": Path(media)}
            if mentions:
                from instagrapi.types import StoryMention

                mention_objects = []
                for m in mentions:
                    uid = int(self._user_id_from_username(m))
                    mention_objects.append(
                        StoryMention(user=self._cl.user_info(uid), x=0.5, y=0.5, width=0.3, height=0.05)
                    )
                kwargs["mentions"] = mention_objects
            if link:
                from instagrapi.types import StoryLink

                kwargs["links"] = [StoryLink(webUri=link)]
            result = self._cl.video_upload_to_story(**kwargs)
            return _story_to_dict(result)
        except PrivateAPIError:
            raise
        except Exception as exc:
            raise _wrap_error("story_post_video", exc)

    def story_viewers(self, story_id: str) -> list[dict]:
        try:
            viewers = self._cl.story_viewers(story_id)
            return [_user_to_dict(v) for v in viewers]
        except Exception as exc:
            raise _wrap_error("story_viewers", exc)

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def comments_list(self, media_id: str, limit: int = 50) -> list[dict]:
        try:
            comments = self._cl.media_comments(media_id, amount=limit)
            return [_comment_to_dict(c) for c in comments]
        except Exception as exc:
            raise _wrap_error("comments_list", exc)

    def comments_reply(self, comment_id: str, text: str) -> dict:
        try:
            # instagrapi expects media_id for comment creation;
            # comment_id format is "media_id:comment_id" when passed from CLI
            parts = comment_id.split(":", 1)
            if len(parts) == 2:
                media_id, cid = parts
            else:
                media_id = comment_id
            result = self._cl.media_comment(media_id, text)
            return _comment_to_dict(result)
        except Exception as exc:
            raise _wrap_error("comments_reply", exc)

    def comments_delete(self, comment_id: str) -> dict:
        try:
            parts = comment_id.split(":", 1)
            if len(parts) == 2:
                media_id, cid = parts
                self._cl.comment_bulk_delete(media_id, [int(cid)])
            else:
                # Best-effort: treat as comment PK
                self._cl.comment_bulk_delete(comment_id, [int(comment_id)])
            return {"id": comment_id, "status": "deleted"}
        except Exception as exc:
            raise _wrap_error("comments_delete", exc)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def analytics_profile(self) -> dict:
        try:
            info = self._cl.account_info()
            return {
                "username": info.username,
                "full_name": info.full_name,
                "followers_count": info.follower_count,
                "following_count": info.following_count,
                "media_count": info.media_count,
                "biography": info.biography,
            }
        except Exception as exc:
            raise _wrap_error("analytics_profile", exc)

    def analytics_post(self, media_id: str) -> dict:
        try:
            info = self._cl.media_info(media_id)
            return _media_to_dict(info)
        except Exception as exc:
            raise _wrap_error("analytics_post", exc)

    def analytics_hashtag(self, tag: str) -> dict:
        try:
            info = self._cl.hashtag_info(tag)
            return {
                "name": info.name,
                "media_count": info.media_count,
            }
        except Exception as exc:
            raise _wrap_error("analytics_hashtag", exc)

    # ------------------------------------------------------------------
    # Followers
    # ------------------------------------------------------------------

    def followers_list(self, limit: int = 100) -> list[dict]:
        try:
            user_id = self._cl.user_id
            followers = self._cl.user_followers(user_id, amount=limit)
            return [_user_to_dict(u) for u in followers.values()]
        except Exception as exc:
            raise _wrap_error("followers_list", exc)

    def followers_following(self, limit: int = 100) -> list[dict]:
        try:
            user_id = self._cl.user_id
            following = self._cl.user_following(user_id, amount=limit)
            return [_user_to_dict(u) for u in following.values()]
        except Exception as exc:
            raise _wrap_error("followers_following", exc)

    def follow(self, user: str) -> dict:
        try:
            user_id = int(self._user_id_from_username(user))
            result = self._cl.user_follow(user_id)
            return {"username": user, "followed": result}
        except PrivateAPIError:
            raise
        except Exception as exc:
            raise _wrap_error("follow", exc)

    def unfollow(self, user: str) -> dict:
        try:
            user_id = int(self._user_id_from_username(user))
            result = self._cl.user_unfollow(user_id)
            return {"username": user, "unfollowed": result}
        except PrivateAPIError:
            raise
        except Exception as exc:
            raise _wrap_error("unfollow", exc)

    # ------------------------------------------------------------------
    # User
    # ------------------------------------------------------------------

    def user_info(self, username: str) -> dict:
        try:
            info = self._cl.user_info_by_username(username)
            return {
                **_user_to_dict(info),
                "biography": info.biography,
                "followers_count": info.follower_count,
                "following_count": info.following_count,
                "media_count": info.media_count,
                "is_verified": info.is_verified,
            }
        except Exception as exc:
            raise _wrap_error("user_info", exc)

    def user_search(self, query: str) -> list[dict]:
        try:
            users = self._cl.search_users(query)
            return [_user_to_dict(u) for u in users]
        except Exception as exc:
            raise _wrap_error("user_search", exc)
