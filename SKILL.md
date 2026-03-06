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
