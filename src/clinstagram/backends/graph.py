from __future__ import annotations

import json as _json
from typing import Any

import httpx

from clinstagram.backends.base import Backend


class GraphAPIError(Exception):
    """Raised when the Instagram/Facebook Graph API returns an error."""

    def __init__(self, status_code: int, error_type: str, message: str, code: int | None = None):
        self.status_code = status_code
        self.error_type = error_type
        self.code = code
        super().__init__(message)


def _extract_error(response: httpx.Response) -> GraphAPIError:
    """Parse a Graph API error response into a structured exception."""
    try:
        body = response.json()
        err = body.get("error", {})
        return GraphAPIError(
            status_code=response.status_code,
            error_type=err.get("type", "Unknown"),
            message=err.get("message", response.text),
            code=err.get("code"),
        )
    except Exception:
        return GraphAPIError(
            status_code=response.status_code,
            error_type="Unknown",
            message=response.text,
        )


def _check(response: httpx.Response) -> dict | list:
    """Raise on non-2xx, otherwise return parsed JSON."""
    if response.status_code >= 400:
        raise _extract_error(response)
    return response.json()


class GraphBackend(Backend):
    """Instagram Graph API / Facebook Graph API backend."""

    BASE_URLS = {
        "ig": "https://graph.instagram.com/v21.0",
        "fb": "https://graph.facebook.com/v21.0",
    }

    def __init__(self, token: str, login_type: str, client: httpx.Client):
        if login_type not in self.BASE_URLS:
            raise ValueError(f"login_type must be 'ig' or 'fb', got '{login_type}'")
        self._token = token
        self._login_type = login_type
        self._client = client
        self._base = self.BASE_URLS[login_type]
        self._me_id_cache: str | None = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return f"graph_{self._login_type}"

    def _url(self, path: str) -> str:
        return f"{self._base}/{path.lstrip('/')}"

    def _params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        p: dict[str, Any] = {"access_token": self._token}
        if extra:
            p.update(extra)
        return p

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return _check(self._client.get(self._url(path), params=self._params(params)))

    def _post(self, path: str, data: dict[str, Any] | None = None) -> Any:
        return _check(self._client.post(self._url(path), data=self._params(data)))

    def _delete(self, path: str) -> Any:
        return _check(self._client.delete(self._url(path), params=self._params()))

    def _normalize_user(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(data["id"]) if data.get("id") is not None else None,
            "username": data.get("username"),
            "full_name": data.get("full_name") or data.get("name"),
            "profile_picture_url": data.get("profile_picture_url") or data.get("profile_pic_url"),
            "is_private": data.get("is_private"),
            "is_verified": data.get("is_verified"),
            "biography": data.get("biography"),
            "followers_count": data.get("followers_count"),
            "following_count": data.get("following_count", data.get("follows_count")),
            "media_count": data.get("media_count"),
        }

    def _normalize_media(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(data["id"]),
            "code": data.get("shortcode") or data.get("code"),
            "media_type": data.get("media_type"),
            "caption": data.get("caption", ""),
            "timestamp": data.get("timestamp"),
            "like_count": data.get("like_count", 0),
            "comment_count": data.get("comment_count", data.get("comments_count", 0)),
            "media_url": data.get("media_url"),
            "permalink": data.get("permalink"),
        }

    def _normalize_comment(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(data["id"]),
            "comment_id": str(data["id"]),
            "comment_ref": str(data["id"]),
            "text": data.get("text", ""),
            "user": self._normalize_user(data["from"]) if isinstance(data.get("from"), dict) else None,
            "timestamp": data.get("timestamp"),
        }

    def _normalize_thread(self, data: dict[str, Any]) -> dict[str, Any]:
        participants = [
            self._normalize_user(participant)
            for participant in data.get("participants", {}).get("data", [])
        ]
        messages = data.get("messages", {}).get("data", [])
        last_message = messages[0] if messages else {}
        thread_title = ", ".join(
            participant["username"] or participant["full_name"] or participant["id"] or ""
            for participant in participants
            if participant["username"] or participant["full_name"] or participant["id"]
        )
        return {
            "thread_id": str(data["id"]),
            "thread_title": thread_title or None,
            "participants": participants,
            "last_message": last_message.get("message"),
            "last_message_at": last_message.get("created_time") or data.get("updated_time"),
            "unread": bool(data["unread_count"]) if data.get("unread_count") is not None else None,
        }

    def _normalize_message(self, data: dict[str, Any]) -> dict[str, Any]:
        sender = data.get("from") or {}
        return {
            "message_id": str(data["id"]),
            "text": data.get("message", ""),
            "sender_id": str(sender["id"]) if sender.get("id") is not None else None,
            "sender_username": sender.get("username"),
            "timestamp": data.get("created_time"),
            "item_type": "text",
        }

    def _require_fb(self, feature: str) -> None:
        if self._login_type != "fb":
            raise NotImplementedError(
                f"{feature} requires Facebook login (login_type='fb'). "
                "Re-authenticate with a Facebook-linked Instagram account."
            )

    def _me_id(self) -> str:
        if self._me_id_cache is None:
            data = self._get("me", {"fields": "id"})
            self._me_id_cache = data["id"]
        return self._me_id_cache

    # ------------------------------------------------------------------
    # Posting
    # ------------------------------------------------------------------

    def post_photo(
        self, media: str, caption: str = "", location: str = "", tags: list[str] | None = None
    ) -> dict:
        me = self._me_id()
        payload: dict[str, Any] = {"image_url": media}
        if caption:
            payload["caption"] = caption
        if location:
            payload["location_id"] = location
        if tags:
            payload["user_tags"] = _json.dumps(
                [{"username": tag, "x": 0.5, "y": 0.5} for tag in tags]
            )

        # Step 1: create media container
        container = self._post(f"{me}/media", payload)
        container_id = container["id"]

        # Step 2: publish
        result = self._post(f"{me}/media_publish", {"creation_id": container_id})
        return {"id": result["id"], "status": "published"}

    def post_video(
        self, media: str, caption: str = "", thumbnail: str = "", location: str = ""
    ) -> dict:
        me = self._me_id()
        payload: dict[str, Any] = {"video_url": media, "media_type": "VIDEO"}
        if caption:
            payload["caption"] = caption
        if thumbnail:
            if not thumbnail.isdigit():
                raise ValueError(
                    "Graph API expects --thumbnail to be a millisecond thumb offset. "
                    "Use a numeric value or route through --backend private."
                )
            payload["thumb_offset"] = thumbnail
        if location:
            payload["location_id"] = location

        container = self._post(f"{me}/media", payload)
        container_id = container["id"]
        result = self._post(f"{me}/media_publish", {"creation_id": container_id})
        return {"id": result["id"], "status": "published"}

    def post_reel(
        self, media: str, caption: str = "", thumbnail: str = "", audio: str = ""
    ) -> dict:
        me = self._me_id()
        payload: dict[str, Any] = {"video_url": media, "media_type": "REELS"}
        if caption:
            payload["caption"] = caption
        if thumbnail:
            if not thumbnail.isdigit():
                raise ValueError(
                    "Graph API expects --thumbnail to be a millisecond thumb offset. "
                    "Use a numeric value or route through --backend private."
                )
            payload["thumb_offset"] = thumbnail
        if audio:
            payload["audio_name"] = audio

        container = self._post(f"{me}/media", payload)
        container_id = container["id"]
        result = self._post(f"{me}/media_publish", {"creation_id": container_id})
        return {"id": result["id"], "status": "published"}

    def post_carousel(self, media_list: list[str], caption: str = "") -> dict:
        me = self._me_id()
        # Create a container for each item
        children_ids = []
        for url in media_list:
            is_video = any(url.lower().endswith(ext) for ext in (".mp4", ".mov", ".avi"))
            payload: dict[str, Any] = {
                "is_carousel_item": "true",
                "video_url" if is_video else "image_url": url,
            }
            if is_video:
                payload["media_type"] = "VIDEO"
            child = self._post(f"{me}/media", payload)
            children_ids.append(child["id"])

        # Create the carousel container
        carousel_payload: dict[str, Any] = {
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
        }
        if caption:
            carousel_payload["caption"] = caption
        container = self._post(f"{me}/media", carousel_payload)
        result = self._post(f"{me}/media_publish", {"creation_id": container["id"]})
        return {"id": result["id"], "status": "published"}

    # ------------------------------------------------------------------
    # DMs (Facebook login only)
    # ------------------------------------------------------------------

    def dm_inbox(self, limit: int = 20, unread_only: bool = False) -> list[dict]:
        self._require_fb("DM inbox")
        me = self._me_id()
        params: dict[str, Any] = {
            "fields": (
                "id,updated_time,unread_count,"
                "participants{id,username,name},"
                "messages.limit(1){id,message,from{id,username,name},created_time}"
            ),
            "limit": str(limit),
        }
        data = self._get(f"{me}/conversations", params)
        threads = data.get("data", [])
        if unread_only:
            threads = [t for t in threads if t.get("unread_count", 0) > 0]
        return [self._normalize_thread(thread) for thread in threads]

    def dm_thread(self, thread_id: str, limit: int = 20) -> list[dict]:
        self._require_fb("DM thread")
        params = {
            "fields": "id,message,from{id,username,name},created_time",
            "limit": str(limit),
        }
        data = self._get(f"{thread_id}/messages", params)
        return [self._normalize_message(message) for message in data.get("data", [])]

    def dm_send(self, user: str, message: str) -> dict:
        self._require_fb("DM send")
        me = self._me_id()
        payload = {
            "recipient": _json.dumps({"id": user}),
            "message": _json.dumps({"text": message}),
        }
        result = self._post(f"{me}/messages", payload)
        return {"message_id": result.get("message_id", result.get("id")), "status": "sent"}

    def dm_send_media(self, user: str, media: str) -> dict:
        self._require_fb("DM send media")
        me = self._me_id()
        media_type = "video" if media.lower().split("?", 1)[0].endswith((".mp4", ".mov", ".avi")) else "image"
        payload = {
            "recipient": _json.dumps({"id": user}),
            "message": _json.dumps({"attachment": {"type": media_type, "payload": {"url": media}}}),
        }
        result = self._post(f"{me}/messages", payload)
        return {"message_id": result.get("message_id", result.get("id")), "status": "sent"}

    # ------------------------------------------------------------------
    # Stories
    # ------------------------------------------------------------------

    def story_list(self, user: str = "") -> list[dict]:
        target = user or self._me_id()
        params = {"fields": "id,media_type,media_url,timestamp"}
        data = self._get(f"{target}/stories", params)
        return data.get("data", [])

    def story_post_photo(
        self, media: str, mentions: list[str] | None = None, link: str = ""
    ) -> dict:
        self._require_fb("Story photo post")
        if link:
            raise ValueError(
                "Graph story publishing does not support link stickers through this CLI. "
                "Use --backend private for story links."
            )
        me = self._me_id()
        payload: dict[str, Any] = {"image_url": media, "media_type": "STORIES"}
        if mentions:
            payload["user_tags"] = _json.dumps(
                [{"username": mention, "x": 0.5, "y": 0.5} for mention in mentions]
            )

        container = self._post(f"{me}/media", payload)
        container_id = container["id"]
        result = self._post(f"{me}/media_publish", {"creation_id": container_id})
        return {"id": result["id"], "status": "published"}

    def story_post_video(
        self, media: str, mentions: list[str] | None = None, link: str = ""
    ) -> dict:
        self._require_fb("Story video post")
        if link:
            raise ValueError(
                "Graph story publishing does not support link stickers through this CLI. "
                "Use --backend private for story links."
            )
        me = self._me_id()
        payload: dict[str, Any] = {"video_url": media, "media_type": "STORIES"}
        if mentions:
            payload["user_tags"] = _json.dumps(
                [{"username": mention, "x": 0.5, "y": 0.5} for mention in mentions]
            )

        container = self._post(f"{me}/media", payload)
        container_id = container["id"]
        result = self._post(f"{me}/media_publish", {"creation_id": container_id})
        return {"id": result["id"], "status": "published"}

    def story_viewers(self, story_id: str) -> list[dict]:
        params = {"fields": "id,username"}
        data = self._get(f"{story_id}/insights", params)
        return data.get("data", [])

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    def comments_list(self, media_id: str, limit: int = 50) -> list[dict]:
        params = {
            "fields": "id,text,from,timestamp",
            "limit": str(limit),
        }
        data = self._get(f"{media_id}/comments", params)
        return [self._normalize_comment(comment) for comment in data.get("data", [])]

    def comments_reply(self, comment_id: str, text: str) -> dict:
        result = self._post(f"{comment_id}/replies", {"message": text})
        return {"comment_ref": str(result["id"]), "status": "replied"}

    def comments_delete(self, comment_id: str) -> dict:
        self._delete(comment_id)
        return {"comment_ref": comment_id, "status": "deleted"}

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def analytics_profile(self) -> dict:
        me = self._me_id()
        params = {
            "fields": "id,followers_count,follows_count,media_count,name,username,biography,profile_picture_url",
        }
        return self._normalize_user(self._get(me, params))

    def analytics_post(self, media_id: str) -> dict:
        if media_id == "latest":
            me = self._me_id()
            latest = self._get(f"{me}/media", {"fields": "id", "limit": "1"})
            items = latest.get("data", [])
            if not items:
                raise ValueError("No posts found for the current account")
            media_id = str(items[0]["id"])
        params = {
            "fields": "id,caption,like_count,comments_count,timestamp,media_type,media_url,permalink,shortcode",
        }
        return self._normalize_media(self._get(media_id, params))

    def analytics_hashtag(self, tag: str) -> dict:
        me = self._me_id()
        # ig_hashtag_search requires user_id on the search request itself
        search = self._get("ig_hashtag_search", {"q": tag, "user_id": me})
        results = search.get("data", [])
        if not results:
            return {"tag": tag, "error": "Hashtag not found"}
        hashtag_id = results[0]["id"]
        params = {"fields": "id,name,media_count", "user_id": me}
        return self._get(hashtag_id, params)

    # ------------------------------------------------------------------
    # Followers
    # ------------------------------------------------------------------

    def followers_list(self, limit: int = 100) -> list[dict]:
        # Graph API does not expose a full followers list.
        # Only business discovery can show follower counts.
        raise NotImplementedError(
            "The Graph API does not provide a full followers list. "
            "Use --backend private for this feature."
        )

    def followers_following(self, limit: int = 100) -> list[dict]:
        raise NotImplementedError(
            "The Graph API does not provide a following list. "
            "Use --backend private for this feature."
        )

    def follow(self, user: str) -> dict:
        raise NotImplementedError(
            "The Graph API does not support follow actions. "
            "Use --backend private for this feature."
        )

    def unfollow(self, user: str) -> dict:
        raise NotImplementedError(
            "The Graph API does not support unfollow actions. "
            "Use --backend private for this feature."
        )

    # ------------------------------------------------------------------
    # User
    # ------------------------------------------------------------------

    def user_info(self, username: str) -> dict:
        me = self._me_id()
        params = {
            "fields": f"business_discovery.fields(id,username,name,biography,followers_count,follows_count,media_count,profile_picture_url).username({username})",
        }
        data = self._get(me, params)
        business = data.get("business_discovery", {})
        return self._normalize_user(business) if business else {}

    def user_search(self, query: str) -> list[dict]:
        # Graph API has no direct user search endpoint.
        # Use business_discovery as a single-user lookup fallback.
        if any(ch.isspace() for ch in query.strip()):
            return []
        try:
            info = self.user_info(query)
            return [info] if info else []
        except GraphAPIError:
            return []

    def user_posts(self, username: str, limit: int = 20) -> list[dict]:
        me = self._me_id()
        params = {
            "fields": f"business_discovery.fields(media.limit({limit}){{id,caption,media_type,media_url,timestamp,like_count,comments_count}}).username({username})",
        }
        data = self._get(me, params)
        business = data.get("business_discovery", {})
        media = business.get("media", {})
        return [self._normalize_media(item) for item in media.get("data", [])]

    # ------------------------------------------------------------------
    # Engagement
    # ------------------------------------------------------------------

    def like_post(self, media_id: str) -> dict:
        raise NotImplementedError(
            "The Graph API does not support liking posts. "
            "Use --backend private for this feature."
        )

    def unlike_post(self, media_id: str) -> dict:
        raise NotImplementedError(
            "The Graph API does not support unliking posts. "
            "Use --backend private for this feature."
        )

    def comments_add(self, media_id: str, text: str) -> dict:
        result = self._post(f"{media_id}/comments", {"message": text})
        return {"id": result["id"], "status": "commented"}

    # ------------------------------------------------------------------
    # Hashtag browsing
    # ------------------------------------------------------------------

    def _hashtag_id(self, tag: str) -> str | None:
        """Look up a hashtag ID (requires user_id per Meta docs)."""
        me = self._me_id()
        search = self._get("ig_hashtag_search", {"q": tag, "user_id": me})
        results = search.get("data", [])
        return results[0]["id"] if results else None

    def hashtag_top(self, tag: str, limit: int = 20) -> list[dict]:
        hashtag_id = self._hashtag_id(tag)
        if not hashtag_id:
            return []
        me = self._me_id()
        params = {
            "fields": "id,caption,media_type,media_url,timestamp,like_count,comments_count",
            "user_id": me,
            "limit": str(limit),
        }
        data = self._get(f"{hashtag_id}/top_media", params)
        return [self._normalize_media(item) for item in data.get("data", [])]

    def hashtag_recent(self, tag: str, limit: int = 20) -> list[dict]:
        hashtag_id = self._hashtag_id(tag)
        if not hashtag_id:
            return []
        me = self._me_id()
        params = {
            "fields": "id,caption,media_type,media_url,timestamp,like_count,comments_count",
            "user_id": me,
            "limit": str(limit),
        }
        data = self._get(f"{hashtag_id}/recent_media", params)
        return [self._normalize_media(item) for item in data.get("data", [])]
