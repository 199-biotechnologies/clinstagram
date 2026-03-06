from clinstagram.auth.keychain import SecretsStore


def test_set_and_get_secret():
    store = SecretsStore(backend="memory")
    store.set("default", "graph_ig_token", "tok_abc123")
    assert store.get("default", "graph_ig_token") == "tok_abc123"


def test_get_missing_returns_none():
    store = SecretsStore(backend="memory")
    assert store.get("default", "nonexistent") is None


def test_delete_secret():
    store = SecretsStore(backend="memory")
    store.set("default", "graph_ig_token", "tok_abc123")
    store.delete("default", "graph_ig_token")
    assert store.get("default", "graph_ig_token") is None


def test_list_keys():
    store = SecretsStore(backend="memory")
    store.set("acct1", "graph_ig_token", "a")
    store.set("acct1", "graph_fb_token", "b")
    store.set("acct1", "private_session", "c")
    keys = store.list_keys("acct1")
    assert set(keys) == {"graph_ig_token", "graph_fb_token", "private_session"}


def test_has_backend():
    store = SecretsStore(backend="memory")
    assert not store.has_backend("default", "graph_ig")
    store.set("default", "graph_ig_token", "tok")
    assert store.has_backend("default", "graph_ig")
