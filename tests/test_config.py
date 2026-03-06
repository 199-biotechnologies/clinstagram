from clinstagram.config import GlobalConfig, RateLimits, ComplianceMode, BackendType


def test_default_config():
    cfg = GlobalConfig()
    assert cfg.compliance_mode == ComplianceMode.HYBRID_SAFE
    assert cfg.default_account == "default"


def test_rate_limits_defaults():
    rl = RateLimits()
    assert rl.graph_dm_per_hour == 200
    assert rl.private_dm_per_hour == 30
    assert rl.request_jitter is True


def test_compliance_modes():
    for mode in ComplianceMode:
        cfg = GlobalConfig(compliance_mode=mode)
        assert cfg.compliance_mode == mode


def test_backend_types():
    assert BackendType.GRAPH_IG.value == "graph_ig"
    assert BackendType.GRAPH_FB.value == "graph_fb"
    assert BackendType.PRIVATE.value == "private"
    assert BackendType.AUTO.value == "auto"
