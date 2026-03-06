import os
from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel, Field
import tomli
import tomli_w

DEFAULT_CONFIG_DIR = Path.home() / ".clinstagram"

class RateLimits(BaseModel):
    graph_dm_per_hour: int = 200
    private_dm_per_hour: int = 50
    private_follows_per_day: int = 50
    private_likes_per_hour: int = 30
    request_delay_min: float = 1.0
    request_delay_max: float = 3.0

class GlobalConfig(BaseModel):
    default_account: str = "default"
    preferred_backend: str = "auto"
    rate_limits: RateLimits = Field(default_factory=RateLimits)

class AccountSettings(BaseModel):
    proxy: Optional[str] = None
    user_agent: Optional[str] = None
    device_id: Optional[str] = None

def get_account_dir(account_name: str) -> Path:
    return DEFAULT_CONFIG_DIR / "accounts" / account_name

def load_config() -> GlobalConfig:
    config_path = DEFAULT_CONFIG_DIR / "config.toml"
    if not config_path.exists():
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        (DEFAULT_CONFIG_DIR / "accounts").mkdir(exist_ok=True)
        (DEFAULT_CONFIG_DIR / "logs").mkdir(exist_ok=True)
        save_config(GlobalConfig())
        return GlobalConfig()
    
    with open(config_path, "rb") as f:
        data = tomli.load(f)
    return GlobalConfig(**data)

def save_config(config: GlobalConfig):
    config_path = DEFAULT_CONFIG_DIR / "config.toml"
    with open(config_path, "wb") as f:
        tomli_w.dump(config.model_dump(), f)

def load_account_settings(account_name: str) -> AccountSettings:
    settings_path = get_account_dir(account_name) / "settings.json"
    if not settings_path.exists():
        return AccountSettings()
    
    import json
    with open(settings_path, "r") as f:
        data = json.load(f)
    return AccountSettings(**data)
