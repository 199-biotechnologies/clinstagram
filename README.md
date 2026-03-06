<p align="center">
  <img src="assets/logo.png" alt="clinstagram" width="128">
</p>

<h1 align="center">clinstagram</h1>

<p align="center">
  <strong>The Instagram CLI that AI agents actually use.</strong><br>
  Meta Graph API + instagrapi private API in one tool. Built for <a href="https://github.com/openclaw/openclaw">OpenClaw</a>.
</p>

<p align="center">
  <a href="#install">Install</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#commands">Commands</a> •
  <a href="#for-agents">For Agents</a> •
  <a href="#compliance-modes">Safety</a> •
  <a href="#architecture">Architecture</a>
</p>

---

## Why

Every Instagram automation tool makes you choose: **official API** (safe but limited) or **private API** (full-featured but risky). clinstagram gives you both behind one CLI, with policy-driven routing that picks the safest path automatically.

```bash
# This command automatically routes through the official Graph API
# if you have a Business account, or falls back to private API if not
$ clinstagram --json dm inbox
[{"thread_id": "839201", "username": "alice", "last_message": "hey!", "unread": true, "backend_used": "graph_fb"}]
```

No browser automation. No Playwright. No bot detection. Just structured CLI commands with JSON output.

## Install

Requires **Python 3.10+**.

```bash
pip install clinstagram
```

Or install from source (recommended for development):

```bash
git clone https://github.com/199-biotechnologies/clinstagram.git
cd clinstagram
pip install -e ".[dev]"
```

Verify it works:

```bash
clinstagram --version
# clinstagram 0.1.0
```

## Quick Start

```bash
# 1. Login (username, email, or phone — locale auto-detected from your system)
clinstagram auth login -u your_username

# 2. Check what's configured
clinstagram auth status

# 3. Use it
clinstagram --json dm inbox
clinstagram --json analytics profile
clinstagram --json post photo cat.jpg --caption "via clinstagram"
```

> **Important:** `--json`, `--proxy`, and `--account` are **global flags** — they go **before** the command:
> ```bash
> clinstagram --json dm inbox          # correct
> clinstagram dm inbox --json          # WRONG — will error
> ```

## Commands

### Auth
```bash
clinstagram auth status          # Show which backends are active
clinstagram auth connect-ig      # OAuth via Instagram Login
clinstagram auth connect-fb      # OAuth via Facebook Login (enables DMs)
clinstagram auth login -u user   # Private API (username, email, or phone)
clinstagram auth probe           # Test all backends, report capabilities
clinstagram auth logout --yes    # Clear all stored sessions
```

### Post
```bash
clinstagram --json post photo <path|url> --caption "..." --tags "@user"
clinstagram --json post video <path|url> --caption "..."
clinstagram --json post reel <path|url> --caption "..."
clinstagram --json post carousel img1.jpg img2.jpg --caption "..."
```

### Direct Messages
```bash
clinstagram --json dm inbox --unread --limit 10
clinstagram --json dm thread @alice --limit 20
clinstagram --json dm send @alice "Thanks for reaching out!"
clinstagram --json dm send-media @alice photo.jpg
clinstagram --json dm search "project"
```

### Stories
```bash
clinstagram --json story list
clinstagram --json story list @alice
clinstagram --json story post-photo photo.jpg --mention @alice
clinstagram --json story post-video clip.mp4 --link "https://..."
clinstagram --json story viewers <story_id>
```

### Comments
```bash
clinstagram --json comments list <media_id> --limit 50
clinstagram --json comments reply <comment_id> "Great point!"
clinstagram --json comments delete <comment_id>
```

### Analytics
```bash
clinstagram --json analytics profile
clinstagram --json analytics post <media_id>
clinstagram --json analytics hashtag "photography"
```

### Followers
```bash
clinstagram --json followers list --limit 100
clinstagram --json followers following
clinstagram --json --enable-growth-actions followers follow @user    # Disabled by default
clinstagram --json --enable-growth-actions followers unfollow @user
```

### User
```bash
clinstagram --json user info @username
clinstagram --json user search "john doe"
```

### Config
```bash
clinstagram --json config show
clinstagram config mode official-only     # Zero risk
clinstagram config mode hybrid-safe       # Official + private read-only (default)
clinstagram config mode private-enabled   # Full access
clinstagram config set proxy socks5://localhost:1080
```

## Global Flags

Global flags go **before** the command name.

| Flag | Description |
|------|-------------|
| `--json` | JSON output (auto-enabled when piped) |
| `--account <name>` | Switch between stored accounts |
| `--backend auto\|graph_ig\|graph_fb\|private` | Force a specific backend |
| `--proxy <url>` | SOCKS5/HTTP proxy for private API |
| `--dry-run` | Preview without executing |
| `--enable-growth-actions` | Unlock follow/unfollow |

## For Agents

clinstagram is designed to be called by AI agents like OpenClaw. Every command:

- Returns **structured JSON** with `--json` (auto-detected when piped)
- Includes `backend_used` field so agents know which path was taken
- Uses **exit codes** for machine-readable error handling:

| Exit Code | Meaning | Agent Action |
|-----------|---------|--------------|
| 0 | Success | Parse JSON |
| 1 | Bad arguments | Fix command |
| 2 | Auth error | Run `auth login` or `auth connect-*` |
| 3 | Rate limited | Retry after `retry_after` seconds |
| 4 | API error | Retry or report |
| 5 | Challenge required | Prompt user (2FA/email) |
| 6 | Policy blocked | Change compliance mode |
| 7 | Capability unavailable | Connect additional backend |

Every error includes a `remediation` field with the exact command to fix it:
```json
{"exit_code": 2, "error": "session_expired", "remediation": "Run: clinstagram auth login"}
```

### OpenClaw Skill

Drop clinstagram into your OpenClaw workspace:
```bash
pip install clinstagram
# Or paste the GitHub URL into your OpenClaw chat
```

The included `SKILL.md` tells OpenClaw what commands are available.

## Compliance Modes

clinstagram routes commands through three backends with **policy-driven safety**:

| Mode | Official API | Private API | Risk |
|------|-------------|-------------|------|
| `official-only` | Full | Disabled | Zero |
| `hybrid-safe` | Full | Read-only | Low |
| `private-enabled` | Full | Full | High |

**Default is `hybrid-safe`** — you get official API for everything it supports, plus private API for read-only operations like viewing stories or listing followers.

### Three Backends

| Backend | Auth | Best For |
|---------|------|----------|
| `graph_ig` | Instagram Login (OAuth) | Posting, comments, analytics. No Facebook Page needed. |
| `graph_fb` | Facebook Login (OAuth) | Everything above + DMs, webhooks, story publishing. Needs linked Page. |
| `private` | Username/password/2FA | Everything. Personal accounts. Cold DMs. Requires proxy. |

The router **always prefers official APIs**. Private API is only used when:
1. The feature isn't available via Graph API (e.g., cold DMs, story viewing)
2. Your compliance mode allows it
3. You have a valid private session

## Architecture

```
┌─────────────────────────────────────────────┐
│                  CLI Layer                    │
│   typer + rich (--json / human output)       │
├─────────────────────────────────────────────┤
│              Policy Router                   │
│   CAPABILITY_MATRIX × ComplianceMode         │
│   → picks best backend per command           │
├──────────┬──────────┬───────────────────────┤
│ graph_ig │ graph_fb │      private          │
│ (OAuth)  │ (OAuth)  │   (instagrapi)        │
│ Post     │ Post+DM  │   Everything          │
│ Comments │ Stories  │   + proxy support     │
│ Analytics│ Webhooks │   + session persist   │
├──────────┴──────────┴───────────────────────┤
│              Config Layer                    │
│   TOML config, rate limits, compliance       │
├─────────────────────────────────────────────┤
│              Secrets                         │
│   OS Keychain (macOS/Linux/Windows)          │
│   Fallback: encrypted file for CI            │
└─────────────────────────────────────────────┘
```

### Key Design Decisions

- **Policy-driven routing** — Commands are routed based on a capability matrix and compliance mode, not by catching errors and falling back.
- **Graph DMs are reply-only** — Meta's Messaging API only works within a 24-hour window after the user messages you. Cold DMs require private API.
- **Growth actions disabled by default** — `follow`/`unfollow` require `--enable-growth-actions` flag.
- **Mandatory proxy for private API** — Protects against IP-based detection on cloud VPS.
- **OS keychain for secrets** — No plaintext tokens on disk. Sessions persisted in keychain with device UUID preservation.

## Rate Limits

```toml
# ~/.clinstagram/config.toml
[rate_limits]
graph_dm_per_hour = 200       # Meta's hard limit
private_dm_per_hour = 30      # Conservative default
private_follows_per_day = 20  # Well below Instagram's threshold
request_delay_min = 2.0       # Seconds between private API calls
request_delay_max = 5.0
request_jitter = true         # Gaussian distribution, not uniform
```

## Development

```bash
git clone https://github.com/199-biotechnologies/clinstagram.git
cd clinstagram
pip install -e ".[dev]"
pytest tests/ -v   # 111 tests
```

## License

MIT

## Credits

- [instagrapi](https://github.com/subzeroid/instagrapi) — Instagram Private API wrapper
- [OpenClaw](https://github.com/openclaw/openclaw) — AI agent platform
- [Typer](https://typer.tiangolo.com/) — CLI framework
- Built by [199 Biotechnologies](https://github.com/199-biotechnologies)
