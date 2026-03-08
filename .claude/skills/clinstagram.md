---
name: clinstagram
description: Use when user asks to post on Instagram, check DMs, view stories, manage followers, get analytics, search users/hashtags, comment on posts, or any Instagram automation task. Also triggers on "clinstagram", "instagram cli", "ig post", "ig dm", "ig story".
---

# clinstagram — Hybrid Instagram CLI

Routes between Meta Graph API and instagrapi private API based on compliance policy. Installed via `pip install clinstagram`.

## Critical: Global Flags Before Subcommand

```bash
clinstagram --json --account main dm inbox     # CORRECT
clinstagram dm inbox --json                    # WRONG — Typer limitation
```

Global flags: `--json`, `--account NAME`, `--backend auto|graph_ig|graph_fb|private`, `--proxy URL`, `--dry-run`, `--enable-growth-actions`

## Commands

| Group | Commands | Notes |
|-------|----------|-------|
| `auth` | `status`, `login`, `connect-ig`, `connect-fb`, `probe`, `logout` | Always start with `auth status --json` |
| `post` | `photo`, `video`, `reel`, `carousel` | Accepts local paths or URLs |
| `dm` | `inbox`, `thread ID`, `send @user "text"`, `send-media`, `search` | Cold DMs = private API only |
| `story` | `list [@user]`, `post-photo`, `post-video`, `viewers ID` | |
| `comments` | `list MEDIA_ID`, `add`, `reply`, `delete` | add/reply need `--enable-growth-actions` |
| `analytics` | `profile`, `post ID\|latest`, `hashtag TAG` | |
| `followers` | `list`, `following`, `follow @user`, `unfollow @user` | follow/unfollow need `--enable-growth-actions` |
| `user` | `info @user`, `search QUERY`, `posts @user` | |
| `hashtag` | `top TAG`, `recent TAG` | |
| `like` | `post MEDIA_ID`, `undo MEDIA_ID` | Needs `--enable-growth-actions` |
| `config` | `show`, `mode MODE`, `set KEY VAL` | Modes: `official-only`, `hybrid-safe`, `private-enabled` |

## JSON Output Schema

Success:
```json
{"exit_code": 0, "data": {}, "backend_used": "graph_fb"}
```

Error:
```json
{"exit_code": 2, "error": "session_expired", "remediation": "Run: clinstagram auth login", "retry_after": null}
```

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Parse `data` |
| 1 | Bad arguments | Fix syntax |
| 2 | Auth error | Run `remediation` command |
| 3 | Rate limited | Wait `retry_after` seconds |
| 4 | API error | Retry |
| 5 | Challenge required | Check `challenge_type`, prompt user |
| 6 | Policy blocked | Change compliance mode |
| 7 | Capability unavailable | Connect another backend |

## Agent Workflow

```bash
# 1. Check what's available
clinstagram --json auth status

# 2. Probe capabilities
clinstagram --json auth probe

# 3. Preview before acting
clinstagram --dry-run --json dm inbox

# 4. Execute
clinstagram --json dm inbox --unread --limit 20

# 5. On error, read remediation field and execute it
```

## Growth Actions (Disabled by Default)

Follow, unfollow, like, unlike, comment add/reply all require `--enable-growth-actions` flag. This is a safety gate — always confirm with user before enabling.

## Backend Routing

| Feature | graph_ig | graph_fb | private |
|---------|:--------:|:--------:|:-------:|
| Post | Y | Y | Y |
| DM inbox | - | Y | Y |
| Cold DM | - | - | Y |
| Stories | - | Y | Y |
| Comments | Y | Y | Y |
| Analytics | Y | Y | Y |
| Follow/Unfollow | - | - | Y |
| Hashtag | Y | Y | Y |

Preference order: `graph_ig` > `graph_fb` > `private`. Override with `--backend`.

## Config

File: `~/.clinstagram/config.toml`. Override dir with `CLINSTAGRAM_CONFIG_DIR` env var.
