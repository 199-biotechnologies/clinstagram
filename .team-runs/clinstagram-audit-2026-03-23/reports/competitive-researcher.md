# Competitive & Ecosystem Research

- **Date**: 2026-03-23
- **Researcher**: Competitive Analysis Agent

---

## Competing Projects Analysis

### instagram-cli (supreme-gg-gg)

**Repository**: https://github.com/supreme-gg-gg/instagram-cli
**Stars**: 1.7k | **Commits**: 492 | **Contributors**: 23 | **Latest**: v1.4.5 (March 2026)

**Tech Stack**: TypeScript, React, Ink (terminal UI), Node.js v20+

**Key Architecture Differences from clinstagram**:

1. **MQTT for Real-Time Messaging**: Uses `instagram_mqtt` (v1.2.3) for push-based DMs — typing indicators, read receipts, presence, live comments. This is a **major gap** for clinstagram which uses REST polling only. MQTT uses Instagram's native MQTToT protocol (MQTT over Thrift), which is significantly lower risk than REST-based DM interactions because it mimics the real app's communication pattern.

2. **TUI (Terminal UI)**: Full interactive terminal interface via Ink + React rendering. Supports keyboard navigation, image rendering (ASCII, half-block, braille, Kitty, iTerm2, Sixel protocols), and mouse interaction. clinstagram is command-based (fire-and-forget), not interactive.

3. **Anti-Detection**: TypeScript client is "much less likely to trigger Instagram's anti-bot mechanisms" per their docs. Uses `instagram-private-api` (Node.js equivalent of instagrapi) with `patch-package` for custom patches to the underlying library.

4. **Multi-Platform Packaging**: npm (`@i7m/instagram-cli`), Homebrew, AUR, Snap. clinstagram is PyPI-only.

5. **Image Rendering**: Displays images/media directly in terminal with automatic protocol detection. clinstagram has no in-terminal media rendering.

6. **Python Legacy Client**: They maintain a separate Python client (`instagram` command) alongside the TypeScript one — suggesting the TypeScript rewrite was motivated by limitations of the Python approach.

**What They Lack That clinstagram Has**:
- No compliance policy system (official-only / hybrid-safe / private-enabled)
- No Graph API integration (purely private API)
- No agent-optimized JSON output
- No AI skill integration (SKILL.md / Claude Code / OpenClaw)
- No rate limit tracking or audit logging
- No multi-backend routing

### Other Competitors

| Project | Description | Status |
|---------|------------|--------|
| **InstaPy** (github.com/InstaPy/InstaPy) | Selenium-based bot for automated interactions | Legacy, Selenium approach heavily detected in 2026 |
| **instagrapi-rest** (subzeroid) | REST wrapper around instagrapi, 15+ language support | Active, but no CLI — library only |
| **instagram-post-fetcher** | Selenium scraper for post details | Niche, scraping only |
| **InstaScrape** | CLI for fetching Reel comments via session cookies | Very niche |
| **Tools-for-Instagram** (linkfy) | Automation scripts collection | Fragmented, no unified CLI |
| **subzerobo/instagram-cli** | Go-based Instagram CLI | Appears unmaintained |

**Key Insight**: The landscape is bifurcated — instagram-cli (supreme-gg-gg) is the only serious TUI competitor. Everything else is either a library (instagrapi), a bot framework (InstaPy), or a niche scraper. clinstagram occupies a unique position as an **agent-oriented CLI with compliance controls**.

---

## instagrapi Ecosystem Updates

### Latest Version: 2.2.1

**Release History** (most relevant):
- **2.2.1** (July 2025): CaptchaHandlerMixin, Livestream support (create/start/info/comments/viewers), StoryPoll, ClipsMetadata
- **2.1.3** (Nov 2024): SignUpMixin, Broadcast Type, `remove_bio_links`
- **2.1.1** (Mar 2024): BioLink type, Story rotation properties
- **2.0.3** (Feb 2024): Bug fixes

**clinstagram pins `>=2.3.0`** in pyproject.toml but the latest PyPI release is 2.2.1. This is a **version mismatch** — either clinstagram uses an unreleased version or the pin is aspirational/incorrect.

### Known Issues & Limitations

1. **Maintainer's Own Warning**: "instagrapi more suits for testing or research than a working business!" — accounts get banned at scale, proxy sourcing is hard.
2. **API Validation**: Last validated May 25, 2025 — 10 months ago. Instagram API changes may have introduced silent breakages.
3. **No MQTT Support**: instagrapi is REST-only for DMs. The `instagram_mqtt` library (Nerixyz) is a separate Node.js project and is no longer actively maintained (last: April 2024).
4. **Device Fingerprint Issues**: Default device (OnePlus 6T, Android 8.0, IG v364) is heavily flagged. clinstagram already addresses this with Pixel 7/Android 13 defaults.

### HikerAPI SaaS

- Recommended by instagrapi maintainers as production alternative
- Handles 4-5M daily requests with 24/7 support
- Affiliate program: 10-50% commission (min $500 payout in USDT)
- **Relevance to clinstagram**: Could be offered as a premium backend option for users who need scale without ban risk. Would require a new backend type (`hiker`) alongside `graph_ig`, `graph_fb`, and `private`.

---

## CLI Skill Installation Patterns

### Claude Code Integration

**Standard Convention**:
- Personal/global skills: `~/.claude/skills/<skill-name>/SKILL.md`
- Project-scoped skills: `.claude/skills/<skill-name>.md` (travels with repo)
- clinstagram already has BOTH: `SKILL.md` (OpenClaw) and `.claude/skills/clinstagram.md` (Claude Code)

**Auto-Installation Tools**:
- `npx agent-skills-cli add <repo>` — installs to all supported agents automatically
- `npx add-skill <repo>` — similar universal installer
- Claude Code native: `/plugin marketplace add` + `/plugin install`
- Individual install scripts: `codex-install.sh`, `gemini-install.sh`

**Multi-Agent Directory Convention**:
| Agent | Skills Directory |
|-------|-----------------|
| Claude Code | `~/.claude/skills/` |
| Cursor | `.cursor/skills/` |
| VS Code/Copilot | `.github/skills/` |
| Goose | `~/.config/goose/skills/` |
| OpenClaw | `~/.openclaw/skills/` |
| Gemini CLI | `~/.gemini/skills/` or via extensions |

**Recommendation for clinstagram**: Add a `clinstagram install-skill` command that:
1. Detects which AI agents are installed (check for `~/.claude/`, `~/.gemini/`, `.cursor/` etc.)
2. Copies the appropriate SKILL.md to each agent's skills directory
3. Supports `--agent claude|gemini|cursor|all` flag
4. Uses symlinks to avoid duplication and keep skills in sync with pip-installed version

### Gemini CLI Integration

**Extension System**: Gemini CLI has its own extension/skill system:
- Skills live in `~/.gemini/extensions/<name>/skills/` or `~/.gemini/skills/`
- Precedence: Workspace > User > Extension
- Skills use identical SKILL.md format to Claude Code
- A bridge project (`gemini-cli-skillz`) enables Claude-style skills in Gemini via MCP server
- Installation: `gemini extensions install <github-url>`

**Key Insight**: The SKILL.md format is becoming a **cross-agent standard**. clinstagram's existing SKILL.md is already compatible with Claude Code, OpenClaw, and (via bridge) Gemini CLI.

### Patterns from 199-biotechnologies Repos

**claude-deep-research-skill**:
- Installation: `git clone <repo> ~/.claude/skills/deep-research`
- Structure: `SKILL.md` + `reference/` + `templates/` + `scripts/`
- No CLI install command — manual git clone only

**claude-skill-seo-geo-optimizer**:
- Same pattern: git clone into `~/.claude/skills/`

**engram** (MCP server):
- Different pattern — MCP server, not a skill file
- Configured in Claude Code's MCP settings

**Pattern Summary**: The org uses manual git clone for skill installation. There's an opportunity for clinstagram to pioneer automated skill installation via `pip install` post-install hooks or a dedicated CLI command.

---

## Anti-Detection Best Practices (2026)

### Instagram's Current Detection Capabilities

Instagram's anti-automation system is a **multi-layered detection engine** analyzing:
1. Device fingerprints (canvas hash, WebGL renderer, fonts, screen resolution, timezone, language, hardware concurrency)
2. IP reputation and IP-to-account correlation
3. Behavioral patterns (action timing, session duration, engagement patterns)
4. Session metadata (mid-session IP changes, login patterns)

### Proxy Strategy

**Tier 1 (Recommended)**: 4G/5G mobile proxies
- Real carrier IPs trusted by Instagram (CGNAT = millions share same IP)
- Strict 1:1 mapping: one dedicated mobile IP per account
- Sticky sessions: maintain same IP for 1-4 hours, then natural rotation
- Cost: ~$28-34/account/month at scale

**Tier 2 (Acceptable)**: Residential proxies
- Increasingly flagged in 2026 as detection improves
- Only useful with antidetect browser profiles

**Tier 3 (Avoid)**: Datacenter proxies
- Almost universally blocked for Instagram in 2026

### Account Warming Protocol (14-Day Minimum)

| Days | Actions Allowed | Limits |
|------|----------------|--------|
| 1-3 | Browse only, complete profile, follow 3-5 | Zero engagement |
| 4-7 | Light likes (10-20/day), 45-90s delays | Max 8-12 min sessions |
| 8-10 | Start following (5-10/day), comments (4+ words) | No generic phrases |
| 11-14 | First posts/stories, following 10-15/day | Gradual increase |

Skipping warmup = 80%+ ban rate in first week.

### Safe Action Limits (Warmed Accounts)

| Action | Daily Max | Delay Between |
|--------|----------|---------------|
| Likes | 50-80 | 25-60 seconds |
| Follows | 20-30 | 45-90 seconds |
| Comments | 10-15 | 120-300 seconds |
| Posts | 1-3 | N/A |
| DMs | 200/hour (API limit) | Variable |

**Critical**: Vary daily totals by 20-30% — hitting max every day triggers pattern detection.

### Top 10 Ban Triggers

1. Identical captions across multiple accounts
2. Following same accounts from multiple profiles
3. Instant actions immediately after login
4. Missing profile photos or incomplete bios
5. Reused bio templates
6. Coordinated engagement on identical posts
7. Exceeding hourly burst rates (50 likes in 10 minutes)
8. Shared device fingerprints across accounts
9. Mid-session IP switching
10. DM automation on accounts less than 30 days old

### Recommendations for clinstagram

1. **Built-in rate limiter with jitter**: Already has rate limit tracking in SQLite, but should enforce limits automatically with randomized delays (not just log)
2. **Action warming mode**: New `clinstagram config warm-account` that enforces graduated limits for new accounts
3. **Session stability checks**: Warn if proxy IP changes mid-session
4. **Daily variance**: Automatically vary action counts by 20-30% to avoid pattern detection

---

## MQTT Protocol Analysis

### Why MQTT Matters

Instagram's native apps use **MQTToT** (MQTT over Thrift) — a modified MQTT 3 protocol — for all real-time messaging. REST-based DM interactions are an abnormal pattern that Instagram can detect.

### Architecture

Two components in Instagram's MQTT stack:
1. **RealtimeClient**: In-app communication (cookie auth). Handles typing indicators, presence, DMs, live comments via topic subscriptions.
2. **FbnsClient**: Push notifications (device auth). Credentials returned in CONNACK payload, registered at `/api/v1/push/register/`.

### Protocol Modifications from Standard MQTT

- CONNECT packet: replaces `clientId` with compressed Thrift payload containing credentials
- CONNACK packet: includes payload (non-standard) for auth tokens and config
- Authentication embedded in payload rather than plain text fields

### Available Libraries

| Library | Language | Status | Notes |
|---------|----------|--------|-------|
| `instagram_mqtt` (Nerixyz) | Node.js/TypeScript | **Maintenance only** (last: Apr 2024) | Used by instagram-cli |
| `instagram4j-realtime` | Java | Active | MQTToT client for Java |
| None | Python | **Does not exist** | Major gap |

### Impact on clinstagram

**There is no Python MQTT library for Instagram.** This is the single biggest technical gap. Options:

1. **Build a Python MQTToT client**: High effort, high reward. Would be the first Python implementation.
2. **Use Node.js subprocess**: Shell out to a small Node.js bridge that handles MQTT, communicate via IPC/stdin/stdout.
3. **Use websockets via instagrapi**: instagrapi has experimental websocket support for some realtime features, but it's not full MQTT.
4. **Accept the gap**: REST-based DMs work but carry higher detection risk.

**Recommendation**: Option 2 (Node.js bridge) is the pragmatic choice. Ship a small `@clinstagram/mqtt-bridge` npm package that clinstagram spawns as a subprocess. This gets MQTT support without rewriting the protocol in Python.

---

## Feature Gap Matrix

| Feature | clinstagram | instagram-cli (supreme-gg-gg) | instagrapi raw |
|---------|------------|-------------------------------|----------------|
| **DMs (send/receive)** | REST only | MQTT real-time | REST only |
| **Typing indicators** | No | Yes (MQTT) | No |
| **Read receipts** | No | Yes (MQTT) | No |
| **Presence/online status** | No | Yes (MQTT) | No |
| **Interactive TUI** | No (command-based) | Yes (Ink/React) | N/A (library) |
| **Image rendering in terminal** | No | Yes (multi-protocol) | N/A |
| **Graph API integration** | Yes (dual backend) | No | No |
| **Compliance modes** | Yes (3 modes) | No | N/A |
| **Agent/AI integration** | Yes (SKILL.md, JSON) | No | N/A |
| **Rate limit enforcement** | Tracking only | Unknown | Manual |
| **Multi-account** | Yes (--account) | Yes (config) | Manual |
| **Post/upload media** | Yes | No (view only) | Yes |
| **Stories** | Yes | Yes (view) | Yes |
| **Reels** | Yes | No | Yes |
| **Analytics/insights** | Yes | No | Yes |
| **Hashtag search** | Yes | No | Yes |
| **Livestream** | No | No | Yes (v2.2.1) |
| **Captcha handling** | No | No | Yes (v2.2.1) |
| **Homebrew/npm install** | No (pip only) | Yes (npm, brew, AUR, snap) | pip |
| **Audit logging** | Yes (SQLite) | Logs dir | No |
| **Proxy support** | Yes (--proxy) | Unknown | Yes |
| **2FA support** | Yes | Yes | Yes |
| **OS keychain secrets** | Yes (keyring) | Local config file | Session file |

---

## Recommended Priorities

### P0 — Critical Gaps
1. **Rate limit enforcement with jitter**: Move from tracking-only to automatic enforcement. Add randomized delays (25-60s for likes, 45-90s for follows). This is the #1 anti-ban measure.
2. **Version pin fix**: `instagrapi>=2.3.0` doesn't exist on PyPI (latest is 2.2.1). Fix to `>=2.2.0`.

### P1 — High Value
3. **MQTT bridge for DMs**: Node.js subprocess approach. Gets real-time DMs, typing indicators, and presence with lower ban risk than REST.
4. **`clinstagram install-skill` command**: Auto-detect installed AI agents, copy SKILL.md to appropriate directories. Low effort, high visibility for AI agent ecosystem.
5. **Account warming mode**: `clinstagram config warm-account` that enforces graduated limits for first 14 days.

### P2 — Medium Value
6. **Multi-platform packaging**: Homebrew formula + npm wrapper (for discoverability). The PyPI-only approach limits adoption.
7. **Livestream support**: instagrapi 2.2.1 added it. Expose via `clinstagram live` subcommand.
8. **Captcha handler integration**: instagrapi 2.2.1's CaptchaHandlerMixin. Add `clinstagram auth captcha` for interactive solving.

### P3 — Nice to Have
9. **HikerAPI backend**: `--backend hiker` for users who want managed infrastructure.
10. **Interactive TUI mode**: `clinstagram tui` using Textual (Python TUI framework). Lower priority since agent use case is command-based.
11. **In-terminal image rendering**: Use `term-image` or `timg` for media preview in terminal.
