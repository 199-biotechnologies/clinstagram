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
{"exit_code":0,"data":[{"thread_id":"839201","thread_title":"alice","participants":[{"id":"1784","username":"alice","full_name":"Alice","profile_picture_url":null,"is_private":null,"is_verified":null,"biography":null,"followers_count":null,"following_count":null,"media_count":null}],"last_message":"hey!","last_message_at":"2026-03-12T12:00:00+0000","unread":true}],"backend_used":"graph_fb"}
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
# 1. Private login (username, email, or phone — locale auto-detected from your system)
clinstagram auth login -u your_username

# 2. Optional: import official Graph tokens if you have them already
clinstagram auth connect-ig --token <instagram-login-token>
clinstagram auth connect-fb --token <facebook-login-token>

# 3. Check what is configured
clinstagram --json auth status
clinstagram --json auth probe

# 4. Use read-only commands immediately
clinstagram --json dm inbox
clinstagram --json analytics profile

# 5. Enable private write actions only when you explicitly want them
clinstagram config mode private-enabled
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
clinstagram auth status          # Show which backends are configured
clinstagram auth connect-ig      # Store an Instagram Login access token
clinstagram auth connect-fb      # Store a Facebook Login access token (enables DMs)
clinstagram auth login -u user   # Private API (username, email, or phone)
clinstagram auth probe           # Live-check configured backends
clinstagram auth logout --yes    # Clear all stored sessions
```

### Post
```bash
clinstagram --json post photo <path|url> --caption "..." --tags "@user"
clinstagram --json post video <path|url> --caption "..."          # file thumbnails require private backend
clinstagram --json post reel <path|url> --caption "..."           # file thumbnails require private backend
clinstagram --json post carousel img1.jpg img2.jpg --caption "..."
```

### Direct Messages
```bash
clinstagram --json dm inbox --unread --limit 10
clinstagram --json dm thread @alice --limit 20
clinstagram --json dm send @alice "Thanks for reaching out!"      # cold DM via private backend
clinstagram --json dm send 123456789 "Thanks for reaching out!"   # reply via thread/recipient ID
clinstagram --json dm send-media @alice photo.jpg                 # prefers private for usernames/local files
clinstagram --json dm search "project"
```

### Stories
```bash
clinstagram --json story list
clinstagram --json story list @alice
clinstagram --json story post-photo photo.jpg --mention @alice
clinstagram --json story post-video clip.mp4 --link "https://..." # story links require private backend
clinstagram --json story viewers <story_id>
```

### Comments
```bash
clinstagram --json comments list <media_id> --limit 50
clinstagram --json comments reply <comment_ref> "Great point!"
clinstagram --json comments delete <comment_ref>
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
clinstagram --json user search "alice"              # username-style lookup on official route
clinstagram --json user posts @username --limit 10
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
- Uses the same success envelope for command groups like `auth`, `config`, and `logout`
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

`auth status` reports configured backends only. Use `auth probe` when you need a live validity check for tokens or sessions.

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
Forced backends via `--backend` are still checked against compliance policy.

### Three Backends

| Backend | Auth | Best For |
|---------|------|----------|
| `graph_ig` | Imported Instagram Login token | Posting, comments, analytics. No Facebook Page needed. |
| `graph_fb` | Imported Facebook Login token | Everything above + DMs, story publishing. Needs linked Page. |
| `private` | Username/password/2FA | Everything. Personal accounts. Cold DMs. Proxy strongly recommended. |

The router prefers official APIs unless you explicitly force or prefer another backend. Private API is only used when:
1. The feature isn't available via Graph API (e.g., cold DMs, story viewing)
2. Your compliance mode allows it
3. You have a valid private session

For local-file write commands on Graph backends, you must supply a public URL. Auto-routing only falls back to private for local files when your compliance mode allows private writes.

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
└─────────────────────────────────────────────┘
```

### Key Design Decisions

- **Policy-driven routing** — Commands are routed based on a capability matrix and compliance mode, and `--backend` overrides are still policy-checked.
- **Graph DMs are reply-oriented** — use a thread/recipient ID on official messaging routes. Cold DMs still require private API.
- **Growth actions disabled by default** — `follow`/`unfollow` require `--enable-growth-actions` flag.
- **Proxy strongly recommended for private API** — protects against IP-based detection on cloud VPS.
- **OS keychain for secrets** — No plaintext tokens on disk. Sessions persist in keychain with device UUID preservation.

## Rate Limits

```toml
# ~/.clinstagram/config.toml
[rate_limits]
graph_dm_per_hour = 200       # Meta's hard limit
private_dm_per_hour = 30      # Conservative default
private_follows_per_day = 20  # Well below Instagram's threshold
request_delay_min = 2.0       # Seconds between private API write calls
request_delay_max = 5.0       # Read-only ops use [0, delay_min] for speed
request_jitter = true         # Randomized within delay range
```

The delay range is enforced today. The hourly and daily values are advisory config targets and are not yet hard-blocking quotas.

## Development

```bash
git clone https://github.com/199-biotechnologies/clinstagram.git
cd clinstagram
pip install -e ".[dev]"
pytest tests/ -v   # 120 tests
```

## License

MIT

## Credits

- [instagrapi](https://github.com/subzeroid/instagrapi) — Instagram Private API wrapper
- [OpenClaw](https://github.com/openclaw/openclaw) — AI agent platform
- [Typer](https://typer.tiangolo.com/) — CLI framework
- Built by [199 Biotechnologies](https://github.com/199-biotechnologies)
