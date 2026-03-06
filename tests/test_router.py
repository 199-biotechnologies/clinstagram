from clinstagram.backends.router import Router
from clinstagram.backends.capabilities import Feature
from clinstagram.config import ComplianceMode
from clinstagram.auth.keychain import SecretsStore


def make_router(mode=ComplianceMode.HYBRID_SAFE, backends=None):
    secrets = SecretsStore(backend="memory")
    if backends:
        for b in backends:
            if b == "graph_ig":
                secrets.set("default", "graph_ig_token", "tok")
            elif b == "graph_fb":
                secrets.set("default", "graph_fb_token", "tok")
            elif b == "private":
                secrets.set("default", "private_session", "sess")
    return Router(account="default", compliance_mode=mode, secrets=secrets)


def test_routes_post_to_graph_ig():
    r = make_router(backends=["graph_ig"])
    backend = r.route(Feature.POST_PHOTO)
    assert backend == "graph_ig"


def test_routes_dm_to_graph_fb():
    r = make_router(backends=["graph_fb"])
    backend = r.route(Feature.DM_INBOX)
    assert backend == "graph_fb"


def test_routes_dm_to_private_when_no_graph_fb():
    r = make_router(mode=ComplianceMode.PRIVATE_ENABLED, backends=["private"])
    backend = r.route(Feature.DM_INBOX)
    assert backend == "private"


def test_official_only_blocks_private():
    r = make_router(mode=ComplianceMode.OFFICIAL_ONLY, backends=["private"])
    backend = r.route(Feature.DM_INBOX)
    assert backend is None


def test_hybrid_safe_allows_private_readonly():
    r = make_router(mode=ComplianceMode.HYBRID_SAFE, backends=["private"])
    backend = r.route(Feature.DM_INBOX)
    assert backend == "private"


def test_hybrid_safe_blocks_private_write():
    r = make_router(mode=ComplianceMode.HYBRID_SAFE, backends=["private"])
    backend = r.route(Feature.DM_COLD_SEND)
    assert backend is None


def test_prefers_graph_over_private():
    r = make_router(mode=ComplianceMode.PRIVATE_ENABLED, backends=["graph_fb", "private"])
    backend = r.route(Feature.DM_INBOX)
    assert backend == "graph_fb"


def test_no_backends_returns_none():
    r = make_router(backends=[])
    backend = r.route(Feature.POST_PHOTO)
    assert backend is None


def test_follow_blocked_by_default():
    r = make_router(mode=ComplianceMode.HYBRID_SAFE, backends=["private"])
    backend = r.route(Feature.FOLLOW)
    assert backend is None
