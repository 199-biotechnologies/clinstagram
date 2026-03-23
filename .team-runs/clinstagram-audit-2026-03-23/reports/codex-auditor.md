# Codex Audit Results

- **Date:** 2026-03-23
- **Model:** GPT-5.4 (xhigh reasoning), 127,471 tokens

## High Severity (5 issues)
1. Security — config_cmd.py:36, router.py:31: setattr without validation undermines policy routing
2. Security — auth.py:92,110, graph.py:75: Secrets in CLI args + access_token in query params
3. Anti-detection — config.py:30, _dispatch.py:75: request_jitter never used, no persistent rate counters
4. Anti-detection — private_login.py:20,123: Static device fingerprint + host-derived locale
5. Performance/Security — media.py:55: Full memory buffer, blind redirects, no content-type validation

## Medium Severity (6 issues)
6. Performance — _dispatch.py:41: New httpx.Client per request, never closed
7. Latency — graph.py:198,220,242: No container status polling before media_publish
8. Performance — private.py:129,254,280: No username→PK cache
9. Latency — dm.py:54,105: Brute-force inbox scan for thread lookup
10. Security — graph.py:465: Raw username interpolation in Graph fields
11. Security — config.py:95, config_cmd.py:12,36: Proxy credentials in plaintext TOML

## Dead Config Surface
- request_jitter, preferred_backend, media_staging.cleanup_after_publish — never read
- private.py:474 — _comment_to_dict missing media_id
