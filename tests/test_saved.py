"""Tests for the saved-posts / collections feature (private backend)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from clinstagram.backends.capabilities import Feature, READ_ONLY_FEATURES
from clinstagram.backends.private import PrivateBackend


def _make_media(pk: str, media_type: int, code: str = "abc") -> MagicMock:
    m = MagicMock()
    m.pk = int(pk)
    m.media_type = media_type
    m.code = code
    return m


def _make_collection(cid: str, name: str, count: int = 0) -> MagicMock:
    c = MagicMock()
    c.id = cid
    c.name = name
    c.media_count = count
    return c


class TestSavedList:
    def test_default_all_posts_resolves_named_collection(self):
        cl = MagicMock()
        cl.collections.return_value = [
            _make_collection("100", "All Posts", 5),
        ]
        cl.collection_medias.return_value = [
            _make_media("1", 2),
            _make_media("2", 1),
        ]
        backend = PrivateBackend(client=cl)
        result = backend.saved_list()
        # "All Posts" collection pk used
        cl.collection_medias.assert_called_once_with("100", amount=50)
        assert len(result) == 2

    def test_named_collection_match(self):
        cl = MagicMock()
        cl.collections.return_value = [
            _make_collection("100", "All Posts", 5),
            _make_collection("200", "Recipes", 3),
        ]
        cl.collection_medias.return_value = [_make_media("9", 2)]
        backend = PrivateBackend(client=cl)
        result = backend.saved_list(collection="recipes")
        cl.collection_medias.assert_called_once_with("200", amount=50)
        assert result[0]["id"] == "9"

    def test_collection_not_found_raises(self):
        cl = MagicMock()
        cl.collections.return_value = [_make_collection("100", "All Posts", 1)]
        backend = PrivateBackend(client=cl)
        with pytest.raises(Exception):
            backend.saved_list(collection="does-not-exist")

    def test_media_type_filter(self):
        cl = MagicMock()
        cl.collections.return_value = [_make_collection("100", "All Posts", 5)]
        cl.collection_medias.return_value = [
            _make_media("1", 2),  # video
            _make_media("2", 1),  # photo
            _make_media("3", 8),  # album
        ]
        backend = PrivateBackend(client=cl)
        result = backend.saved_list(media_types=[2, 8])
        ids = {r["id"] for r in result}
        assert ids == {"1", "3"}

    def test_fallback_to_biggest_when_no_all_posts(self):
        cl = MagicMock()
        cl.collections.return_value = [
            _make_collection("10", "Travel", 2),
            _make_collection("20", "Music", 9),
        ]
        cl.collection_medias.return_value = [_make_media("1", 2)]
        backend = PrivateBackend(client=cl)
        backend.saved_list()  # empty collection arg
        cl.collection_medias.assert_called_once_with("20", amount=50)


class TestSavedDownload:
    def test_downloads_videos_and_albums_only_by_default(self):
        cl = MagicMock()
        cl.collections.return_value = [_make_collection("100", "All Posts", 5)]
        cl.collection_medias.return_value = [
            _make_media("1", 2),  # video -> video_download
            _make_media("2", 1),  # photo -> skipped
            _make_media("3", 8),  # album -> album_download
        ]
        cl.media_info.side_effect = lambda pk: _make_media(str(pk), {1: 2, 2: 1, 3: 8}[pk])
        cl.video_download.return_value = "/tmp/v.mp4"
        cl.album_download.return_value = ["/tmp/a1.jpg", "/tmp/a2.jpg"]

        backend = PrivateBackend(client=cl)
        result = backend.saved_download(output_dir="/tmp/saved_out")

        assert result["count"] == 2
        # video + album downloads happened; photo skipped
        cl.video_download.assert_called_once()
        cl.album_download.assert_called_once()
        cl.photo_download.assert_not_called()
        codes = {item["media_id"] for item in result["items"]}
        assert codes == {"1", "3"}

    def test_all_media_includes_photos(self):
        cl = MagicMock()
        cl.collections.return_value = [_make_collection("100", "All Posts", 1)]
        cl.collection_medias.return_value = [_make_media("1", 1)]
        cl.media_info.return_value = _make_media("1", 1)
        cl.photo_download.return_value = "/tmp/p.jpg"

        backend = PrivateBackend(client=cl)
        result = backend.saved_download(output_dir="/tmp/saved_out", media_types=[1])
        assert result["count"] == 1
        cl.photo_download.assert_called_once()

    def test_empty_collection_raises(self):
        cl = MagicMock()
        cl.collections.return_value = []
        backend = PrivateBackend(client=cl)
        with pytest.raises(Exception):
            backend.saved_download(output_dir="/tmp/x")


def test_features_are_read_only():
    assert Feature.SAVED_LIST in READ_ONLY_FEATURES
    assert Feature.SAVED_DOWNLOAD in READ_ONLY_FEATURES
