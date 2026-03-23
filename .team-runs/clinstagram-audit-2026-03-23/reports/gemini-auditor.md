# Gemini Audit Results

- **Date:** 2026-03-23
- **Model:** Gemini (auto-routed)
- **Files analyzed:** All Python files under `src/clinstagram/` (cli.py, backends/router.py, backends/graph.py, backends/private.py, backends/base.py, backends/capabilities.py, auth/private_login.py, config.py, models.py, media.py, _dispatch.py, keychain.py, commands/*)

---

## Architecture Assessment

| Severity | File Reference | Current State | Recommended Change | Expected Impact |
|----------|---------------|---------------|-------------------|----------------|
| **High** | `cli.py` | Eagerly imports all 11 command modules and `instagrapi` at startup. | Use lazy-loading/local imports for command groups within `app.add_typer`. | Reduces cold-start latency by ~300-500ms; speeds up `--help`. |
| **Medium** | `_dispatch.py` | `_instantiate_backend` creates a new `httpx.Client` for every single request. | Use a context-managed shared session or a persistent connection pool. | Reduces TLS handshake overhead; enables HTTP/2 keep-alive. |
| **Medium** | `router.py` | Backend preference is hardcoded `["graph_ig", "graph_fb", "private"]`. | Allow `preferred_backend` to be configured globally or per-command via `config.toml`. | Gives users control over cost (Graph) vs. risk (Private) trade-offs. |

## Performance Findings

| Severity | File Reference | Current State | Recommended Change | Expected Impact |
|----------|---------------|---------------|-------------------|----------------|
| **Medium** | `media.py` | `httpx.get` for media downloads is synchronous and blocks the main thread. | Transition to `asyncio` with `httpx.AsyncClient` for downloads. | Better UX and foundation for batch operations/concurrent downloads. |
| **Medium** | `media.py` | Media staging downloads the entire file into memory before writing. | Use `response.iter_bytes()` to stream content directly to the temporary file. | Dramatically reduces memory footprint for 100MB+ video uploads. |

## Hardening Recommendations

| Severity | File Reference | Current State | Recommended Change | Expected Impact |
|----------|---------------|---------------|-------------------|----------------|
| **High** | `_dispatch.py` | Rate limiting is binary (exit on error). No persistent state. | Implement a SQLite-backed token bucket or simple file-based cooldown tracker. | Prevents account bans by enforcing global daily/hourly limits across multiple CLI runs. |
| **Medium** | `private_login.py` | Challenge handler is interactive only. | Support a callback-based or environment-variable-based challenge resolver for CI/CD or headless use. | Enables automation and integration into larger pipelines. |
| **Low** | `keychain.py` | Deleting non-existent passwords logs a silent exception. | Standardize secret deletion checks and support multiple secret providers (Env, File, Keyring). | Improves portability across Linux/Docker environments where `keyring` might fail. |

## Anti-Detection Improvements

| Severity | File Reference | Current State | Recommended Change | Expected Impact |
|----------|---------------|---------------|-------------------|----------------|
| **Critical** | `private_login.py` | `DEFAULT_DEVICE_SETTINGS` is a static "Pixel 7" across all CLI installs. | Generate a unique, deterministic device fingerprint per account using `hmac(account_name, system_uuid)`. | Prevents mass-flagging of the CLI "device type" by Instagram's heuristic engines. |
| **High** | `private.py` | No caching for `_user_id_from_username` calls. | Add a local JSON/SQLite cache for Username -> PK mappings (TTL 24h). | Eliminates redundant "User Info" API calls, reducing account "noise" and latency. |

## Optimization Opportunities

| Severity | File Reference | Current State | Recommended Change | Expected Impact |
|----------|---------------|---------------|-------------------|----------------|
| **High** | `cli.py` | Eager imports at startup. | Lazy-load command groups. | ~300-500ms cold-start reduction. |
| **High** | `private.py` | No username->PK cache. | SQLite/JSON cache with 24h TTL. | Fewer API calls, less detection surface. |
| **Medium** | `_dispatch.py` | New httpx.Client per request. | Shared connection pool. | HTTP/2 keep-alive, reduced TLS overhead. |
| **Medium** | `media.py` | Full file buffered in memory. | Streaming via `iter_bytes()`. | Memory reduction for large video uploads. |

## Latency Reduction

1. **Cold-start:** Lazy imports for command modules — biggest single win (~300-500ms).
2. **Connection reuse:** Persistent `httpx.Client` with connection pooling eliminates repeated TLS handshakes.
3. **Username caching:** Local cache for username->PK lookups removes redundant API round-trips.
4. **Streaming downloads:** `iter_bytes()` reduces time-to-first-byte for media staging.

## Missing Features / Competitive Gaps

1. **MQTT / Real-time:** Current DM implementation is polling-only. Competitors like `instagrapi` support MQTT for real-time notifications/listening.
2. **TUI Mode:** A `clinstagram dashboard` using `Textual` or `Rich` to provide a live feed/inbox view would distinguish this from standard "one-shot" CLIs.
3. **Deployment:** Missing a `brew` Formula or `npm` wrapper (via PyPI) for easier global installation on macOS/Linux.
4. **Session Portability:** No command to export/import session JSON for moving accounts between machines without re-triggering 2FA.

## Prioritized Action Plan

1. **Surgical Fix (Immediate):** Randomize the device fingerprint in `private_login.py`. Having a static Pixel 7 fingerprint for all users is a "signature" that leads to instant account flagging.
2. **Performance Refactor:** Move command imports inside the Typer callback to fix the heavy CLI cold-start.
3. **Resilience:** Implement a basic SQLite cache for ID lookups to minimize the number of requests sent to Instagram, as high request volume is the primary trigger for "Suspicious Activity" challenges.

---

## Raw Gemini Output

```
This audit of the **clinstagram** codebase identifies several architectural bottlenecks and anti-detection risks. While the hybrid routing logic is robust, the implementation suffers from synchronous I/O, static device fingerprinting, and high cold-start latency due to eager imports.

### 1. ARCHITECTURE & PERFORMANCE
| Severity | File Reference | Current State | Recommended Change | Expected Impact |
| :--- | :--- | :--- | :--- | :--- |
| **High** | `cli.py` | Eagerly imports all 11 command modules and `instagrapi` at startup. | Use lazy-loading/local imports for command groups within `app.add_typer`. | Reduces cold-start latency by ~300-500ms; speeds up `--help`. |
| **Medium** | `media.py` | `httpx.get` for media downloads is synchronous and blocks the main thread. | Transition to `asyncio` with `httpx.AsyncClient` for downloads. | Better UX and foundation for batch operations/concurrent downloads. |
| **Medium** | `_dispatch.py` | `_instantiate_backend` creates a new `httpx.Client` for every single request. | Use a context-managed shared session or a persistent connection pool. | Reduces TLS handshake overhead; enables HTTP/2 keep-alive. |

### 2. ANTI-DETECTION & HARDENING
| Severity | File Reference | Current State | Recommended Change | Expected Impact |
| :--- | :--- | :--- | :--- | :--- |
| **Critical** | `private_login.py` | `DEFAULT_DEVICE_SETTINGS` is a static "Pixel 7" across all CLI installs. | Generate a unique, deterministic device fingerprint per account using `hmac(account_name, system_uuid)`. | Prevents mass-flagging of the CLI "device type" by Instagram's heuristic engines. |
| **High** | `_dispatch.py` | Rate limiting is binary (exit on error). No persistent state. | Implement a SQLite-backed token bucket or simple file-based cooldown tracker. | Prevents account bans by enforcing global daily/hourly limits across multiple CLI runs. |
| **Medium** | `private_login.py` | Challenge handler is interactive only. | Support a callback-based or environment-variable-based challenge resolver for CI/CD or headless use. | Enables automation and integration into larger pipelines. |
| **Low** | `keychain.py` | Deleting non-existent passwords logs a silent exception. | Standardize secret deletion checks and support multiple secret providers (Env, File, Keyring). | Improves portability across Linux/Docker environments where `keyring` might fail. |

### 3. OPTIMIZATION & LATENCY
| Severity | File Reference | Current State | Recommended Change | Expected Impact |
| :--- | :--- | :--- | :--- | :--- |
| **High** | `private.py` | No caching for `_user_id_from_username` calls. | Add a local JSON/SQLite cache for Username -> PK mappings (TTL 24h). | Eliminates redundant "User Info" API calls, reducing account "noise" and latency. |
| **Medium** | `media.py` | Media staging downloads the entire file into memory before writing. | Use `response.iter_bytes()` to stream content directly to the temporary file. | Dramatically reduces memory footprint for 100MB+ video uploads. |
| **Medium** | `router.py` | Backend preference is hardcoded `["graph_ig", "graph_fb", "private"]`. | Allow `preferred_backend` to be configured globally or per-command via `config.toml`. | Gives users control over cost (Graph) vs. risk (Private) trade-offs. |

### 4. MISSING FEATURES (COMPETITIVE ANALYSIS)
*   **MQTT / Real-time:** Current DM implementation is polling-only. Competitors like `instagrapi` support MQTT for real-time notifications/listening.
*   **TUI Mode:** A `clinstagram dashboard` using `Textual` or `Rich` to provide a live feed/inbox view would distinguish this from standard "one-shot" CLIs.
*   **Deployment:** Missing a `brew` Formula or `npm` wrapper (via PyPI) for easier global installation on macOS/Linux.
*   **Session Portability:** No command to export/import session JSON for moving accounts between machines without re-triggering 2FA.

### 5. SUMMARY OF ACTION PLAN
1.  **Surgical Fix (Immediate):** Randomize the device fingerprint in `private_login.py`. Having a static Pixel 7 fingerprint for all users is a "signature" that leads to instant account flagging.
2.  **Performance Refactor:** Move command imports inside the Typer callback to fix the heavy CLI cold-start.
3.  **Resilience:** Implement a basic SQLite cache for ID lookups to minimize the number of requests sent to Instagram, as high request volume is the primary trigger for "Suspicious Activity" challenges.
```
