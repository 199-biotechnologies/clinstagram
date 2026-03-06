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
            payload["user_tags"] = ",".join(tags)

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
            "fields": "id,participants,messages{id,message,from,created_time}",
            "limit": str(limit),
        }
        data = self._get(f"{me}/conversations", params)
        threads = data.get("data", [])
        if unread_only:
            # Graph API doesn't natively filter unread; filter client-side would need
            # additional logic. Return all for now.
            pass
        return [
            {
                "thread_id": t["id"],
                "participants": t.get("participants", {}).get("data", []),
                "messages": t.get("messages", {}).get("data", []),
            }
            for t in threads
        ]

    def dm_thread(self, thread_id: str, limit: int = 20) -> list[dict]:
        self._require_fb("DM thread")
        params = {
            "fields": "id,message,from,created_time",
            "limit": str(limit),
        }
        data = self._get(f"{thread_id}/messages", params)
        return data.get("data", [])

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
        payload = {
            "recipient": _json.dumps({"id": user}),
            "message": _json.dumps({"attachment": {"type": "image", "payload": {"url": media}}}),
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
        me = self._me_id()
        payload: dict[str, Any] = {"image_url": media, "media_type": "STORIES"}
        if link:
            payload["link"] = link

        container = self._post(f"{me}/media", payload)
        container_id = container["id"]
        result = self._post(f"{me}/media_publish", {"creation_id": container_id})
        return {"id": result["id"], "status": "published"}

    def story_post_video(
        self, media: str, mentions: list[str] | None = None, link: str = ""
    ) -> dict:
        self._require_fb("Story video post")
        me = self._me_id()
        payload: dict[str, Any] = {"video_url": media, "media_type": "STORIES"}
        if link:
            payload["link"] = link

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
        return data.get("data", [])

    def comments_reply(self, comment_id: str, text: str) -> dict:
        result = self._post(f"{comment_id}/replies", {"message": text})
        return {"id": result["id"], "status": "replied"}

    def comments_delete(self, comment_id: str) -> dict:
        self._delete(comment_id)
        return {"id": comment_id, "status": "deleted"}

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def analytics_profile(self) -> dict:
        me = self._me_id()
        params = {
            "fields": "followers_count,follows_count,media_count,name,username",
        }
        return self._get(me, params)

    def analytics_post(self, media_id: str) -> dict:
        params = {
            "fields": "id,like_count,comments_count,timestamp,media_type,permalink",
        }
        return self._get(media_id, params)

    def analytics_hashtag(self, tag: str) -> dict:
        # Search for the hashtag ID first, then fetch insights
        search = self._get("ig_hashtag_search", {"q": tag})
        results = search.get("data", [])
        if not results:
            return {"tag": tag, "error": "Hashtag not found"}
        hashtag_id = results[0]["id"]
        me = self._me_id()
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
        return data.get("business_discovery", {})

    def user_search(self, query: str) -> list[dict]:
        # Graph API has no direct user search endpoint.
        # Use business_discovery as a single-user lookup fallback.
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
        return media.get("data", [])

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

    def hashtag_top(self, tag: str, limit: int = 20) -> list[dict]:
        search = self._get("ig_hashtag_search", {"q": tag})
        results = search.get("data", [])
        if not results:
            return []
        hashtag_id = results[0]["id"]
        me = self._me_id()
        params = {
            "fields": "id,caption,media_type,media_url,timestamp,like_count,comments_count",
            "user_id": me,
            "limit": str(limit),
        }
        data = self._get(f"{hashtag_id}/top_media", params)
        return data.get("data", [])

    def hashtag_recent(self, tag: str, limit: int = 20) -> list[dict]:
        search = self._get("ig_hashtag_search", {"q": tag})
        results = search.get("data", [])
        if not results:
            return []
        hashtag_id = results[0]["id"]
        me = self._me_id()
        params = {
            "fields": "id,caption,media_type,media_url,timestamp,like_count,comments_count",
            "user_id": me,
            "limit": str(limit),
        }
        data = self._get(f"{hashtag_id}/recent_media", params)
        return data.get("data", [])
