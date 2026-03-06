# clinstagram — Hybrid Instagram CLI for OpenClaw

**Date:** 2026-03-06
**Status:** v2 — Post-Review (Codex 5/10 → revised, Gemini 8.5/10 → incorporated)

---

## 1. Problem Statement

OpenClaw's existing Instagram skill (ClawHub) uses only the Meta Graph API, which provides posting, insights, comments, and hashtag research — but **no DMs, no stories, no follower management, and no personal account support**. Meanwhile, `instagrapi` covers the full private API surface (DMs, stories, followers, reels) but isn't packaged as a CLI that OpenClaw agents can invoke.

Browser automation via Playwright is unreliable for Instagram (bot detection, DOM fragility, ban risk, slow). The community consensus ([@anitakirkovska](https://x.com/i/status/2020167439066038627), [@blakeurmos](https://x.com)) is clear: **CLI > browser for agent workflows**.

**Goal:** Build `clinstagram`, a single Python CLI that merges both backends into one tool — safe official API where possible, private API where needed — designed as an OpenClaw skill from day one.

---

## 2. Research Summary

### 2.1 Landscape

| Tool/Service | Type | DMs | Stories | Posting | Analytics | Personal Accts | Risk |
|---|---|---|---|---|---|---|---|
| OpenClaw Instagram skill | Graph API | No | No | Yes | Yes | No | None |
| instagrapi v2.3.0 | Private API | Yes (20+ methods) | Yes | Yes | Basic | Yes | High |
| instagram-cli (supreme-gg-gg) | TUI app | Yes (read) | Beta | No | No | Yes | High |
| Instagram Messaging API | Graph API | Yes (200/hr, reply-only) | No | No | No | No (Biz/Creator) | None |
| Playwright browser-use | Browser | Yes | Yes | Yes | No | Yes | Very High |

### 2.2 Key Insight: Graph API DMs Are Reply-Only

Meta's Instagram Messaging API supports DMs for Business/Creator accounts at 200 messages/hour — but **only within a 24-hour window after the user messages you first**. You cannot cold-DM via the official API. This means:
- **Inbox reading + replying** → Graph API (safe)
- **Cold outreach + media DMs** → Private API only (risky)

### 2.3 Key Insight: Two Graph API Auth Modes

Meta offers **two distinct Graph API login paths** with different prereqs:
- **Instagram Login** — No Facebook Page required. Simpler OAuth. Supports content publishing, comments, insights.
- **Facebook Login** — Requires linked Facebook Page. Supports Messaging API (DMs), webhooks, additional permissions.

The router must know which auth mode is active to determine available features.

### 2.4 Prior Art

- **[@brandon_ai](https://x.com/i/status/2029555059273695406):** Open-sourced a CLI giving AI agents full control of Instantly.ai — 156 commands, 31 API groups. Validates the "agent-native CLI" pattern.
- **[@yuhasbeentaken](https://x.com/i/status/2029027396998025487):** Built CLI Lark wrapper for OpenClaw — 80k LOC via vibe-coded agent, now self-maintaining. Confirms CLI-first is the OpenClaw way.
- **[@postclaw_](https://x.com/i/status/1969122847118540968):** OpenClaw agent posting to X, Threads, LinkedIn, Instagram, Facebook, TikTok — uses API-first approach, not browser.
- **instagrapi MCP server** exists for DMs (basic send/receive) but is not a full CLI and lacks Graph API fallback.

---

## 3. Architecture

### 3.1 Design Principles

1. **Policy-driven routing, not exception-driven** — Each command maps to a capability matrix. The router checks what's *available and allowed*, never blindly falls back on error.
2. **Three compliance modes** — `official-only` (Graph API only, zero ban risk), `hybrid-safe` (Graph primary, private for read-only extras), `private-enabled` (full access, user accepts risk).
3. **CLI-native for agents** — Structured subcommands with `--json` output. No interactive prompts in non-interactive mode.
4. **Triple auth model** — `graph_instagram_login`, `graph_facebook_login`, `private`. Capabilities derived at auth time.
5. **Rate-limit aware** — Built-in backoff and respect for both Graph API (200 DM/hr) and private API limits.
6. **Proxy-first for private API** — SOCKS5/HTTP proxy support is mandatory, not optional.
7. **Secrets in OS keychain** — No plaintext tokens in config files.

### 3.2 Backend Routing Logic

```
Command received (e.g., "dm send @alice hello")
    │
    ├─ 1. Look up command in CAPABILITY_MATRIX
    │      → dm.send requires: messaging permission, recipient must have messaged first (Graph)
    │                          OR private session (Private)
    │
    ├─ 2. Check compliance mode
    │      ├─ official-only → Only consider Graph backends
    │      ├─ hybrid-safe → Graph primary, private for read-only commands only
    │      └─ private-enabled → All backends available
    │
    ├─ 3. Check available auth sessions
    │      ├─ graph_facebook_login → Has Messaging API access? Recipient eligible?
    │      ├─ graph_instagram_login → No DM support (lacks Messaging API)
    │      └─ private → Session valid? Proxy configured?
    │
    ├─ 4. Route to best available backend per policy
    │
    └─ 5. If no backend available → structured error with reason + remediation
           Exit code 2 (auth), 6 (policy), or 7 (capability)
```

### 3.3 Feature × Backend Matrix

| Feature | Graph (IG Login) | Graph (FB Login) | Private API | Notes |
|---|---|---|---|---|
| **Auth** | OAuth | OAuth + Page | Username/pass/2FA | |
| **Post photo/video/reel** | Yes | Yes | Yes | Graph requires public URL or uploaded asset |
| **Post carousel** | Yes | Yes | Yes | |
| **DM - reply (24hr window)** | No | Yes (200/hr) | Yes | FB Login required for Graph DMs |
| **DM - cold send** | No | No | Yes | Private only — high risk |
| **DM - send photo/video** | No | Yes (via Send API) | Yes | |
| **DM - read inbox** | No | Yes | Yes | |
| **DM - search/delete/mute** | No | No | Yes | Private only |
| **Stories - post** | No | Yes (Business) | Yes | Graph added story publishing |
| **Stories - view others** | No | No | Yes | Private only |
| **Comments - list/reply/delete** | Yes | Yes | Yes | Graph primary |
| **Analytics - profile/post** | Yes | Yes | Basic | Graph primary |
| **Analytics - hashtag** | Yes | Yes | Yes | |
| **Followers - list** | No | No | Yes | Private only |
| **Follow/unfollow** | No | No | Yes | Private only, **disabled by default** |
| **User - search/info** | Limited | Limited | Yes | |

---

## 4. CLI Command Structure

```
clinstagram
├── auth
│   ├── login                  # Private API: username/password/2FA → session
│   ├── connect-ig             # Graph API via Instagram Login (no Page needed)
│   ├── connect-fb             # Graph API via Facebook Login (requires Page, enables DMs)
│   ├── status                 # Show backends, capabilities, compliance mode
│   ├── probe                  # Test all backends, report available features
│   └── logout                 # Clear stored sessions (with confirmation)
│
├── post
│   ├── photo <path|url>       # --caption --location --tags (auto-stages URLs for Graph)
│   ├── video <path|url>       # --caption --thumbnail --location
│   ├── reel <path|url>        # --caption --thumbnail --audio
│   └── carousel <paths|urls>  # --caption
│
├── dm
│   ├── inbox                  # List threads (--unread --limit)
│   ├── pending                # List pending message requests
│   ├── thread <thread_id|@user>  # Read messages (--limit)
│   ├── send <@user> <message> # Send text DM (policy-routed)
│   ├── send-media <@user> <path|url>  # Send photo/video DM
│   ├── search <query>         # Search threads (private only)
│   ├── share-post <@user> <media_id>  # Share a post via DM
│   ├── delete <thread_id> <msg_id>
│   ├── mute <thread_id>
│   ├── unmute <thread_id>
│   └── listen                 # Long-poll for new messages (Graph webhook or private poll)
│
├── story
│   ├── list [user]            # View stories
│   ├── post-photo <path|url>  # --mention --link --location
│   ├── post-video <path|url>  # --mention --link
│   └── viewers <story_id>     # List story viewers
│
├── comments
│   ├── list <media_id>        # --limit
│   ├── reply <comment_id> <text>
│   └── delete <comment_id>
│
├── analytics
│   ├── profile                # Follower count, reach, impressions
│   ├── post <media_id|latest> # Likes, comments, shares, saves, reach
│   └── hashtag <tag>          # Volume, related tags, top posts
│
├── followers
│   ├── list                   # --limit --cursor
│   ├── following              # List accounts you follow
│   ├── follow <@user>         # DISABLED by default (requires --enable-growth-actions)
│   └── unfollow <@user>       # DISABLED by default
│
├── user
│   ├── info <@username>
│   └── search <query>
│
└── config
    ├── show                   # Print current config
    ├── set <key> <value>      # e.g., compliance_mode=hybrid-safe
    └── mode <official-only|hybrid-safe|private-enabled>
```

### 4.1 Global Flags

| Flag | Description |
|---|---|
| `--json` | Output as JSON (default for piped/non-TTY) |
| `--account <name>` | Switch between multiple stored accounts |
| `--backend graph-ig\|graph-fb\|private\|auto` | Force specific backend (default: auto) |
| `--proxy <url>` | SOCKS5/HTTP proxy for private API calls |
| `--dry-run` | Show what would happen without executing |
| `--verbose` | Debug logging |
| `--no-color` | Disable color output |
| `--enable-growth-actions` | Unlock follow/unfollow commands |

### 4.2 Exit Codes

| Code | Meaning | Agent Action |
|---|---|---|
| 0 | Success | Parse JSON output |
| 1 | User error (bad args) | Fix command |
| 2 | Auth error (expired/invalid) | Run `auth login` or `auth connect-*` |
| 3 | Rate limited | Retry after `retry_after` seconds in JSON |
| 4 | API error (Instagram side) | Retry or report |
| 5 | Challenge required | JSON contains `challenge_type` + `challenge_url` — prompt user |
| 6 | Policy blocked | Command not allowed in current compliance mode |
| 7 | Capability unavailable | Backend doesn't support this feature — suggest auth upgrade |

### 4.3 Output Format

```bash
# Human mode
$ clinstagram dm inbox --limit 3
THREAD_ID   USER         LAST_MSG                  TIME          UNREAD
839201      @alice       "hey, check this out"     2 hours ago   ●
738291      @bob         "sounds good"             5 hours ago
612039      @charlie     photo                     1 day ago

# Agent mode (auto-detected when piped or --json)
$ clinstagram dm inbox --limit 3 --json
[
  {"thread_id": "839201", "username": "alice", "last_message": "hey, check this out",
   "timestamp": "2026-03-06T10:00:00Z", "unread": true, "backend_used": "graph_fb"},
  ...
]
```

---

## 5. Authentication & Session Management

### 5.1 Config Directory

```
~/.clinstagram/
├── config.toml              # Global settings (compliance mode, default account, proxy)
├── clinstagram.db           # SQLite WAL — rate limits, capability cache, audit log
├── accounts/
│   ├── <account_name>/
│   │   ├── capabilities.json    # Probed feature availability (cached)
│   │   └── settings.toml       # Per-account overrides (proxy, limits)
│   └── default -> <account_name>/
└── logs/
    └── audit.log               # All API calls logged for debugging
```

**Secrets** (tokens, sessions) stored in OS keychain via `keyring` library:
- `clinstagram/<account>/graph_ig_token`
- `clinstagram/<account>/graph_fb_token`
- `clinstagram/<account>/private_session` (serialized instagrapi session)

Fallback for headless/CI: `CLINSTAGRAM_SECRETS_FILE=~/.clinstagram/.secrets` (0600 permissions, gitignored).

### 5.2 Auth Flows

**Instagram Login (`clinstagram auth connect-ig`):**
1. Prompt for Meta App ID (or use built-in dev app for quick start)
2. Open OAuth URL → user grants permissions (content publishing, comments, insights)
3. Exchange code for long-lived token (60-day)
4. Probe capabilities → cache in `capabilities.json`
5. Store token in keychain

**Facebook Login (`clinstagram auth connect-fb`):**
1. Prompt for Meta App ID + confirm linked Facebook Page
2. Open OAuth URL → user grants extended permissions (messaging, webhooks)
3. Exchange code for long-lived token + Page access token
4. Probe capabilities (including Messaging API) → cache
5. Store tokens in keychain

**Private API (`clinstagram auth login`):**
1. Prompt for username + password
2. Handle 2FA (TOTP or SMS)
3. Handle challenge → if non-interactive, exit code 5 with structured JSON
4. Save session via instagrapi `dump_settings()` → keychain
5. Probe capabilities → cache
6. **Require proxy configuration** if running on non-residential IP

### 5.3 Capability Probing

`clinstagram auth probe` tests each backend and reports:

```json
{
  "account": "mybusiness",
  "backends": {
    "graph_instagram_login": {
      "active": true,
      "features": ["post_photo", "post_video", "post_reel", "comments", "analytics"]
    },
    "graph_facebook_login": {
      "active": true,
      "features": ["post_photo", "post_video", "dm_inbox", "dm_reply", "dm_send_media", "story_post", "comments", "analytics", "webhooks"]
    },
    "private": {
      "active": true,
      "proxy": "socks5://...",
      "features": ["all"]
    }
  },
  "compliance_mode": "hybrid-safe"
}
```

---

## 6. Media Staging Layer

**Problem (from Codex review):** Graph API requires public URLs for media publishing, not local file paths. `post photo /tmp/cat.jpg` must work seamlessly regardless of backend.

**Solution:** Built-in media staging:

1. **Local path detected** → If Graph backend selected:
   - Upload to a temporary public URL (options: Imgur API free tier, Cloudflare R2 presigned URL, or user-configured S3 bucket)
   - Pass URL to Graph API
   - Clean up after publish confirmation
2. **Remote URL detected** → If Private backend selected:
   - Download to temp file via `httpx`
   - Pass local path to instagrapi
3. **Configurable staging provider:**
   ```toml
   [media_staging]
   provider = "r2"  # or "imgur", "s3", "local-only"
   r2_bucket = "clinstagram-staging"
   r2_account_id = "..."
   cleanup_after_publish = true
   ```

This keeps the CLI interface consistent (`<path|url>`) regardless of which backend handles it.

---

## 7. Risk Mitigation

### 7.1 Compliance Modes

| Mode | Private API | Growth Actions | Risk |
|---|---|---|---|
| `official-only` | Disabled entirely | N/A | Zero |
| `hybrid-safe` | Read-only (inbox, user info, story viewing) | Disabled | Low |
| `private-enabled` | Full access | Requires `--enable-growth-actions` | High |

Default: `hybrid-safe`. Set via `clinstagram config mode <mode>`.

### 7.2 Ban Prevention (Private API)

| Strategy | Implementation |
|---|---|
| **Mandatory proxy** | Refuse private API calls without proxy configured (unless `--allow-direct`) |
| **Human-like sequencing** | Not just random delays — model realistic action sequences (open inbox → read → delay → reply) |
| **Session reuse** | Never re-login when session is valid |
| **Device fingerprint** | Persist and reuse device_id, user_agent, etc. |
| **Action budgets** | Configurable daily/hourly caps with SQLite tracking |
| **Warm-up mode** | New sessions start with low limits, auto-increase over days |
| **Challenge handling** | Auto-handle email/SMS challenges; exit code 5 + JSON for unknown types |
| **Growth actions disabled** | `follow`/`unfollow` require explicit `--enable-growth-actions` flag |
| **Kill switch** | `clinstagram config set private_api_enabled false` — instant disable |

### 7.3 Rate Limiting

```toml
[rate_limits]
graph_dm_per_hour = 200
private_dm_per_hour = 30         # Conservative — Instagram flags >50
private_follows_per_day = 20     # Much lower than Instagram's "soft limit"
private_likes_per_hour = 20
request_delay_min = 2.0
request_delay_max = 5.0
request_jitter = true            # Gaussian distribution, not uniform
```

Tracked in SQLite with sliding window counters, not flat JSON.

### 7.4 Graceful Degradation

If a private API session is invalidated mid-operation:
1. Attempt session refresh
2. If refresh fails → exit code 2 with `{"error": "session_expired", "remediation": "Run: clinstagram auth login"}`
3. Never attempt to create a new session silently

---

## 8. State & Daemon Layer

### 8.1 SQLite Database (`clinstagram.db`)

```sql
-- Rate limit tracking
CREATE TABLE rate_limits (
    account TEXT, backend TEXT, action TEXT,
    window_start DATETIME, count INTEGER,
    PRIMARY KEY (account, backend, action, window_start)
);

-- Capability cache
CREATE TABLE capabilities (
    account TEXT, backend TEXT, feature TEXT,
    available BOOLEAN, last_probed DATETIME,
    PRIMARY KEY (account, backend, feature)
);

-- Audit log
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    account TEXT, backend TEXT, command TEXT,
    args TEXT, exit_code INTEGER, response_summary TEXT
);

-- Username ↔ ID cache
CREATE TABLE user_cache (
    username TEXT PRIMARY KEY,
    user_id TEXT, graph_scoped_id TEXT, private_pk TEXT,
    last_updated DATETIME
);

-- Thread ID mapping (Graph ↔ Private)
CREATE TABLE thread_map (
    username TEXT PRIMARY KEY,
    graph_thread_id TEXT, private_thread_id TEXT,
    last_updated DATETIME
);
```

### 8.2 `dm listen` — Long-Poll / Webhook Mode

For agents that need real-time DM monitoring:

- **Graph (FB Login):** Register webhook subscription → `clinstagram dm listen` starts a lightweight HTTP server on `localhost:PORT` to receive webhook POSTs, outputs each new message as a JSON line to stdout.
- **Private API:** Polling loop with configurable interval (default 30s), outputs new messages as JSON lines.
- Both modes support `--timeout` and `--max-messages` for bounded execution.

### 8.3 Future: `clinstagramd` Daemon (Post-MVP)

For advanced use cases (scheduling, webhook persistence, OAuth callback server):
- Lightweight background service
- Manages token refresh, scheduled posts, webhook receiver
- Communicates with CLI via Unix socket
- **Not in MVP** — marked as post-v1.0 enhancement

---

## 9. OpenClaw Skill Integration

### 9.1 SKILL.md

```yaml
---
name: clinstagram
description: >
  Full Instagram CLI — posting, DMs, stories, analytics, followers.
  Supports Meta Graph API (official, safe) and private API (full features).
  Three compliance modes: official-only, hybrid-safe, private-enabled.
env:
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
```

The SKILL.md body contains natural language descriptions of each command group with example invocations, compliance mode explanations, and common agent workflows.

### 9.2 Agent Ergonomics

- All commands return structured JSON with `--json` (auto-detected for piped output)
- Expanded exit codes (0-7) with machine-readable error types
- Every JSON error includes `remediation` field with exact command to fix
- Username resolution: `@alice` auto-resolves to appropriate ID per backend
- Thread resolution: `@username` auto-maps to correct thread ID per backend (via `thread_map` cache)
- `backend_used` field in every JSON response — agent knows which path was taken
- `dm listen` outputs JSONL for streaming consumption

---

## 10. Tech Stack

| Component | Choice | Rationale |
|---|---|---|
| Language | Python 3.10+ | instagrapi is Python; no cross-language bridge needed |
| CLI framework | `typer` | Automatic help, type validation, shell completion |
| HTTP client | `httpx` | Async-capable, modern, for Graph API + media staging |
| Private API | `instagrapi` 2.3.x | Battle-tested, 20+ DM methods, session persistence |
| Config | `tomli` / `tomli-w` | TOML for human-readable config |
| Validation | `pydantic` | Config validation, structured outputs, response models |
| Output | `rich` | Tables, JSON, progress bars for terminal |
| State | `sqlite3` (WAL mode) | Rate limits, capability cache, audit log, thread mapping |
| Secrets | `keyring` | OS keychain (macOS Keychain, GNOME Keyring, Windows Credential Locker) |
| Testing | `pytest` | Unit + integration tests from Phase 1 |
| Packaging | `pyproject.toml` + `hatch` | Modern Python packaging, ClawHub + PyPI |

---

## 11. Project Structure

```
clinstagram/
├── pyproject.toml
├── README.md
├── SKILL.md
├── src/
│   └── clinstagram/
│       ├── __init__.py
│       ├── cli.py              # Typer app, global flags, command groups
│       ├── config.py           # TOML config + Pydantic validation
│       ├── db.py               # SQLite setup, rate limits, caches
│       ├── models.py           # Pydantic response models (unified across backends)
│       ├── media.py            # Media staging (local↔URL, upload/download)
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── graph_ig.py     # Instagram Login OAuth
│       │   ├── graph_fb.py     # Facebook Login OAuth
│       │   ├── private.py      # instagrapi login/session
│       │   └── keychain.py     # OS keychain abstraction
│       ├── backends/
│       │   ├── __init__.py
│       │   ├── base.py         # Abstract backend interface
│       │   ├── graph.py        # Graph API client (both login modes)
│       │   ├── private.py      # instagrapi wrapper
│       │   ├── router.py       # Policy + capability-driven routing
│       │   └── capabilities.py # CAPABILITY_MATRIX + probing
│       └── commands/
│           ├── __init__.py
│           ├── auth.py
│           ├── post.py
│           ├── dm.py
│           ├── story.py
│           ├── comments.py
│           ├── analytics.py
│           ├── followers.py
│           ├── user.py
│           └── config_cmd.py
├── tests/
│   ├── conftest.py             # Fixtures, mock backends
│   ├── test_auth.py
│   ├── test_router.py
│   ├── test_capabilities.py
│   ├── test_dm.py
│   ├── test_media_staging.py
│   └── test_models.py
└── scripts/
    └── setup_graph_api.sh
```

---

## 12. Implementation Phases (Revised)

### Phase 1: Foundation + Tests (Week 1)
- Project scaffold (pyproject.toml, typer app, src layout)
- Config system with Pydantic validation
- SQLite database setup (rate limits, capability cache, audit log)
- OS keychain integration via `keyring`
- Auth commands: `login`, `connect-ig`, `connect-fb`, `status`, `probe`
- Capability probing + caching
- **Test infrastructure from day one** — mock backends, fixtures
- `--json` output + exit code contract

### Phase 2: Posting + Media Staging (Week 2)
- Media staging layer (local→URL for Graph, URL→local for private)
- `post photo`, `post video`, `post reel`, `post carousel`
- Graph backend (both login modes)
- Private backend
- Policy-driven router with compliance modes
- Tests for each backend + router

### Phase 3: Direct Messages (Week 2-3)
- `dm inbox`, `dm thread`, `dm send`, `dm pending`
- Graph Messaging API backend (FB Login only, reply-within-24hr)
- Private API backend for cold DMs + media DMs
- Thread ID mapping (Graph ↔ Private via `thread_map`)
- Username → thread resolution
- `dm listen` (polling mode for private, webhook prep for Graph)
- Challenge handling (exit code 5 + structured JSON)
- Tests

### Phase 4: Stories & Comments (Week 3)
- `story list`, `story post-photo`, `story post-video`, `story viewers`
- `comments list`, `comments reply`, `comments delete`
- Graph API for comments + story publishing (FB Login)
- Private API for story viewing + personal account stories
- Tests

### Phase 5: Analytics & User (Week 4)
- `analytics profile`, `analytics post`, `analytics hashtag`
- `user info`, `user search`
- Graph primary for analytics, private for extended user data
- Tests

### Phase 6: Followers + OpenClaw Packaging (Week 4)
- `followers list`, `followers following`
- `follow`/`unfollow` (disabled by default, `--enable-growth-actions`)
- SKILL.md with full documentation
- ClawHub submission prep
- PyPI release
- README with standalone + OpenClaw usage examples
- Integration tests against mock Graph API + mock instagrapi

### Post-MVP
- `clinstagramd` daemon (webhook server, scheduler, token refresh)
- HikerAPI SaaS backend option
- StoryBuild advanced story creation
- Multi-account management polish

---

## 13. What This Enables for OpenClaw

```
Agent: "Check your Instagram DMs for unread messages"
→ clinstagram dm inbox --unread --json
→ Routes via Graph FB Login (official, safe) if available

Agent: "Reply to @alice's last message"
→ clinstagram dm send @alice "Thanks!" --json
→ Graph Messaging API (within 24hr window) or private fallback

Agent: "Post this photo to your story with a mention of @bob"
→ clinstagram story post-photo /tmp/photo.jpg --mention @bob --json
→ Graph (FB Login, Business) or private API

Agent: "How did my last post perform?"
→ clinstagram analytics post latest --json
→ Always Graph API (official)

Agent: "Monitor DMs and notify me of new messages"
→ clinstagram dm listen --timeout 3600 --json
→ JSONL stream, one line per new message
```

---

## 14. Resolved Open Questions

1. **HikerAPI** → Post-MVP. Start with self-hosted instagrapi + proxy for ban mitigation.
2. **Webhook support** → `dm listen` in Phase 3 (polling first, webhook in daemon post-MVP).
3. **Multi-account** → Config supports it from Phase 1, but full UX polish in Phase 6.
4. **Story builder** → Post-MVP. Too complex for CLI; basic story posting first.
5. **Thread ID mapping** → SQLite `thread_map` table resolves Graph↔Private ID divergence.
6. **Media staging** → Built-in with configurable providers (Phase 2).
7. **Proxy support** → Mandatory for private API from Phase 1.

---

## 15. Review Feedback Incorporated

### From Codex (GPT-5.4) — Original: 5/10
- [x] Split Graph API into `graph_ig` and `graph_fb` with distinct capabilities
- [x] Policy-driven routing with compliance modes instead of exception-based fallback
- [x] Media staging layer for Graph API's URL requirement
- [x] SQLite for state instead of JSON files
- [x] OS keychain for secrets
- [x] Growth actions disabled by default
- [x] Tests from Phase 1, not Phase 6
- [x] DM Send API reply-only constraint documented
- [x] Daemon deferred to post-MVP (acknowledged need, scoped correctly)

### From Gemini — Original: 8.5/10
- [x] Feature-aware routing via CAPABILITY_MATRIX
- [x] Mandatory proxy support (`--proxy` global flag + config)
- [x] `dm listen` command for reactive agents
- [x] Thread ID mapping cache (SQLite `thread_map`)
- [x] Challenge handling with exit code 5 + structured JSON
- [x] Pydantic for config validation + response models
- [x] URL support in media commands (auto-download for private backend)
- [x] Rate limit jitter (Gaussian distribution)

---

## Sources

- [instagrapi GitHub](https://github.com/subzeroid/instagrapi)
- [instagrapi DM docs](https://subzeroid.github.io/instagrapi/usage-guide/direct.html)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [OpenClaw skills registry](https://github.com/openclaw/skills)
- [instagram-cli (supreme-gg-gg)](https://github.com/supreme-gg-gg/instagram-cli)
- [Instagram Graph API 2026 Guide](https://elfsight.com/blog/instagram-graph-api-complete-developer-guide-for-2026/)
- [Instagram DM API Guide](https://www.bot.space/blog/the-instagram-dm-api-your-ultimate-guide-to-automation-sales-and-customer-loyalty-svpt5)
- [Instagram API Rate Limits](https://creatorflow.so/blog/instagram-api-rate-limits-explained/)
- [Meta Instagram Login API](https://www.postman.com/meta/instagram/folder/6raa77c/instagram-api-with-instagram-login)
- [Meta Facebook Login API](https://www.postman.com/meta/instagram/folder/9cgqucg/instagram-api-with-facebook-login)
- [Meta Send API](https://www.postman.com/meta/instagram/folder/jb8vta5/send-api)
- [Meta Conversations API](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/conversations-api)
- [OpenClaw Instagram Skill](https://playbooks.com/skills/openclaw/skills/instagram)
- [VoltAgent Awesome OpenClaw Skills](https://github.com/VoltAgent/awesome-openclaw-skills)
