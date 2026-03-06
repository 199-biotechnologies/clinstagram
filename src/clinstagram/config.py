from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
import tomli_w


class ComplianceMode(str, Enum):
    OFFICIAL_ONLY = "official-only"
    HYBRID_SAFE = "hybrid-safe"
    PRIVATE_ENABLED = "private-enabled"


class BackendType(str, Enum):
    AUTO = "auto"
    GRAPH_IG = "graph_ig"
    GRAPH_FB = "graph_fb"
    PRIVATE = "private"


class RateLimits(BaseModel):
    graph_dm_per_hour: int = 200
    private_dm_per_hour: int = 30
    private_follows_per_day: int = 20
    private_likes_per_hour: int = 20
    request_delay_min: float = 2.0
    request_delay_max: float = 5.0
    request_jitter: bool = True


class MediaStaging(BaseModel):
    provider: str = "local-only"
    cleanup_after_publish: bool = True


class GlobalConfig(BaseModel):
    default_account: str = "default"
    compliance_mode: ComplianceMode = ComplianceMode.HYBRID_SAFE
    preferred_backend: BackendType = BackendType.AUTO
    proxy: Optional[str] = None
    rate_limits: RateLimits = Field(default_factory=RateLimits)
    media_staging: MediaStaging = Field(default_factory=MediaStaging)


DEFAULT_CONFIG_DIR = Path.home() / ".clinstagram"


def get_config_dir(override: Optional[Path] = None) -> Path:
    return override or DEFAULT_CONFIG_DIR


def get_account_dir(account: str, config_dir: Optional[Path] = None) -> Path:
    return get_config_dir(config_dir) / "accounts" / account


def ensure_dirs(config_dir: Optional[Path] = None) -> Path:
    d = get_config_dir(config_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / "accounts").mkdir(exist_ok=True)
    (d / "logs").mkdir(exist_ok=True)
    return d


def load_config(config_dir: Optional[Path] = None) -> GlobalConfig:
    d = get_config_dir(config_dir)
    config_path = d / "config.toml"
    if not config_path.exists():
        ensure_dirs(config_dir)
        cfg = GlobalConfig()
        save_config(cfg, config_dir)
        return cfg
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    return GlobalConfig(**data)


def save_config(config: GlobalConfig, config_dir: Optional[Path] = None) -> None:
    d = ensure_dirs(config_dir)
    config_path = d / "config.toml"
    with open(config_path, "wb") as f:
        tomli_w.dump(config.model_dump(mode="json"), f)
