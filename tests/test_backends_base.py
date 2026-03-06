"""Verify both backends implement the Backend ABC."""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import httpx
import pytest

from clinstagram.backends.base import Backend
from clinstagram.backends.graph import GraphBackend
from clinstagram.backends.private import PrivateBackend


def _abstract_method_names() -> set[str]:
    """Return the names of all abstract methods (and abstract properties) on Backend."""
    names = set()
    for name, _ in inspect.getmembers(Backend):
        if name.startswith("_"):
            continue
        # Check if it's declared abstract
        obj = getattr(Backend, name, None)
        if obj is None:
            continue
        # abstractmethod or abstractproperty (via @property @abstractmethod)
        if getattr(obj, "__isabstractmethod__", False):
            names.add(name)
        # Handle @property wrapping @abstractmethod
        if isinstance(obj, property) and getattr(obj.fget, "__isabstractmethod__", False):
            names.add(name)
    return names


class TestGraphBackendImplementsInterface:
    def test_is_subclass(self):
        assert issubclass(GraphBackend, Backend)

    def test_can_instantiate(self):
        client = httpx.Client()
        try:
            backend = GraphBackend(token="test-token", login_type="ig", client=client)
            assert isinstance(backend, Backend)
        finally:
            client.close()

    def test_all_abstract_methods_implemented(self):
        abstract = _abstract_method_names()
        assert abstract, "Expected at least one abstract method on Backend"
        for method_name in abstract:
            impl = getattr(GraphBackend, method_name, None)
            assert impl is not None, f"GraphBackend missing: {method_name}"
            if isinstance(impl, property):
                assert not getattr(impl.fget, "__isabstractmethod__", False), (
                    f"GraphBackend.{method_name} is still abstract"
                )
            else:
                assert not getattr(impl, "__isabstractmethod__", False), (
                    f"GraphBackend.{method_name} is still abstract"
                )

    def test_name_property(self):
        client = httpx.Client()
        try:
            ig = GraphBackend(token="t", login_type="ig", client=client)
            assert ig.name == "graph_ig"
        finally:
            client.close()

        client2 = httpx.Client()
        try:
            fb = GraphBackend(token="t", login_type="fb", client=client2)
            assert fb.name == "graph_fb"
        finally:
            client2.close()

    def test_invalid_login_type_raises(self):
        client = httpx.Client()
        try:
            with pytest.raises(ValueError, match="login_type must be"):
                GraphBackend(token="t", login_type="bad", client=client)
        finally:
            client.close()


class TestPrivateBackendImplementsInterface:
    def test_is_subclass(self):
        assert issubclass(PrivateBackend, Backend)

    def test_can_instantiate(self):
        mock_client = MagicMock()
        backend = PrivateBackend(client=mock_client)
        assert isinstance(backend, Backend)

    def test_all_abstract_methods_implemented(self):
        abstract = _abstract_method_names()
        for method_name in abstract:
            impl = getattr(PrivateBackend, method_name, None)
            assert impl is not None, f"PrivateBackend missing: {method_name}"
            if isinstance(impl, property):
                assert not getattr(impl.fget, "__isabstractmethod__", False), (
                    f"PrivateBackend.{method_name} is still abstract"
                )
            else:
                assert not getattr(impl, "__isabstractmethod__", False), (
                    f"PrivateBackend.{method_name} is still abstract"
                )

    def test_name_property(self):
        mock_client = MagicMock()
        backend = PrivateBackend(client=mock_client)
        assert backend.name == "private"


class TestBackendCannotBeInstantiated:
    def test_abstract_class_raises(self):
        with pytest.raises(TypeError):
            Backend()  # type: ignore[abstract]
