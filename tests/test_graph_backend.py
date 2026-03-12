from __future__ import annotations

import json
from urllib.parse import parse_qs

import httpx

from clinstagram.backends.graph import GraphBackend


def test_analytics_profile_is_normalized():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        if request.url.path == "/v21.0/me":
            return httpx.Response(200, json={"id": "42"})
        assert request.url.path == "/v21.0/42"
        return httpx.Response(
            200,
            json={
                "id": "42",
                "username": "testaccount",
                "name": "Test Account",
                "followers_count": 120,
                "follows_count": 45,
                "media_count": 9,
                "profile_picture_url": "https://example.com/pic.jpg",
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = GraphBackend(token="tok", login_type="ig", client=client)

    result = backend.analytics_profile()

    assert result["id"] == "42"
    assert result["full_name"] == "Test Account"
    assert result["followers_count"] == 120
    assert result["following_count"] == 45
    assert result["profile_picture_url"] == "https://example.com/pic.jpg"


def test_analytics_post_latest_resolves_latest_media_before_fetch():
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.url.path == "/v21.0/me":
            return httpx.Response(200, json={"id": "42"})
        if request.url.path == "/v21.0/42/media":
            return httpx.Response(200, json={"data": [{"id": "media123"}]})
        if request.url.path == "/v21.0/media123":
            return httpx.Response(
                200,
                json={
                    "id": "media123",
                    "caption": "hello",
                    "shortcode": "ABC123",
                    "media_type": "IMAGE",
                    "timestamp": "2026-03-12T12:00:00+0000",
                    "like_count": 7,
                    "comments_count": 2,
                    "media_url": "https://example.com/photo.jpg",
                    "permalink": "https://instagram.com/p/ABC123/",
                },
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = GraphBackend(token="tok", login_type="ig", client=client)

    result = backend.analytics_post("latest")

    assert requests == [
        ("GET", "/v21.0/me"),
        ("GET", "/v21.0/42/media"),
        ("GET", "/v21.0/media123"),
    ]
    assert result["id"] == "media123"
    assert result["code"] == "ABC123"
    assert result["comment_count"] == 2


def test_dm_send_media_marks_video_attachments_correctly():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/v21.0/me":
            return httpx.Response(200, json={"id": "42"})
        if request.method == "POST" and request.url.path == "/v21.0/42/messages":
            body = parse_qs(request.content.decode())
            message = json.loads(body["message"][0])
            assert message["attachment"]["type"] == "video"
            assert message["attachment"]["payload"]["url"] == "https://example.com/clip.mp4"
            recipient = json.loads(body["recipient"][0])
            assert recipient["id"] == "123456"
            return httpx.Response(200, json={"message_id": "mid.1"})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = GraphBackend(token="tok", login_type="fb", client=client)

    result = backend.dm_send_media("123456", "https://example.com/clip.mp4")

    assert result["message_id"] == "mid.1"
    assert result["status"] == "sent"
