from clinstagram.config import GlobalConfig, ComplianceMode, load_config, save_config


def test_save_and_reload(tmp_path):
    cfg = GlobalConfig(compliance_mode=ComplianceMode.OFFICIAL_ONLY)
    save_config(cfg, tmp_path)
    loaded = load_config(tmp_path)
    assert loaded.compliance_mode == ComplianceMode.OFFICIAL_ONLY
    assert loaded.rate_limits.private_dm_per_hour == 30


def test_default_config_created_on_first_load(tmp_path):
    cfg = load_config(tmp_path)
    assert cfg.compliance_mode == ComplianceMode.HYBRID_SAFE
    assert (tmp_path / "config.toml").exists()
    assert (tmp_path / "accounts").is_dir()
    assert (tmp_path / "logs").is_dir()


def test_modify_and_persist(tmp_path):
    cfg = load_config(tmp_path)
    cfg.compliance_mode = ComplianceMode.PRIVATE_ENABLED
    cfg.rate_limits.private_dm_per_hour = 10
    save_config(cfg, tmp_path)
    reloaded = load_config(tmp_path)
    assert reloaded.compliance_mode == ComplianceMode.PRIVATE_ENABLED
    assert reloaded.rate_limits.private_dm_per_hour == 10
