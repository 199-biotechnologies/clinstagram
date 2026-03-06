---
name: clinstagram
description: Hybrid Instagram CLI for OpenClaw. Routes between Meta Graph API and Private API (instagrapi).
env:
  - INSTAGRAM_ACCESS_TOKEN (optional, for Graph API)
install:
  pip: .
bin:
  - clinstagram
tags:
  - social-media
  - instagram
  - automation
  - messaging
---

# clinstagram

Full Instagram CLI — posting, DMs, stories, analytics, followers.

## Usage

```bash
# Auth
clinstagram auth login --username <user> --password <pass>
clinstagram auth status

# DMs
clinstagram dm inbox --json
clinstagram dm send @alice "Hello from OpenClaw" --json

# Posting
clinstagram post photo /path/to/img.jpg --caption "New post" --json
```

## Backend Routing
- **Graph API:** Used for Business/Creator accounts for posting and basic DMs.
- **Private API:** Fallback for personal accounts, stories, and media DMs.
- **Auto:** Automatically selects the safest and most capable backend.
