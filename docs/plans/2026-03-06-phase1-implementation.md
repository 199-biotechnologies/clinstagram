# Phase 1: Foundation + Tests — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the core scaffold, config system, SQLite state, keychain secrets, capability matrix, backend router, auth commands, and test infrastructure for clinstagram.

**Architecture:** Typer CLI with three backends (graph_ig, graph_fb, private), policy-driven routing via a CAPABILITY_MATRIX, Pydantic models for config and responses, SQLite WAL for state, OS keychain for secrets. All commands support `--json` with structured exit codes 0-7.

**Tech Stack:** Python 3.12, typer, httpx, instagrapi, pydantic, rich, tomli/tomli-w, keyring, sqlite3, pytest

---

### Task 1: Clean Scaffold + pyproject.toml

**Files:**
- Rewrite: `pyproject.toml`
- Create: `src/clinstagram/__init__.py`
- Delete: `src/clinstagram/__pycache__/` (stale)

**Step 1: Rewrite pyproject.toml with correct deps and metadata**

```toml
[project]
name = "clinstagram"
version = "0.1.0"
description = "Hybrid Instagram CLI for OpenClaw — Graph API + Private API"
requires-python = ">=3.10"
dependencies = [
    "typer[all]>=0.12.0",
    "httpx>=0.27.0",
    "instagrapi>=2.3.0",
    "rich>=13.7.0",
    "tomli>=2.0.1; python_version < '3.11'",
    "tomli-w>=1.0.0",
    "pydantic>=2.6.0",
    "keyring>=25.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[project.scripts]
clinstagram = "clinstagram.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/clinstagram"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 2: Create __init__.py with version**

```python
__version__ = "0.1.0"
```

**Step 3: Clean up stale pycache and install**

Run:
```bash
rm -rf src/clinstagram/__pycache__
pip install -e ".[dev]"
```
Expected: Install succeeds, `clinstagram --help` works.

**Step 4: Commit**

```bash
git init && git add pyproject.toml src/clinstagram/__init__.py
git commit -m "feat: clean scaffold with correct dependencies"
```

---

### Task 2: Pydantic Models — Config + Response Types

**Files:**
- Rewrite: `src/clinstagram/config.py`
- Create: `src/clinstagram/models.py`
- Test: `tests/test_config.py`, `tests/test_models.py`
- Create: `tests/conftest.py`

**Step 1: Write failing tests for config models**

`tests/conftest.py`:
```python
import pytest
from pathlib import Path
import tempfile

@pytest.fixture
def tmp_config_dir(tmp_path):
    """Provide a temporary config directory instead of ~/.clinstagram/"""
    return tmp_path / ".clinstagram"
```

`tests/test_config.py`:
```python
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
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — ComplianceMode, BackendType not defined

**Step 3: Implement config.py**

```python
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
```

**Step 4: Write failing tests for response models**

`tests/test_models.py`:
```python
import json
from clinstagram.models import CLIResponse, CLIError, ExitCode

def test_success_response():
    r = CLIResponse(data={"thread_id": "123"}, backend_used="graph_fb")
    assert r.exit_code == ExitCode.SUCCESS
    d = json.loads(r.to_json())
    assert d["data"]["thread_id"] == "123"
    assert d["backend_used"] == "graph_fb"

def test_error_response():
    e = CLIError(
        exit_code=ExitCode.AUTH_ERROR,
        error="session_expired",
        remediation="Run: clinstagram auth login",
    )
    d = json.loads(e.to_json())
    assert d["exit_code"] == 2
    assert d["remediation"] == "Run: clinstagram auth login"

def test_all_exit_codes():
    assert ExitCode.SUCCESS == 0
    assert ExitCode.USER_ERROR == 1
    assert ExitCode.AUTH_ERROR == 2
    assert ExitCode.RATE_LIMITED == 3
    assert ExitCode.API_ERROR == 4
    assert ExitCode.CHALLENGE_REQUIRED == 5
    assert ExitCode.POLICY_BLOCKED == 6
    assert ExitCode.CAPABILITY_UNAVAILABLE == 7
```

**Step 5: Implement models.py**

```python
from __future__ import annotations

import json
from enum import IntEnum
from typing import Any, Optional

from pydantic import BaseModel


class ExitCode(IntEnum):
    SUCCESS = 0
    USER_ERROR = 1
    AUTH_ERROR = 2
    RATE_LIMITED = 3
    API_ERROR = 4
    CHALLENGE_REQUIRED = 5
    POLICY_BLOCKED = 6
    CAPABILITY_UNAVAILABLE = 7


class CLIResponse(BaseModel):
    exit_code: ExitCode = ExitCode.SUCCESS
    data: Any = None
    backend_used: Optional[str] = None

    def to_json(self) -> str:
        return self.model_dump_json()


class CLIError(BaseModel):
    exit_code: ExitCode
    error: str
    remediation: Optional[str] = None
    retry_after: Optional[int] = None
    challenge_type: Optional[str] = None
    challenge_url: Optional[str] = None

    def to_json(self) -> str:
        return self.model_dump_json(exclude_none=True)
```

**Step 6: Run all tests**

Run: `pytest tests/test_config.py tests/test_models.py -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add src/clinstagram/config.py src/clinstagram/models.py tests/
git commit -m "feat: pydantic config + response models with compliance modes and exit codes"
```

---

### Task 3: SQLite State Layer

**Files:**
- Create: `src/clinstagram/db.py`
- Test: `tests/test_db.py`

**Step 1: Write failing tests**

`tests/test_db.py`:
```python
from clinstagram.db import Database

def test_init_creates_tables(tmp_path):
    db = Database(tmp_path / "test.db")
    tables = db.list_tables()
    assert "rate_limits" in tables
    assert "capabilities" in tables
    assert "audit_log" in tables
    assert "user_cache" in tables
    assert "thread_map" in tables

def test_record_rate_limit(tmp_path):
    db = Database(tmp_path / "test.db")
    db.record_action("default", "graph_fb", "dm_send")
    db.record_action("default", "graph_fb", "dm_send")
    count = db.get_action_count("default", "graph_fb", "dm_send", window_minutes=60)
    assert count == 2

def test_check_rate_limit_within_budget(tmp_path):
    db = Database(tmp_path / "test.db")
    assert db.check_rate_limit("default", "graph_fb", "dm_send", limit=200, window_minutes=60)

def test_check_rate_limit_exceeded(tmp_path):
    db = Database(tmp_path / "test.db")
    for _ in range(5):
        db.record_action("default", "private", "dm_send")
    assert not db.check_rate_limit("default", "private", "dm_send", limit=5, window_minutes=60)

def test_cache_user(tmp_path):
    db = Database(tmp_path / "test.db")
    db.cache_user("alice", user_id="123", private_pk="456")
    user = db.get_cached_user("alice")
    assert user["user_id"] == "123"
    assert user["private_pk"] == "456"

def test_cache_user_miss(tmp_path):
    db = Database(tmp_path / "test.db")
    assert db.get_cached_user("nonexistent") is None

def test_audit_log(tmp_path):
    db = Database(tmp_path / "test.db")
    db.log_audit("default", "graph_fb", "dm send", '{"user": "@alice"}', 0, "sent")
    rows = db.get_recent_audit(limit=1)
    assert len(rows) == 1
    assert rows[0]["command"] == "dm send"
```

**Step 2: Run to verify fail**

Run: `pytest tests/test_db.py -v`
Expected: FAIL — Database not defined

**Step 3: Implement db.py**

```python
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account TEXT NOT NULL,
                backend TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp DATETIME DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_rate_limits_lookup
                ON rate_limits(account, backend, action, timestamp);

            CREATE TABLE IF NOT EXISTS capabilities (
                account TEXT NOT NULL,
                backend TEXT NOT NULL,
                feature TEXT NOT NULL,
                available BOOLEAN NOT NULL DEFAULT 1,
                last_probed DATETIME DEFAULT (datetime('now')),
                PRIMARY KEY (account, backend, feature)
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT (datetime('now')),
                account TEXT,
                backend TEXT,
                command TEXT,
                args TEXT,
                exit_code INTEGER,
                response_summary TEXT
            );

            CREATE TABLE IF NOT EXISTS user_cache (
                username TEXT PRIMARY KEY,
                user_id TEXT,
                graph_scoped_id TEXT,
                private_pk TEXT,
                last_updated DATETIME DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS thread_map (
                username TEXT PRIMARY KEY,
                graph_thread_id TEXT,
                private_thread_id TEXT,
                last_updated DATETIME DEFAULT (datetime('now'))
            );
        """)
        self.conn.commit()

    def list_tables(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return [r["name"] for r in rows]

    def record_action(self, account: str, backend: str, action: str) -> None:
        self.conn.execute(
            "INSERT INTO rate_limits (account, backend, action) VALUES (?, ?, ?)",
            (account, backend, action),
        )
        self.conn.commit()

    def get_action_count(
        self, account: str, backend: str, action: str, window_minutes: int = 60
    ) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM rate_limits WHERE account=? AND backend=? AND action=? AND timestamp>=?",
            (account, backend, action, cutoff.strftime("%Y-%m-%d %H:%M:%S")),
        ).fetchone()
        return row["cnt"]

    def check_rate_limit(
        self, account: str, backend: str, action: str, limit: int, window_minutes: int = 60
    ) -> bool:
        return self.get_action_count(account, backend, action, window_minutes) < limit

    def cache_user(
        self,
        username: str,
        user_id: Optional[str] = None,
        graph_scoped_id: Optional[str] = None,
        private_pk: Optional[str] = None,
    ) -> None:
        self.conn.execute(
            """INSERT INTO user_cache (username, user_id, graph_scoped_id, private_pk)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(username) DO UPDATE SET
                 user_id=COALESCE(excluded.user_id, user_cache.user_id),
                 graph_scoped_id=COALESCE(excluded.graph_scoped_id, user_cache.graph_scoped_id),
                 private_pk=COALESCE(excluded.private_pk, user_cache.private_pk),
                 last_updated=datetime('now')""",
            (username, user_id, graph_scoped_id, private_pk),
        )
        self.conn.commit()

    def get_cached_user(self, username: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM user_cache WHERE username=?", (username,)
        ).fetchone()
        return dict(row) if row else None

    def log_audit(
        self,
        account: str,
        backend: str,
        command: str,
        args: str,
        exit_code: int,
        response_summary: str,
    ) -> None:
        self.conn.execute(
            "INSERT INTO audit_log (account, backend, command, args, exit_code, response_summary) VALUES (?, ?, ?, ?, ?, ?)",
            (account, backend, command, args, exit_code, response_summary),
        )
        self.conn.commit()

    def get_recent_audit(self, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.conn.close()
```

**Step 4: Run tests**

Run: `pytest tests/test_db.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/clinstagram/db.py tests/test_db.py
git commit -m "feat: SQLite state layer with rate limits, user cache, audit log"
```

---

### Task 4: Keychain Secrets Abstraction

**Files:**
- Create: `src/clinstagram/auth/__init__.py`
- Create: `src/clinstagram/auth/keychain.py`
- Test: `tests/test_keychain.py`

**Step 1: Write failing tests**

`tests/test_keychain.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
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
```

**Step 2: Run to verify fail**

Run: `pytest tests/test_keychain.py -v`
Expected: FAIL — SecretsStore not defined

**Step 3: Implement keychain.py**

```python
from __future__ import annotations

from typing import Optional

SERVICE_PREFIX = "clinstagram"

# Maps backend name to the secret key suffix
BACKEND_TOKEN_MAP = {
    "graph_ig": "graph_ig_token",
    "graph_fb": "graph_fb_token",
    "private": "private_session",
}


class SecretsStore:
    """Abstraction over secret storage. Supports 'memory' (testing), 'keyring' (production), 'file' (CI)."""

    def __init__(self, backend: str = "keyring"):
        self.backend = backend
        self._memory: dict[str, str] = {}

    def _key(self, account: str, name: str) -> str:
        return f"{SERVICE_PREFIX}/{account}/{name}"

    def set(self, account: str, name: str, value: str) -> None:
        key = self._key(account, name)
        if self.backend == "memory":
            self._memory[key] = value
        elif self.backend == "keyring":
            import keyring as kr
            kr.set_password(SERVICE_PREFIX, key, value)
        else:
            raise ValueError(f"Unknown secrets backend: {self.backend}")

    def get(self, account: str, name: str) -> Optional[str]:
        key = self._key(account, name)
        if self.backend == "memory":
            return self._memory.get(key)
        elif self.backend == "keyring":
            import keyring as kr
            return kr.get_password(SERVICE_PREFIX, key)
        return None

    def delete(self, account: str, name: str) -> None:
        key = self._key(account, name)
        if self.backend == "memory":
            self._memory.pop(key, None)
        elif self.backend == "keyring":
            import keyring as kr
            try:
                kr.delete_password(SERVICE_PREFIX, key)
            except kr.errors.PasswordDeleteError:
                pass

    def list_keys(self, account: str) -> list[str]:
        prefix = self._key(account, "")
        if self.backend == "memory":
            return [k.removeprefix(prefix) for k in self._memory if k.startswith(prefix)]
        # keyring doesn't support listing — check known keys
        return [
            name
            for name in ["graph_ig_token", "graph_fb_token", "private_session"]
            if self.get(account, name) is not None
        ]

    def has_backend(self, account: str, backend_name: str) -> bool:
        token_key = BACKEND_TOKEN_MAP.get(backend_name)
        if not token_key:
            return False
        return self.get(account, token_key) is not None
```

**Step 4: Run tests**

Run: `pytest tests/test_keychain.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/clinstagram/auth/ tests/test_keychain.py
git commit -m "feat: keychain secrets abstraction with memory/keyring backends"
```

---

### Task 5: Capability Matrix + Router

**Files:**
- Create: `src/clinstagram/backends/__init__.py`
- Create: `src/clinstagram/backends/capabilities.py`
- Create: `src/clinstagram/backends/router.py`
- Test: `tests/test_capabilities.py`, `tests/test_router.py`

**Step 1: Write failing tests for capabilities**

`tests/test_capabilities.py`:
```python
from clinstagram.backends.capabilities import CAPABILITY_MATRIX, Feature, can_backend_do

def test_graph_ig_can_post():
    assert can_backend_do("graph_ig", Feature.POST_PHOTO)
    assert can_backend_do("graph_ig", Feature.POST_VIDEO)
    assert can_backend_do("graph_ig", Feature.POST_REEL)

def test_graph_ig_cannot_dm():
    assert not can_backend_do("graph_ig", Feature.DM_INBOX)
    assert not can_backend_do("graph_ig", Feature.DM_SEND)

def test_graph_fb_can_dm():
    assert can_backend_do("graph_fb", Feature.DM_INBOX)
    assert can_backend_do("graph_fb", Feature.DM_REPLY)

def test_graph_fb_cannot_cold_dm():
    assert not can_backend_do("graph_fb", Feature.DM_COLD_SEND)

def test_private_can_everything():
    for feat in Feature:
        assert can_backend_do("private", feat)

def test_feature_enum_completeness():
    assert Feature.POST_PHOTO in Feature
    assert Feature.DM_INBOX in Feature
    assert Feature.STORY_POST in Feature
    assert Feature.FOLLOW in Feature
    assert Feature.ANALYTICS_PROFILE in Feature
```

**Step 2: Write failing tests for router**

`tests/test_router.py`:
```python
import pytest
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
    assert backend is None  # No Graph FB, private blocked by policy

def test_hybrid_safe_allows_private_readonly():
    r = make_router(mode=ComplianceMode.HYBRID_SAFE, backends=["private"])
    backend = r.route(Feature.DM_INBOX)  # read-only
    assert backend == "private"

def test_hybrid_safe_blocks_private_write():
    r = make_router(mode=ComplianceMode.HYBRID_SAFE, backends=["private"])
    backend = r.route(Feature.DM_COLD_SEND)  # write, private only
    assert backend is None

def test_prefers_graph_over_private():
    r = make_router(mode=ComplianceMode.PRIVATE_ENABLED, backends=["graph_fb", "private"])
    backend = r.route(Feature.DM_INBOX)
    assert backend == "graph_fb"  # Graph preferred

def test_no_backends_returns_none():
    r = make_router(backends=[])
    backend = r.route(Feature.POST_PHOTO)
    assert backend is None

def test_follow_blocked_by_default():
    """Follow is private-only AND requires --enable-growth-actions (not modeled in router, just policy)."""
    r = make_router(mode=ComplianceMode.HYBRID_SAFE, backends=["private"])
    backend = r.route(Feature.FOLLOW)
    assert backend is None  # growth action, blocked in hybrid-safe
```

**Step 3: Implement capabilities.py**

```python
from __future__ import annotations

from enum import Enum


class Feature(str, Enum):
    # Posting
    POST_PHOTO = "post_photo"
    POST_VIDEO = "post_video"
    POST_REEL = "post_reel"
    POST_CAROUSEL = "post_carousel"
    # DMs
    DM_INBOX = "dm_inbox"
    DM_PENDING = "dm_pending"
    DM_THREAD = "dm_thread"
    DM_REPLY = "dm_reply"
    DM_COLD_SEND = "dm_cold_send"
    DM_SEND_MEDIA = "dm_send_media"
    DM_SEARCH = "dm_search"
    DM_DELETE = "dm_delete"
    DM_MUTE = "dm_mute"
    DM_LISTEN = "dm_listen"
    # Stories
    STORY_LIST = "story_list"
    STORY_POST = "story_post"
    STORY_VIEW_OTHERS = "story_view_others"
    STORY_VIEWERS = "story_viewers"
    # Comments
    COMMENTS_LIST = "comments_list"
    COMMENTS_REPLY = "comments_reply"
    COMMENTS_DELETE = "comments_delete"
    # Analytics
    ANALYTICS_PROFILE = "analytics_profile"
    ANALYTICS_POST = "analytics_post"
    ANALYTICS_HASHTAG = "analytics_hashtag"
    # Followers
    FOLLOWERS_LIST = "followers_list"
    FOLLOWERS_FOLLOWING = "followers_following"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    # User
    USER_INFO = "user_info"
    USER_SEARCH = "user_search"


# True = backend supports this feature
CAPABILITY_MATRIX: dict[str, set[Feature]] = {
    "graph_ig": {
        Feature.POST_PHOTO, Feature.POST_VIDEO, Feature.POST_REEL, Feature.POST_CAROUSEL,
        Feature.COMMENTS_LIST, Feature.COMMENTS_REPLY, Feature.COMMENTS_DELETE,
        Feature.ANALYTICS_PROFILE, Feature.ANALYTICS_POST, Feature.ANALYTICS_HASHTAG,
        Feature.USER_INFO, Feature.USER_SEARCH,
    },
    "graph_fb": {
        Feature.POST_PHOTO, Feature.POST_VIDEO, Feature.POST_REEL, Feature.POST_CAROUSEL,
        Feature.DM_INBOX, Feature.DM_THREAD, Feature.DM_REPLY, Feature.DM_SEND_MEDIA,
        Feature.DM_LISTEN,
        Feature.STORY_POST,
        Feature.COMMENTS_LIST, Feature.COMMENTS_REPLY, Feature.COMMENTS_DELETE,
        Feature.ANALYTICS_PROFILE, Feature.ANALYTICS_POST, Feature.ANALYTICS_HASHTAG,
        Feature.USER_INFO, Feature.USER_SEARCH,
    },
    "private": set(Feature),  # Private API can do everything
}

# Features that are read-only (allowed in hybrid-safe for private backend)
READ_ONLY_FEATURES: set[Feature] = {
    Feature.DM_INBOX, Feature.DM_PENDING, Feature.DM_THREAD, Feature.DM_SEARCH,
    Feature.DM_LISTEN,
    Feature.STORY_LIST, Feature.STORY_VIEW_OTHERS, Feature.STORY_VIEWERS,
    Feature.COMMENTS_LIST,
    Feature.ANALYTICS_PROFILE, Feature.ANALYTICS_POST, Feature.ANALYTICS_HASHTAG,
    Feature.FOLLOWERS_LIST, Feature.FOLLOWERS_FOLLOWING,
    Feature.USER_INFO, Feature.USER_SEARCH,
}

# Growth actions — require explicit opt-in
GROWTH_ACTIONS: set[Feature] = {Feature.FOLLOW, Feature.UNFOLLOW}


def can_backend_do(backend: str, feature: Feature) -> bool:
    caps = CAPABILITY_MATRIX.get(backend, set())
    return feature in caps
```

**Step 4: Implement router.py**

```python
from __future__ import annotations

from typing import Optional

from clinstagram.auth.keychain import SecretsStore
from clinstagram.backends.capabilities import (
    CAPABILITY_MATRIX,
    GROWTH_ACTIONS,
    READ_ONLY_FEATURES,
    Feature,
    can_backend_do,
)
from clinstagram.config import ComplianceMode


# Backend preference order (most official first)
BACKEND_PREFERENCE = ["graph_ig", "graph_fb", "private"]


class Router:
    def __init__(
        self,
        account: str,
        compliance_mode: ComplianceMode,
        secrets: SecretsStore,
    ):
        self.account = account
        self.compliance_mode = compliance_mode
        self.secrets = secrets

    def _available_backends(self) -> list[str]:
        return [b for b in BACKEND_PREFERENCE if self.secrets.has_backend(self.account, b)]

    def _is_allowed_by_policy(self, backend: str, feature: Feature) -> bool:
        if self.compliance_mode == ComplianceMode.OFFICIAL_ONLY:
            return backend != "private"

        if self.compliance_mode == ComplianceMode.HYBRID_SAFE:
            if backend == "private":
                if feature in GROWTH_ACTIONS:
                    return False
                return feature in READ_ONLY_FEATURES
            return True

        # PRIVATE_ENABLED — allow everything except growth actions require explicit flag
        # (growth action gating handled at CLI layer, not router)
        return True

    def route(self, feature: Feature) -> Optional[str]:
        available = self._available_backends()
        for backend in BACKEND_PREFERENCE:
            if backend not in available:
                continue
            if not can_backend_do(backend, feature):
                continue
            if not self._is_allowed_by_policy(backend, feature):
                continue
            return backend
        return None
```

**Step 5: Run all tests**

Run: `pytest tests/test_capabilities.py tests/test_router.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add src/clinstagram/backends/ tests/test_capabilities.py tests/test_router.py
git commit -m "feat: capability matrix + policy-driven router with compliance modes"
```

---

### Task 6: CLI App — Rewrite with Full Structure

**Files:**
- Rewrite: `src/clinstagram/cli.py`
- Create: `src/clinstagram/commands/__init__.py`
- Create: `src/clinstagram/commands/auth.py`
- Create: `src/clinstagram/commands/config_cmd.py`
- Test: `tests/test_cli.py`

**Step 1: Write failing tests**

`tests/test_cli.py`:
```python
from typer.testing import CliRunner
from clinstagram.cli import app

runner = CliRunner()

def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "clinstagram" in result.stdout.lower() or "instagram" in result.stdout.lower()

def test_auth_status_no_config(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINSTAGRAM_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(app, ["auth", "status", "--json"])
    assert result.exit_code == 0

def test_config_show(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINSTAGRAM_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(app, ["config", "show", "--json"])
    assert result.exit_code == 0

def test_config_mode_set(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINSTAGRAM_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(app, ["config", "mode", "official-only"])
    assert result.exit_code == 0

def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout
```

**Step 2: Run to verify fail**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — various import errors / missing commands

**Step 3: Implement cli.py**

```python
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from clinstagram import __version__
from clinstagram.config import (
    BackendType,
    ComplianceMode,
    GlobalConfig,
    get_config_dir,
    load_config,
    save_config,
)

console = Console()

app = typer.Typer(
    name="clinstagram",
    help="Hybrid Instagram CLI for OpenClaw — Graph API + Private API",
    no_args_is_help=True,
)


def version_callback(value: bool):
    if value:
        typer.echo(f"clinstagram {__version__}")
        raise typer.Exit()


def _resolve_config_dir() -> Optional[Path]:
    env = os.environ.get("CLINSTAGRAM_CONFIG_DIR")
    return Path(env) if env else None


@app.callback()
def main(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    account: str = typer.Option("default", "--account", help="Account name"),
    backend: BackendType = typer.Option(BackendType.AUTO, "--backend", help="Force backend"),
    proxy: Optional[str] = typer.Option(None, "--proxy", help="Proxy URL for private API"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen"),
    verbose: bool = typer.Option(False, "--verbose", help="Debug logging"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable color output"),
    enable_growth: bool = typer.Option(False, "--enable-growth-actions", help="Unlock follow/unfollow"),
    version: bool = typer.Option(False, "--version", callback=version_callback, is_eager=True),
):
    config_dir = _resolve_config_dir()
    # Auto-detect JSON for piped output
    if not json_output and not sys.stdout.isatty():
        json_output = True
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output
    ctx.obj["account"] = account
    ctx.obj["backend"] = backend
    ctx.obj["proxy"] = proxy
    ctx.obj["dry_run"] = dry_run
    ctx.obj["verbose"] = verbose
    ctx.obj["no_color"] = no_color
    ctx.obj["enable_growth"] = enable_growth
    ctx.obj["config_dir"] = config_dir
    ctx.obj["config"] = load_config(config_dir)


# Import and register command groups
from clinstagram.commands.auth import auth_app
from clinstagram.commands.config_cmd import config_app

app.add_typer(auth_app, name="auth")
app.add_typer(config_app, name="config")

# Placeholder groups for future phases
post_app = typer.Typer(help="Post photos, videos, reels")
dm_app = typer.Typer(help="Manage direct messages")
story_app = typer.Typer(help="Manage stories")
comments_app = typer.Typer(help="Manage comments")
analytics_app = typer.Typer(help="View analytics")
followers_app = typer.Typer(help="Manage followers")
user_app = typer.Typer(help="User lookup")

for name, sub in [
    ("post", post_app), ("dm", dm_app), ("story", story_app),
    ("comments", comments_app), ("analytics", analytics_app),
    ("followers", followers_app), ("user", user_app),
]:
    # Add a placeholder command so typer doesn't complain about empty groups
    @sub.command("help")
    def _placeholder(ctx: typer.Context):
        """Coming in a future phase."""
        typer.echo(f"Commands for this group are not yet implemented.")
    app.add_typer(sub, name=name)
```

**Step 4: Implement commands/auth.py**

```python
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from clinstagram.auth.keychain import SecretsStore
from clinstagram.config import load_config

console = Console()
auth_app = typer.Typer(help="Manage authentication (Graph & Private)")


def _get_secrets(ctx: typer.Context) -> SecretsStore:
    return SecretsStore(backend="keyring")


@auth_app.command("status")
def status(ctx: typer.Context):
    """Show authentication status for the current account."""
    account = ctx.obj["account"]
    config = ctx.obj["config"]
    secrets = _get_secrets(ctx)

    backends = {}
    for name in ["graph_ig", "graph_fb", "private"]:
        backends[name] = secrets.has_backend(account, name)

    result = {
        "account": account,
        "compliance_mode": config.compliance_mode.value,
        "backends": backends,
    }

    if ctx.obj["json"]:
        typer.echo(json.dumps(result, indent=2))
    else:
        table = Table(title=f"Auth Status: {account}")
        table.add_column("Backend", style="cyan")
        table.add_column("Status", style="green")
        for name, active in backends.items():
            table.add_row(name, "Active" if active else "Not configured")
        console.print(table)
        console.print(f"Compliance mode: [bold]{config.compliance_mode.value}[/bold]")


@auth_app.command("connect-ig")
def connect_ig(ctx: typer.Context):
    """Connect via Instagram Login (OAuth). Enables posting, comments, analytics."""
    typer.echo("Instagram Login OAuth flow — coming in Phase 1 finalization.")
    raise typer.Exit(code=1)


@auth_app.command("connect-fb")
def connect_fb(ctx: typer.Context):
    """Connect via Facebook Login (OAuth + Page). Enables DMs, webhooks."""
    typer.echo("Facebook Login OAuth flow — coming in Phase 1 finalization.")
    raise typer.Exit(code=1)


@auth_app.command("login")
def login(ctx: typer.Context):
    """Login via Private API (instagrapi). Username/password/2FA."""
    typer.echo("Private API login flow — coming in Phase 1 finalization.")
    raise typer.Exit(code=1)


@auth_app.command("probe")
def probe(ctx: typer.Context):
    """Test all backends and report available features."""
    account = ctx.obj["account"]
    secrets = _get_secrets(ctx)
    result = {"account": account, "backends": {}}
    for name in ["graph_ig", "graph_fb", "private"]:
        result["backends"][name] = {"active": secrets.has_backend(account, name)}
    if ctx.obj["json"]:
        typer.echo(json.dumps(result, indent=2))
    else:
        for name, info in result["backends"].items():
            status = "Active" if info["active"] else "Not configured"
            typer.echo(f"  {name}: {status}")


@auth_app.command("logout")
def logout(
    ctx: typer.Context,
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clear stored sessions for the current account."""
    if not confirm:
        typer.confirm("Clear all stored sessions?", abort=True)
    account = ctx.obj["account"]
    secrets = _get_secrets(ctx)
    for name in ["graph_ig_token", "graph_fb_token", "private_session"]:
        secrets.delete(account, name)
    typer.echo(f"Cleared sessions for account: {account}")
```

**Step 5: Implement commands/config_cmd.py**

```python
from __future__ import annotations

import json

import typer

from clinstagram.config import ComplianceMode, load_config, save_config

config_app = typer.Typer(help="Manage configuration")


@config_app.command("show")
def show(ctx: typer.Context):
    """Print current configuration."""
    config = ctx.obj["config"]
    data = config.model_dump(mode="json")
    if ctx.obj["json"]:
        typer.echo(json.dumps(data, indent=2))
    else:
        for key, val in data.items():
            typer.echo(f"  {key}: {val}")


@config_app.command("mode")
def set_mode(ctx: typer.Context, mode: ComplianceMode = typer.Argument(...)):
    """Set compliance mode (official-only, hybrid-safe, private-enabled)."""
    config = ctx.obj["config"]
    config.compliance_mode = mode
    save_config(config, ctx.obj.get("config_dir"))
    typer.echo(f"Compliance mode set to: {mode.value}")


@config_app.command("set")
def set_value(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="Config key (dot notation)"),
    value: str = typer.Argument(..., help="New value"),
):
    """Set a configuration value."""
    config = ctx.obj["config"]
    # Handle flat top-level keys
    if hasattr(config, key):
        setattr(config, key, value)
        save_config(config, ctx.obj.get("config_dir"))
        typer.echo(f"Set {key} = {value}")
    else:
        typer.echo(f"Unknown config key: {key}", err=True)
        raise typer.Exit(code=1)
```

**Step 6: Create commands/__init__.py**

```python
```

**Step 7: Run all tests**

Run: `pytest tests/ -v`
Expected: All PASS

**Step 8: Verify CLI works end-to-end**

Run:
```bash
clinstagram --help
clinstagram --version
clinstagram auth --help
clinstagram config --help
```
Expected: All show proper help text.

**Step 9: Commit**

```bash
git add src/clinstagram/ tests/
git commit -m "feat: full CLI scaffold with auth, config commands, global flags, exit codes"
```

---

### Task 7: Config Persistence Integration Test

**Files:**
- Test: `tests/test_config_persistence.py`

**Step 1: Write integration test**

```python
from pathlib import Path
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
```

**Step 2: Run test**

Run: `pytest tests/test_config_persistence.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/test_config_persistence.py
git commit -m "test: config persistence integration tests"
```

---

### Task 8: End-to-End Smoke Test

**Files:**
- Test: `tests/test_e2e.py`

**Step 1: Write e2e test using Typer test runner**

```python
from typer.testing import CliRunner
from clinstagram.cli import app
import json

runner = CliRunner()

def test_full_workflow(tmp_path, monkeypatch):
    """Simulate: set config → check status → set mode → verify."""
    monkeypatch.setenv("CLINSTAGRAM_CONFIG_DIR", str(tmp_path))

    # Check initial config
    result = runner.invoke(app, ["config", "show", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["compliance_mode"] == "hybrid-safe"

    # Set mode
    result = runner.invoke(app, ["config", "mode", "official-only"])
    assert result.exit_code == 0

    # Verify persisted
    result = runner.invoke(app, ["config", "show", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["compliance_mode"] == "official-only"

    # Auth status (no backends configured)
    result = runner.invoke(app, ["auth", "status", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["backends"]["graph_ig"] is False
    assert data["backends"]["graph_fb"] is False
    assert data["backends"]["private"] is False

def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout

def test_placeholder_commands():
    """Future command groups show help, not crash."""
    for group in ["post", "dm", "story", "comments", "analytics", "followers", "user"]:
        result = runner.invoke(app, [group, "--help"])
        assert result.exit_code == 0
```

**Step 2: Run test**

Run: `pytest tests/test_e2e.py -v`
Expected: All PASS

**Step 3: Run full suite**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add tests/test_e2e.py
git commit -m "test: end-to-end smoke tests for CLI workflow"
```

---

### Task 9: Final Cleanup + SKILL.md Update

**Files:**
- Rewrite: `SKILL.md`

**Step 1: Update SKILL.md to match v2 design**

```yaml
---
name: clinstagram
description: >
  Full Instagram CLI — posting, DMs, stories, analytics, followers.
  Supports Meta Graph API (official, safe) and private API (full features).
  Three compliance modes: official-only, hybrid-safe, private-enabled.
env:
  - CLINSTAGRAM_CONFIG_DIR (optional, override config directory)
  - CLINSTAGRAM_SECRETS_FILE (optional, for headless/CI)
install:
  pip: clinstagram
bin:
  - clinstagram
tags:
  - social-media
  - instagram
  - automation
  - messaging
  - openclaw
---

# clinstagram

Hybrid Instagram CLI for OpenClaw. Routes between Meta Graph API and instagrapi private API based on policy.

## Quick Start

```bash
# Check status
clinstagram auth status --json

# Set compliance mode
clinstagram config mode official-only    # Graph API only, zero risk
clinstagram config mode hybrid-safe      # Graph primary, private read-only
clinstagram config mode private-enabled  # Full access, user accepts risk

# Connect official API
clinstagram auth connect-ig   # Instagram Login (posting, comments, analytics)
clinstagram auth connect-fb   # Facebook Login (adds DMs, webhooks, story publishing)

# Connect private API
clinstagram auth login         # Username/password/2FA via instagrapi
```

## Command Groups

- `clinstagram auth` — Login, connect, status, probe, logout
- `clinstagram post` — Post photos, videos, reels, carousels
- `clinstagram dm` — Read inbox, send messages, search, listen
- `clinstagram story` — View and post stories
- `clinstagram comments` — List, reply, delete comments
- `clinstagram analytics` — Profile, post, and hashtag insights
- `clinstagram followers` — List followers, follow/unfollow (requires --enable-growth-actions)
- `clinstagram user` — Search and view user profiles
- `clinstagram config` — Show/set configuration, compliance mode

## Agent Usage

All commands support `--json` for structured output. Exit codes:
- 0: Success
- 1: Bad arguments
- 2: Auth error (run `clinstagram auth login` or `clinstagram auth connect-*`)
- 3: Rate limited (check `retry_after` in JSON)
- 4: API error
- 5: Challenge required (check `challenge_type` in JSON)
- 6: Policy blocked (change compliance mode)
- 7: Capability unavailable (connect additional backend)

## Examples

```bash
# Check DMs
clinstagram dm inbox --unread --json

# Reply to a message
clinstagram dm send @alice "Thanks!" --json

# Post a photo
clinstagram post photo /path/to/img.jpg --caption "Hello world" --json

# Get analytics
clinstagram analytics post latest --json
```
```

**Step 2: Commit**

```bash
git add SKILL.md
git commit -m "docs: update SKILL.md to match v2 design with compliance modes"
```

---

## Summary

| Task | What it builds | Files | Tests |
|------|---------------|-------|-------|
| 1 | Clean scaffold + deps | pyproject.toml, __init__.py | install verify |
| 2 | Config + response models | config.py, models.py | test_config, test_models |
| 3 | SQLite state layer | db.py | test_db |
| 4 | Keychain secrets | auth/keychain.py | test_keychain |
| 5 | Capability matrix + router | backends/capabilities.py, router.py | test_capabilities, test_router |
| 6 | CLI app + commands | cli.py, commands/*.py | test_cli |
| 7 | Config persistence | — | test_config_persistence |
| 8 | E2E smoke tests | — | test_e2e |
| 9 | SKILL.md update | SKILL.md | — |

Total: 9 tasks, ~9 commits, full TDD.
